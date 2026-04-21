"""
Funzioni di utilità per interagire con il database SQLite.
"""
import sqlite3
from pathlib import Path

# Percorso del database (stesso usato in init_db.py)
DB_PATH = Path(__file__).parent.parent / "database" / "calcetto.db"


def get_connection():
    """Restituisce una connessione al database con foreign key abilitate."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    # Permette di accedere alle colonne per nome (es: row["name"])
    conn.row_factory = sqlite3.Row
    return conn


# ---------- FUNZIONI PER I GIOCATORI ----------

def get_all_players():
    """Restituisce tutti i giocatori, ordinati per nickname."""
    conn = get_connection()
    players = conn.execute(
        "SELECT id, name, nickname, created_at FROM players ORDER BY nickname;"
    ).fetchall()
    conn.close()
    return players


def add_player(name: str, nickname: str):
    """
    Aggiunge un nuovo giocatore.
    Restituisce (True, messaggio) se riuscito, (False, errore) altrimenti.
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO players (name, nickname) VALUES (?, ?);",
            (name.strip(), nickname.strip())
        )
        conn.commit()
        return True, f"Giocatore '{nickname}' aggiunto!"
    except sqlite3.IntegrityError:
        # Scatta se il nickname è duplicato (UNIQUE nel DB)
        return False, f"Il nickname '{nickname}' è già in uso."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


def delete_player(player_id: int):
    """Elimina un giocatore. Attenzione: non si può eliminare se ha partite giocate."""
    conn = get_connection()
    try:
        # Controlliamo se ha partecipato a partite
        count = conn.execute(
            "SELECT COUNT(*) FROM match_players WHERE player_id = ?;",
            (player_id,)
        ).fetchone()[0]
        if count > 0:
            return False, f"Non puoi eliminare questo giocatore: ha giocato {count} partite."
        
        conn.execute("DELETE FROM players WHERE id = ?;", (player_id,))
        conn.commit()
        return True, "Giocatore eliminato."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()
        
        
# ---------- FUNZIONI PER LE PARTITE ----------

