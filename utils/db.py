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
        for goal in goals:
            cursor.execute(
                "INSERT INTO goals (match_id, scorer_id, assist_id) VALUES (?, ?, ?);",
                (match_id, goal['scorer_id'], goal.get('assist_id'))
            )
        
        conn.commit()
        return True, match_id
    
    except Exception as e:
        conn.rollback()  # annulla tutto se qualcosa va storto
        return False, f"Errore durante il salvataggio: {e}"
    finally:
        conn.close()