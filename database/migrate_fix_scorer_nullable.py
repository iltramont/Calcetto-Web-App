"""
Migrazione: rende scorer_id nullable nella tabella goals.
Ricrea la tabella per rimuovere il vincolo NOT NULL implicito.

Lanciare UNA SOLA VOLTA:
    python database/migrate_fix_scorer_nullable.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "calcetto.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Disabilita temporaneamente le foreign key durante la migrazione
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Crea la nuova tabella con lo schema corretto
        print("Creo nuova tabella goals_new...")
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
        
        # 2. Copia i dati dalla vecchia alla nuova
        print("Copio i dati esistenti...")
        cursor.execute("""
            INSERT INTO goals_new (id, match_id, scorer_id, assist_id, minute, team, is_own_goal)
            SELECT id, match_id, scorer_id, assist_id, minute, team, 
                   COALESCE(is_own_goal, 0)
            FROM goals;
        """)
        
        # Verifica che il numero di righe corrisponda
        old_count = cursor.execute("SELECT COUNT(*) FROM goals;").fetchone()[0]
        new_count = cursor.execute("SELECT COUNT(*) FROM goals_new;").fetchone()[0]
        
        if old_count != new_count:
            raise Exception(f"Mismatch righe: vecchia={old_count}, nuova={new_count}")
        
        print(f"Copiate {new_count} righe.")
        
        # 3. Elimina la vecchia tabella
        print("Elimino la vecchia tabella goals...")
        cursor.execute("DROP TABLE goals;")
        
        # 4. Rinomina la nuova
        print("Rinomino goals_new → goals...")
        cursor.execute("ALTER TABLE goals_new RENAME TO goals;")
        
        cursor.execute("COMMIT;")
        print("✅ Migrazione completata con successo!")
        
    except Exception as e:
        cursor.execute("ROLLBACK;")
        print(f"❌ Errore durante la migrazione: {e}")
        print("Il database è stato ripristinato allo stato precedente.")
        raise
    
    finally:
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    migrate()