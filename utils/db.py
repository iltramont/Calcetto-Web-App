"""
Funzioni di utilità per interagire con il database.
Supporta sia SQLite (sviluppo locale) sia PostgreSQL (produzione su Supabase).

La scelta avviene in base alla presenza della variabile d'ambiente DATABASE_URL:
- Se presente: usa PostgreSQL
- Altrimenti: usa SQLite locale
"""
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Carica le variabili d'ambiente da .env (se presente)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

# Import condizionale per evitare errori se psycopg2 non è installato in locale
if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

SQLITE_PATH = Path(__file__).parent.parent / "database" / "calcetto.db"


def get_connection():
    """Restituisce una connessione al database."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn


def _cursor(conn):
    """Crea un cursor compatibile con entrambi i DB che restituisce righe come dict."""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        return conn.cursor()


def _q(query: str) -> str:
    """
    Converte i placeholder '?' (SQLite) in '%s' (PostgreSQL) quando necessario.
    Così possiamo scrivere le query una volta sola con '?' e convertirle al volo.
    """
    if USE_POSTGRES:
        return query.replace("?", "%s")
    return query


def _row_to_dict(row):
    """Converte una riga in dict (gestisce sia sqlite3.Row sia dict di psycopg2)."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def _rows_to_dicts(rows):
    """Converte una lista di righe in lista di dict."""
    return [_row_to_dict(r) for r in rows]


# ---------- FUNZIONI PER I GIOCATORI ----------

def get_all_players():
    conn = get_connection()
    cur = _cursor(conn)
    cur.execute(_q("SELECT id, name, nickname, created_at FROM players ORDER BY nickname;"))
    result = _rows_to_dicts(cur.fetchall())
    conn.close()
    return result


def add_player(name: str, nickname: str):
    conn = get_connection()
    try:
        cur = _cursor(conn)
        cur.execute(
            _q("INSERT INTO players (name, nickname) VALUES (?, ?);"),
            (name.strip(), nickname.strip())
        )
        conn.commit()
        return True, f"Giocatore '{nickname}' aggiunto!"
    except Exception as e:
        # psycopg2 usa psycopg2.IntegrityError, sqlite3 usa sqlite3.IntegrityError
        # catturiamo in modo generico per entrambi
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg:
            return False, f"Il nickname '{nickname}' è già in uso."
        return False, f"Errore: {e}"
    finally:
        conn.close()


def delete_player(player_id: int):
    conn = get_connection()
    try:
        cur = _cursor(conn)
        cur.execute(
            _q("SELECT COUNT(*) AS c FROM match_players WHERE player_id = ?;"),
            (player_id,)
        )
        row = _row_to_dict(cur.fetchone())
        count = row['c'] if 'c' in row else list(row.values())[0]
        
        if count > 0:
            return False, f"Non puoi eliminare questo giocatore: ha giocato {count} partite."
        
        cur.execute(_q("DELETE FROM players WHERE id = ?;"), (player_id,))
        conn.commit()
        return True, "Giocatore eliminato."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


# ---------- FUNZIONI PER LE PARTITE ----------

