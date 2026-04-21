"""
Migrazione: 
- Rende player_id nullable in users (utenti possono non essere giocatori)
- Aggiunge il campo 'role' ('admin' o 'viewer')
- Imposta tutti gli utenti esistenti come admin

Lanciare UNA SOLA VOLTA:
    python database/migrate_users_roles.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "calcetto.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Crea la nuova tabella users con schema aggiornato
        print("Creo nuova tabella users_new...")
        cursor.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER UNIQUE,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'viewer')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id)
            );
        """)
        
        # 2. Copia gli utenti esistenti, impostandoli tutti come admin
        print("Copio utenti esistenti (tutti come admin)...")
        cursor.execute("""
            INSERT INTO users_new (id, player_id, username, password_hash, role, created_at)
            SELECT id, player_id, username, password_hash, 'admin', created_at
            FROM users;
        """)
        
        old_count = cursor.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        new_count = cursor.execute("SELECT COUNT(*) FROM users_new;").fetchone()[0]
        
        if old_count != new_count:
            raise Exception(f"Mismatch righe: vecchia={old_count}, nuova={new_count}")
        
        print(f"Copiate {new_count} righe.")
        
        # 3. Elimina vecchia tabella e rinomina la nuova
        cursor.execute("DROP TABLE users;")
        cursor.execute("ALTER TABLE users_new RENAME TO users;")
        
        cursor.execute("COMMIT;")
        print("✅ Migrazione completata!")
        
    except Exception as e:
        cursor.execute("ROLLBACK;")
        print(f"❌ Errore: {e}")
        raise
    finally:
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    migrate()