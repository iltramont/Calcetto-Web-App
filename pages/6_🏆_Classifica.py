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

max_played = max(p['played'] for p in standings)  # Il numero di partite massimo giocate da un singolo giocatore
most_active = [p for p in standings if p['played'] == max_played]  # Tutti i giocatori che hanno giocato più partite
nick_most_active = "\n\n".join(p['nickname'] for p in most_active)  # Nomi dei giocatori più attivi
title_most_active = "Giocatori più assidui" if len(most_active) > 1 else "Giocatore più assiduo"

col1, col2 = st.columns(2, border=False)
with col1:
    st.metric("Giocatori in classifica", len(standings))
with col2:
    st.metric(
        title_most_active,
        nick_most_active,
        delta=f"{max_played} partite",
        delta_color="off",
        delta_arrow="off",
        help="Chi ha giocato più partite"
    )



st.divider()

# ---------- COMPAGNO FORTUNATO E BESTIA NERA ----------
st.subheader("🤝 Compagni fortunati e 😈 bestie nere")
st.caption(
    "Seleziona un giocatore per vedere con quali compagni vince di più "
    "e contro quali avversari perde di più. *Statistiche basate su almeno 3 partite condivise.*"
)

# Selettore giocatore
nicknames = [p['nickname'] for p in standings]
selected_nick = st.selectbox(
    "Giocatore",
    options=nicknames,
    index=0
)

# Recupera l'id del giocatore selezionato
selected_player = next(p for p in standings if p['nickname'] == selected_nick)

from utils.db import get_player_chemistry
chemistry = get_player_chemistry(selected_player['id'], min_matches=3)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🤝 Top compagni")
    if not chemistry['teammates']:
        st.info("Non ci sono ancora abbastanza partite condivise (min. 3) per generare statistiche.")
    else:
        # Top 3 compagni per win_rate
        for i, mate in enumerate(chemistry['teammates'][:3], start=1):
            medal = ["🥇", "🥈", "🥉"][i-1]
            st.markdown(
                f"{medal} **{mate['nickname']}** — "
                f"`{mate['win_rate']:.0f}%` vittorie  \n"
                f"<small>{mate['played_together']} partite insieme: "
                f"{mate['wins']}V / {mate['draws']}P / {mate['losses']}S</small>",
                unsafe_allow_html=True
            )

with col2:
    st.markdown("### 😈 Top bestie nere")
    if not chemistry['opponents']:
        st.info("Non ci sono ancora abbastanza partite contro per generare statistiche.")
    else:
        # Top 3 avversari per loss_rate
        for i, opp in enumerate(chemistry['opponents'][:3], start=1):
            medal = ["🥇", "🥈", "🥉"][i-1]
            st.markdown(
                f"{medal} **{opp['nickname']}** — "
                f"`{opp['loss_rate']:.0f}%` sconfitte  \n"
                f"<small>{opp['played_together']} partite contro: "
                f"{opp['wins']}V / {opp['draws']}P / {opp['losses']}S</small>",
                unsafe_allow_html=True
            )

# Sezione "tutti gli altri" sotto, in due tabelle se ci sono dati
if chemistry['teammates'] or chemistry['opponents']:
    with st.expander("Vedi statistiche complete"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Tutti i compagni**")
            if chemistry['teammates']:
                teammate_data = [
                    {
                        "Compagno": t['nickname'],
                        "Insieme": t['played_together'],
                        "V": t['wins'],
                        "P": t['draws'],
                        "S": t['losses'],
                        "% Vittorie": round(t['win_rate'], 1)
                    }
                    for t in chemistry['teammates']
                ]
                st.dataframe(teammate_data, hide_index=True, use_container_width=True)
            else:
                st.caption("Nessun dato.")
        
        with col2:
            st.markdown("**Tutti gli avversari**")
            if chemistry['opponents']:
                opponent_data = [
                    {
                        "Avversario": o['nickname'],
                        "Contro": o['played_together'],
                        "V": o['wins'],
                        "P": o['draws'],
                        "S": o['losses'],
                        "% Sconfitte": round(o['loss_rate'], 1)
                    }
                    for o in chemistry['opponents']
                ]
                st.dataframe(opponent_data, hide_index=True, use_container_width=True)
            else:
                st.caption("Nessun dato.")