def create_match(match_date, location, notes, team_a_ids, team_b_ids, goals):
    conn = get_connection()
    try:
        cur = _cursor(conn)
        
        # 1. Inserisci la partita (serve RETURNING per PostgreSQL, lastrowid per SQLite)
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO matches (match_date, location, notes) VALUES (%s, %s, %s) RETURNING id;",
                (match_date.isoformat(), location.strip() or None, notes.strip() or None)
            )
            match_id = cur.fetchone()['id']
        else:
            cur.execute(
                "INSERT INTO matches (match_date, location, notes) VALUES (?, ?, ?);",
                (match_date.isoformat(), location.strip() or None, notes.strip() or None)
            )
            match_id = cur.lastrowid
        
        # 2. Partecipazioni
        for player_id in team_a_ids:
            cur.execute(
                _q("INSERT INTO match_players (match_id, player_id, team) VALUES (?, ?, 'A');"),
                (match_id, player_id)
            )
        for player_id in team_b_ids:
            cur.execute(
                _q("INSERT INTO match_players (match_id, player_id, team) VALUES (?, ?, 'B');"),
                (match_id, player_id)
            )
        
        # 3. Goal
        for goal in goals:
            cur.execute(
                _q("""INSERT INTO goals (match_id, scorer_id, assist_id, team, is_own_goal) 
                      VALUES (?, ?, ?, ?, ?);"""),
                (
                    match_id,
                    goal.get('scorer_id'),
                    goal.get('assist_id'),
                    goal['team'],
                    bool(goal.get('is_own_goal')) if USE_POSTGRES else (1 if goal.get('is_own_goal') else 0)
                )
            )
        
        conn.commit()
        return True, match_id
    except Exception as e:
        conn.rollback()
        return False, f"Errore durante il salvataggio: {e}"
    finally:
        conn.close()


def update_match(match_id: int, match_date, location, notes, team_a_ids, team_b_ids, goals):
    conn = get_connection()
    try:
        cur = _cursor(conn)
        
        cur.execute(
            _q("UPDATE matches SET match_date = ?, location = ?, notes = ? WHERE id = ?;"),
            (match_date.isoformat(), location.strip() or None, notes.strip() or None, match_id)
        )
        
        cur.execute(_q("DELETE FROM match_players WHERE match_id = ?;"), (match_id,))
        
        for player_id in team_a_ids:
            cur.execute(
                _q("INSERT INTO match_players (match_id, player_id, team) VALUES (?, ?, 'A');"),
                (match_id, player_id)
            )
        for player_id in team_b_ids:
            cur.execute(
                _q("INSERT INTO match_players (match_id, player_id, team) VALUES (?, ?, 'B');"),
                (match_id, player_id)
            )
        
        valid_player_ids = set(team_a_ids) | set(team_b_ids)
        cur.execute(_q("DELETE FROM goals WHERE match_id = ?;"), (match_id,))
        
        for goal in goals:
            scorer_id = goal.get('scorer_id')
            assist_id = goal.get('assist_id')
            
            if scorer_id is not None and scorer_id not in valid_player_ids:
                scorer_id = None
                assist_id = None
            if assist_id is not None and assist_id not in valid_player_ids:
                assist_id = None
            
            cur.execute(
                _q("""INSERT INTO goals (match_id, scorer_id, assist_id, team, is_own_goal)
                      VALUES (?, ?, ?, ?, ?);"""),
                (
                    match_id, scorer_id, assist_id, goal['team'],
                    bool(goal.get('is_own_goal')) if USE_POSTGRES else (1 if goal.get('is_own_goal') else 0)
                )
            )
        
        conn.commit()
        return True, "Partita aggiornata."
    except Exception as e:
        conn.rollback()
        return False, f"Errore: {e}"
    finally:
        conn.close()


def get_all_matches():
    conn = get_connection()
    cur = _cursor(conn)
    cur.execute("""
        SELECT 
            m.id,
            m.match_date,
            m.location,
            m.notes,
            COALESCE(SUM(CASE WHEN g.team = 'A' THEN 1 ELSE 0 END), 0) AS score_a,
            COALESCE(SUM(CASE WHEN g.team = 'B' THEN 1 ELSE 0 END), 0) AS score_b
        FROM matches m
        LEFT JOIN goals g ON g.match_id = m.id
        GROUP BY m.id, m.match_date, m.location, m.notes
        ORDER BY m.match_date DESC, m.id DESC;
    """)
    result = _rows_to_dicts(cur.fetchall())
    conn.close()
    
    # Normalizza la data in stringa (PostgreSQL restituisce date object, SQLite stringa)
    for r in result:
        if hasattr(r['match_date'], 'isoformat'):
            r['match_date'] = r['match_date'].isoformat()
    
    return result


