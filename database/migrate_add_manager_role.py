"""
Migrazione: aggiunge il ruolo 'manager' ai valori permessi nel CHECK della colonna role.

Lanciare UNA SOLA VOLTA:
    python database/migrate_add_manager_role.py
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
        
        print("Creo nuova tabella users_new con CHECK aggiornato...")
        cursor.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER UNIQUE,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer' 
                    CHECK (role IN ('admin', 'manager', 'viewer')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id)
            );
        """)
        
        print("Copio utenti esistenti...")
        cursor.execute("""
            INSERT INTO users_new (id, player_id, username, password_hash, role, created_at)
            SELECT id, player_id, username, password_hash, role, created_at
            FROM users;
        """)
        
        old_count = cursor.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        new_count = cursor.execute("SELECT COUNT(*) FROM users_new;").fetchone()[0]
        
        if old_count != new_count:
            raise Exception(f"Mismatch righe: vecchia={old_count}, nuova={new_count}")
        
        print(f"Copiate {new_count} righe.")
        
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