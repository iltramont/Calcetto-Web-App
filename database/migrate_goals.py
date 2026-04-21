"""
Migrazione: aggiunge i campi 'team' e 'is_own_goal' alla tabella goals.
Gestisce anche la compatibilità con i goal senza marcatore e gli autogoal.

Lanciare UNA SOLA VOLTA:
    python database/migrate_goals.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "calcetto.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verifica quali colonne esistono già (per poter rilanciare lo script senza errori)
    cursor.execute("PRAGMA table_info(goals);")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # 1. Aggiungi colonna 'team' se non esiste
    if 'team' not in existing_columns:
        print("Aggiungo colonna 'team'...")
        cursor.execute("ALTER TABLE goals ADD COLUMN team TEXT;")
    else:
        print("Colonna 'team' già presente, skip.")
    
    # 2. Aggiungi colonna 'is_own_goal' se non esiste
    if 'is_own_goal' not in existing_columns:
        print("Aggiungo colonna 'is_own_goal'...")
        cursor.execute("ALTER TABLE goals ADD COLUMN is_own_goal INTEGER DEFAULT 0;")
    else:
        print("Colonna 'is_own_goal' già presente, skip.")
    
    # 3. Popola 'team' per i goal esistenti che ce l'hanno NULL
    # (usando la squadra del marcatore, visto che prima non c'erano autogoal né goal senza marcatore)
    print("Popolo 'team' per i goal esistenti...")
    cursor.execute("""
        UPDATE goals
        SET team = (
            SELECT mp.team 
            FROM match_players mp 
            WHERE mp.match_id = goals.match_id 
              AND mp.player_id = goals.scorer_id
        )
        WHERE team IS NULL;
    """)
    
    # 4. Rinforziamo 'is_own_goal' a 0 per eventuali NULL (sicurezza)
    cursor.execute("UPDATE goals SET is_own_goal = 0 WHERE is_own_goal IS NULL;")
    
    conn.commit()
    conn.close()
    print("✅ Migrazione completata!")


if __name__ == "__main__":
    migrate()