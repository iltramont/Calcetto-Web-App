"""
Script per creare il database SQLite con tutte le tabelle.
Va eseguito UNA SOLA VOLTA per inizializzare il database.
Se il database esiste già, non sovrascrive nulla.
"""
import sqlite3
from pathlib import Path

# Percorso del file database (nella cartella database/)
DB_PATH = Path(__file__).parent / "calcetto.db"


def init_database():
    """Crea le tabelle se non esistono già."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Abilita il supporto alle foreign key (SQLite non le forza di default)
    cursor.execute("PRAGMA foreign_keys = ON;")

    # --- Tabella giocatori ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            nickname TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # --- Tabella utenti (per il login) ---
    # Un utente può essere collegato a un giocatore (tramite player_id) o essere
    # un semplice spettatore senza collegamento.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER UNIQUE,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'manager', 'viewer')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        );
    """)

    # --- Tabella partite ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_date DATE NOT NULL,
            location TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
    """)

    # --- Tabella di collegamento: chi ha giocato in quale squadra ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team TEXT NOT NULL CHECK (team IN ('A', 'B')),
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (player_id) REFERENCES players(id),
            UNIQUE (match_id, player_id)
        );
    """)

    # --- Tabella goal ---
    cursor.execute("""
        CREATE TABLE goals_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            scorer_id INTEGER,
            assist_id INTEGER,
            minute INTEGER,
            team TEXT NOT NULL CHECK (team IN ('A', 'B')),
            is_own_goal INTEGER DEFAULT 0,
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (scorer_id) REFERENCES players(id),
            FOREIGN KEY (assist_id) REFERENCES players(id)
        );
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database inizializzato correttamente: {DB_PATH}")


if __name__ == "__main__":
    init_database()