def get_match_details(match_id: int):
    conn = get_connection()
    cur = _cursor(conn)
    
    cur.execute(
        _q("SELECT id, match_date, location, notes FROM matches WHERE id = ?;"),
        (match_id,)
    )
    match = _row_to_dict(cur.fetchone())
    
    if not match:
        conn.close()
        return None
    
    cur.execute(_q("""
        SELECT p.id, p.nickname, p.name, mp.team
        FROM match_players mp
        JOIN players p ON p.id = mp.player_id
        WHERE mp.match_id = ?
        ORDER BY mp.team, p.nickname;
    """), (match_id,))
    players_rows = _rows_to_dicts(cur.fetchall())
    
    team_a = [p for p in players_rows if p['team'] == 'A']
    team_b = [p for p in players_rows if p['team'] == 'B']
    
    cur.execute(_q("""
        SELECT 
            g.id, g.minute, g.team, g.is_own_goal,
            scorer.nickname AS scorer_nickname,
            assist.nickname AS assist_nickname
        FROM goals g
        LEFT JOIN players scorer ON scorer.id = g.scorer_id
        LEFT JOIN players assist ON assist.id = g.assist_id
        WHERE g.match_id = ?
        ORDER BY g.id;
    """), (match_id,))
    goals = _rows_to_dicts(cur.fetchall())
    
    score_a = sum(1 for g in goals if g['team'] == 'A')
    score_b = sum(1 for g in goals if g['team'] == 'B')
    
    # Converti la data in stringa (PostgreSQL restituisce date object, SQLite stringa)
    match_date = match['match_date']
    if hasattr(match_date, 'isoformat'):
        match_date = match_date.isoformat()
    
    conn.close()
    
    return {
        "id": match['id'],
        "date": match_date,
        "location": match['location'],
        "notes": match['notes'],
        "team_a": team_a,
        "team_b": team_b,
        "goals": goals,
        "score_a": score_a,
        "score_b": score_b
    }


def delete_match(match_id: int):
    conn = get_connection()
    try:
        cur = _cursor(conn)
        cur.execute(_q("DELETE FROM matches WHERE id = ?;"), (match_id,))
        conn.commit()
        return True, "Partita eliminata."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


# ---------- FUNZIONI PER GLI UTENTI / LOGIN ----------

def get_all_users_for_auth():
    conn = get_connection()
    cur = _cursor(conn)
    cur.execute("""
        SELECT u.username, u.password_hash, u.role, p.nickname
        FROM users u
        LEFT JOIN players p ON p.id = u.player_id;
    """)
    rows = _rows_to_dicts(cur.fetchall())
    conn.close()
    
    credentials = {"usernames": {}}
    roles = {}
    for row in rows:
        display_name = row['nickname'] if row['nickname'] else row['username']
        credentials["usernames"][row['username']] = {
            "name": display_name,
            "password": row['password_hash']
        }
        roles[row['username']] = row['role']
    return credentials, roles


def create_user(username: str, password_hash: str, role: str = 'viewer', player_id: int = None):
    if role not in ('admin', 'manager', 'viewer'):
        return False, "Ruolo non valido."
    
    conn = get_connection()
    try:
        cur = _cursor(conn)
        cur.execute(
            _q("INSERT INTO users (player_id, username, password_hash, role) VALUES (?, ?, ?, ?);"),
            (player_id, username.strip().lower(), password_hash, role)
        )
        conn.commit()
        return True, f"Account '{username}' creato come {role}!"
    except Exception as e:
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg:
            if "username" in msg:
                return False, f"Lo username '{username}' è già in uso."
            return False, "Questo giocatore ha già un account."
        return False, f"Errore: {e}"
    finally:
        conn.close()


def update_user_password(username: str, new_password_hash: str):
    conn = get_connection()
    try:
        cur = _cursor(conn)
        cur.execute(
            _q("UPDATE users SET password_hash = ? WHERE username = ?;"),
            (new_password_hash, username)
        )
        conn.commit()
        return True, "Password aggiornata."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


