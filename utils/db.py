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