def create_match(match_date, location, notes, team_a_ids, team_b_ids, goals):
    """
    Crea una partita completa: dati della partita, squadre e goal.
    
    Parametri:
        match_date: data della partita (datetime.date)
        location: luogo (stringa, può essere vuota)
        notes: note (stringa, può essere vuota)
        team_a_ids: lista di player_id che giocano nella squadra A
        team_b_ids: lista di player_id che giocano nella squadra B
        goals: lista di dict con chiavi 'scorer_id', 'assist_id' (può essere None), 'team'
    
    Restituisce (True, match_id) se ok, (False, messaggio_errore) altrimenti.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Inserisci la partita
        cursor.execute(
            "INSERT INTO matches (match_date, location, notes) VALUES (?, ?, ?);",
            (match_date.isoformat(), location.strip() or None, notes.strip() or None)
        )
        match_id = cursor.lastrowid
        
        # 2. Inserisci le partecipazioni squadra A
        for player_id in team_a_ids:
            cursor.execute(
                "INSERT INTO match_players (match_id, player_id, team) VALUES (?, ?, 'A');",
                (match_id, player_id)
            )
        
        # 3. Inserisci le partecipazioni squadra B
        for player_id in team_b_ids:
            cursor.execute(
                "INSERT INTO match_players (match_id, player_id, team) VALUES (?, ?, 'B');",
                (match_id, player_id)
            )
        
        # 4. Inserisci i goal
        # 4. Inserisci i goal
        for goal in goals:
            cursor.execute(
                """INSERT INTO goals 
                   (match_id, scorer_id, assist_id, team, is_own_goal) 
                   VALUES (?, ?, ?, ?, ?);""",
                (
                    match_id,
                    goal.get('scorer_id'),      # può essere None
                    goal.get('assist_id'),      # può essere None
                    goal['team'],               # 'A' o 'B' (squadra che prende il punto)
                    1 if goal.get('is_own_goal') else 0
                )
            )
        
        conn.commit()
        return True, match_id
    
    except Exception as e:
        conn.rollback()  # annulla tutto se qualcosa va storto
        return False, f"Errore durante il salvataggio: {e}"
    finally:
        conn.close()
        
        
def get_all_matches():
    """
    Restituisce tutte le partite con il punteggio finale calcolato.
    Ordinate dalla più recente alla più vecchia.
    """
    conn = get_connection()
    matches = conn.execute("""
        SELECT 
            m.id,
            m.match_date,
            m.location,
            m.notes,
            COALESCE(SUM(CASE WHEN g.team = 'A' THEN 1 ELSE 0 END), 0) AS score_a,
            COALESCE(SUM(CASE WHEN g.team = 'B' THEN 1 ELSE 0 END), 0) AS score_b
        FROM matches m
        LEFT JOIN goals g ON g.match_id = m.id
        GROUP BY m.id
        ORDER BY m.match_date DESC, m.id DESC;
    """).fetchall()
    conn.close()
    return matches


def get_match_details(match_id: int):
    """
    Restituisce un dizionario con tutti i dettagli di una partita:
    - info base (data, luogo, note)
    - giocatori divisi per squadra
    - lista dei goal con marcatore, assist, squadra
    """
    conn = get_connection()
    
    # Info base partita
    match = conn.execute(
        "SELECT id, match_date, location, notes FROM matches WHERE id = ?;",
        (match_id,)
    ).fetchone()
    
    if not match:
        conn.close()
        return None
    
    # Giocatori e squadre
    players_rows = conn.execute("""
        SELECT p.id, p.nickname, p.name, mp.team
        FROM match_players mp
        JOIN players p ON p.id = mp.player_id
        WHERE mp.match_id = ?
        ORDER BY mp.team, p.nickname;
    """, (match_id,)).fetchall()
    
    team_a = [dict(p) for p in players_rows if p['team'] == 'A']
    team_b = [dict(p) for p in players_rows if p['team'] == 'B']
    
    # Goal con info marcatore, assist e squadra che ha preso il punto
    goals_rows = conn.execute("""
        SELECT 
            g.id,
            g.minute,
            g.team,
            g.is_own_goal,
            scorer.nickname AS scorer_nickname,
            assist.nickname AS assist_nickname
        FROM goals g
        LEFT JOIN players scorer ON scorer.id = g.scorer_id
        LEFT JOIN players assist ON assist.id = g.assist_id
        WHERE g.match_id = ?
        ORDER BY g.id;
    """, (match_id,)).fetchall()
    
    goals = [dict(g) for g in goals_rows]
    
    # Punteggio
    score_a = sum(1 for g in goals if g['team'] == 'A')
    score_b = sum(1 for g in goals if g['team'] == 'B')
    
    conn.close()
    
    return {
        "id": match['id'],
        "date": match['match_date'],
        "location": match['location'],
        "notes": match['notes'],
        "team_a": team_a,
        "team_b": team_b,
        "goals": goals,
        "score_a": score_a,
        "score_b": score_b
    }


def delete_match(match_id: int):
    """Elimina una partita e tutti i goal/partecipazioni collegate (cascade)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM matches WHERE id = ?;", (match_id,))
        conn.commit()
        return True, "Partita eliminata."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()
        
        
# ---------- FUNZIONI PER GLI UTENTI / LOGIN ----------

def get_all_users_for_auth():
    """
    Restituisce tutti gli utenti nel formato richiesto da streamlit-authenticator,
    più un dizionario separato username -> role per controllare i permessi.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT u.username, u.password_hash, u.role, p.nickname
        FROM users u
        LEFT JOIN players p ON p.id = u.player_id;
    """).fetchall()
    conn.close()
    
    credentials = {"usernames": {}}
    roles = {}
    for row in rows:
        # Se l'utente è collegato a un giocatore, mostriamo il nickname
        # Altrimenti mostriamo l'username come nome visualizzato
        display_name = row['nickname'] if row['nickname'] else row['username']
        credentials["usernames"][row['username']] = {
            "name": display_name,
            "password": row['password_hash']
        }
        roles[row['username']] = row['role']
    
    return credentials, roles


def create_user(username: str, password_hash: str, role: str = 'viewer', player_id: int = None):
    """
    Crea un account utente.
    - player_id opzionale: se None, è un utente "solo spettatore" non legato a un giocatore
    - role: 'admin' o 'viewer' o 'manager'
    """
    if role not in ('admin', 'viewer', 'manager'):
        return False, "Ruolo non valido."
    
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (player_id, username, password_hash, role) VALUES (?, ?, ?, ?);",
            (player_id, username.strip().lower(), password_hash, role)
        )
        conn.commit()
        return True, f"Account '{username}' creato come {role}!"
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, f"Lo username '{username}' è già in uso."
        elif "player_id" in str(e):
            return False, "Questo giocatore ha già un account."
        else:
            return False, f"Errore: {e}"
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