def get_players_without_user():
    conn = get_connection()
    cur = _cursor(conn)
    cur.execute("""
        SELECT p.id, p.name, p.nickname
        FROM players p
        LEFT JOIN users u ON u.player_id = p.id
        WHERE u.id IS NULL
        ORDER BY p.nickname;
    """)
    result = _rows_to_dicts(cur.fetchall())
    conn.close()
    return result


def get_all_users():
    conn = get_connection()
    cur = _cursor(conn)
    cur.execute("""
        SELECT u.id, u.username, u.role, u.created_at, p.nickname AS player_nickname
        FROM users u
        LEFT JOIN players p ON p.id = u.player_id
        ORDER BY u.role DESC, u.username;
    """)
    result = _rows_to_dicts(cur.fetchall())
    conn.close()
    return result


def update_user_role(user_id: int, new_role: str):
    if new_role not in ('admin', 'manager', 'viewer'):
        return False, "Ruolo non valido."
    conn = get_connection()
    try:
        cur = _cursor(conn)
        cur.execute(_q("UPDATE users SET role = ? WHERE id = ?;"), (new_role, user_id))
        conn.commit()
        return True, f"Ruolo aggiornato a '{new_role}'."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


def delete_user(user_id: int):
    conn = get_connection()
    try:
        cur = _cursor(conn)
        cur.execute(_q("DELETE FROM users WHERE id = ?;"), (user_id,))
        conn.commit()
        return True, "Utente eliminato."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


def count_admins():
    conn = get_connection()
    cur = _cursor(conn)
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin';")
    row = _row_to_dict(cur.fetchone())
    count = row['c'] if 'c' in row else list(row.values())[0]
    conn.close()
    return count


# ---------- FUNZIONI PER STATISTICHE ----------

def get_standings():
    """
    Calcola la classifica generale: per ogni giocatore restituisce 
    partite giocate, vittorie, pareggi, sconfitte e punti.
    
    Punti: 3 per vittoria, 1 per pareggio, 0 per sconfitta.
    """
    conn = get_connection()
    cur = _cursor(conn)
    
    # La query è densa ma fa una cosa precisa:
    # 1. Per ogni partita calcola i goal di squadra A e B (subquery)
    # 2. Per ogni partecipazione (player + match), determina se ha vinto, pareggiato o perso
    # 3. Aggrega per giocatore contando V/P/S e calcolando i punti
    cur.execute("""
        WITH match_scores AS (
            SELECT 
                m.id AS match_id,
                COALESCE(SUM(CASE WHEN g.team = 'A' THEN 1 ELSE 0 END), 0) AS score_a,
                COALESCE(SUM(CASE WHEN g.team = 'B' THEN 1 ELSE 0 END), 0) AS score_b
            FROM matches m
            LEFT JOIN goals g ON g.match_id = m.id
            GROUP BY m.id
        ),
        player_results AS (
            SELECT 
                mp.player_id,
                CASE 
                    WHEN mp.team = 'A' AND ms.score_a > ms.score_b THEN 'W'
                    WHEN mp.team = 'B' AND ms.score_b > ms.score_a THEN 'W'
                    WHEN ms.score_a = ms.score_b THEN 'D'
                    ELSE 'L'
                END AS result
            FROM match_players mp
            JOIN match_scores ms ON ms.match_id = mp.match_id
        )
        SELECT 
            p.id,
            p.nickname,
            p.name,
            COUNT(*) AS played,
            SUM(CASE WHEN pr.result = 'W' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN pr.result = 'D' THEN 1 ELSE 0 END) AS draws,
            SUM(CASE WHEN pr.result = 'L' THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN pr.result = 'W' THEN 3 
                     WHEN pr.result = 'D' THEN 1 
                     ELSE 0 END) AS points
        FROM player_results pr
        JOIN players p ON p.id = pr.player_id
        GROUP BY p.id, p.nickname, p.name
        ORDER BY points DESC, wins DESC, played DESC, p.nickname ASC;
    """)
    
    result = _rows_to_dicts(cur.fetchall())
    conn.close()
    return result