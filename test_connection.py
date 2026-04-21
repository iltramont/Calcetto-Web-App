"""
Script di test: verifica che la connessione al database funzioni.
"""
from utils.db import get_connection, USE_POSTGRES

print(f"Backend in uso: {'PostgreSQL (Supabase)' if USE_POSTGRES else 'SQLite locale'}")

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM players;")
    row = cur.fetchone()
    count = row[0] if isinstance(row, tuple) else list(dict(row).values())[0]
    print(f"✅ Connessione OK. Giocatori nel DB: {count}")
    conn.close()
except Exception as e:
    print(f"❌ Errore connessione: {e}")