def update_user_password(username: str, new_password_hash: str):
    """Aggiorna la password di un utente."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?;",
            (new_password_hash, username)
        )
        conn.commit()
        return True, "Password aggiornata."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


def get_players_without_user():
    """Restituisce i giocatori che NON hanno ancora un account."""
    conn = get_connection()
    players = conn.execute("""
        SELECT p.id, p.name, p.nickname
        FROM players p
        LEFT JOIN users u ON u.player_id = p.id
        WHERE u.id IS NULL
        ORDER BY p.nickname;
    """).fetchall()
    conn.close()
    return players


def get_all_users():
    """Restituisce tutti gli utenti con il loro ruolo e giocatore collegato (se c'è)."""
    conn = get_connection()
    users = conn.execute("""
        SELECT u.id, u.username, u.role, u.created_at, p.nickname AS player_nickname
        FROM users u
        LEFT JOIN players p ON p.id = u.player_id
        ORDER BY u.role DESC, u.username;
    """).fetchall()
    conn.close()
    return users


def update_user_role(user_id: int, new_role: str):
    """Cambia il ruolo di un utente."""
    if new_role not in ('admin', 'viewer', 'manager'):
        return False, "Ruolo non valido."
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET role = ? WHERE id = ?;", (new_role, user_id))
        conn.commit()
        return True, f"Ruolo aggiornato a '{new_role}'."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


def delete_user(user_id: int):
    """Elimina un utente."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        conn.commit()
        return True, "Utente eliminato."
    except Exception as e:
        return False, f"Errore: {e}"
    finally:
        conn.close()


def count_admins():
    """Conta quanti admin ci sono (serve per non lasciare l'app senza admin)."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin';"
    ).fetchone()[0]
    conn.close()
    return count


def update_match(match_id: int, match_date, location, notes, team_a_ids, team_b_ids, goals):
    """
    Aggiorna una partita esistente: dati base, squadre e goal.
    Riscrive completamente partecipazioni e goal (più semplice e sicuro).
    
    I goal passati possono avere 'id' (goal esistenti) o non averlo (nuovi).
    Se un giocatore viene rimosso dalle squadre e aveva segnato, i suoi goal
    vengono trasformati automaticamente in "goal sconosciuti" (scorer_id=NULL).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN;")
        
        # 1. Aggiorna i dati base della partita
        cursor.execute("""
            UPDATE matches 
            SET match_date = ?, location = ?, notes = ?
            WHERE id = ?;
        """, (
            match_date.isoformat(),
            location.strip() or None,
            notes.strip() or None,
            match_id
        ))
        
        # 2. Riscrivi le partecipazioni: cancella tutte e reinserisci
        cursor.execute("DELETE FROM match_players WHERE match_id = ?;", (match_id,))
        
        for player_id in team_a_ids:
            cursor.execute(
                "INSERT INTO match_players (match_id, player_id, team) VALUES (?, ?, 'A');",
                (match_id, player_id)
            )
        for player_id in team_b_ids:
            cursor.execute(
                "INSERT INTO match_players (match_id, player_id, team) VALUES (?, ?, 'B');",
                (match_id, player_id)
            )
        
        # 3. Riscrivi i goal: cancella tutti e reinserisci
        # Se un marcatore non gioca più, lo trasformiamo in "goal sconosciuto"
        valid_player_ids = set(team_a_ids) | set(team_b_ids)
        
        cursor.execute("DELETE FROM goals WHERE match_id = ?;", (match_id,))
        
        for goal in goals:
            scorer_id = goal.get('scorer_id')
            assist_id = goal.get('assist_id')
            
            # Se il marcatore non è più tra i giocatori, lo rimuoviamo (goal sconosciuto)
            if scorer_id is not None and scorer_id not in valid_player_ids:
                scorer_id = None
                assist_id = None  # senza marcatore non ha senso mantenere l'assist
            
            # Stessa logica per l'assist: se chi ha fatto assist non gioca più, lo rimuoviamo
            if assist_id is not None and assist_id not in valid_player_ids:
                assist_id = None
            
            cursor.execute(
                """INSERT INTO goals 
                   (match_id, scorer_id, assist_id, team, is_own_goal) 
                   VALUES (?, ?, ?, ?, ?);""",
                (
                    match_id,
                    scorer_id,
                    assist_id,
                    goal['team'],
                    1 if goal.get('is_own_goal') else 0
                )
            )
        
        conn.commit()
        return True, "Partita aggiornata."
    
    except Exception as e:
        conn.rollback()
        return False, f"Errore durante l'aggiornamento: {e}"
    finally:
        conn.close()