"""
Pagina con la classifica dei giocatori.
Accessibile a tutti gli utenti loggati (anche viewer).
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import require_login
from utils.db import get_standings

st.set_page_config(page_title="Classifica", page_icon="🏆")
user = require_login()

st.title("🏆 Classifica")
st.caption("3 punti per vittoria, 1 per pareggio, 0 per sconfitta.")

standings = get_standings()

if not standings:
    st.info("Nessuna partita giocata ancora. La classifica si popolerà dopo la prima partita!")
    st.stop()

# Trasformiamo i dati nel formato che vogliamo mostrare
table_data = []
for i, p in enumerate(standings, start=1):
    # Medaglie per i primi tre
    if i == 1:
        position = "1 🥇"
    elif i == 2:
        position = "2 🥈"
    elif i == 3:
        position = "3 🥉"
    else:
        position = f"{i}"
    
    table_data.append({
        "Pos": position,
        "Giocatore": p['nickname'],
        "PG": p['played'],
        "Pti": p['points'],
        "Media": round(p['points'] / p['played'], 2) if p['played'] > 0 else 0,
        "V": p['wins'],
        "P": p['draws'],
        "S": p['losses'],
    })

# Mostriamo come dataframe (Streamlit lo rende interattivo: ordinabile, ridimensionabile)
st.dataframe(
    table_data,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Pos": st.column_config.TextColumn("Pos", width="small"),
        "Giocatore": st.column_config.TextColumn("Giocatore", width="medium"),
        "PG": st.column_config.NumberColumn("PG", help="Partite Giocate", width="small"),
        "Pti": st.column_config.NumberColumn(
            "Punti", 
            help="3 per vittoria, 1 per pareggio",
            width="small"
        ),
        "Media": st.column_config.NumberColumn(
            "Media Punti",
            help="Punti per partita (Punti / Partite Giocate)",
            format="%.2f",
            width="small"
        ),
        "V": st.column_config.NumberColumn("V", help="Vittorie", width="small"),
        "P": st.column_config.NumberColumn("P", help="Pareggi", width="small"),
        "S": st.column_config.NumberColumn("S", help="Sconfitte", width="small"),
    }
)

# Info supplementari sotto
total_matches = sum(p['played'] for p in standings) // 1  # ogni partita conta più volte (una per ogni giocatore)
# Stima del numero di partite uniche: prendiamo il massimo di partite giocate da un singolo giocatore
# (il giocatore con più partite ne avrà giocate tante quante ne sono state fatte, se è sempre presente)
max_played = max(p['played'] for p in standings)

most_active = max(standings, key=lambda p: p['played'])


col1, col2 = st.columns(2)
with col1:
    st.metric("Giocatori in classifica", len(standings))
with col2:
    st.metric(
        "Giocatore più assiduo",
        most_active['nickname'],
        delta=f"{most_active['played']} partite",
        delta_color="off",
        help="Chi ha giocato più partite in totale"
    )