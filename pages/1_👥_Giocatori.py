"""
Pagina per gestire i giocatori del gruppo.
"""
import streamlit as st
import sys
from pathlib import Path

from utils.auth import require_login, is_manager

# Aggiungi la cartella radice al path per poter importare utils
sys.path.append(str(Path(__file__).parent.parent))

from utils.db import get_all_players, add_player, delete_player

st.set_page_config(page_title="Giocatori", page_icon="👥")
user = require_login()
can_edit = is_manager()

st.title("👥 Giocatori")
st.write("Gestisci i giocatori del gruppo.")

# ---------- FORM PER AGGIUNGERE UN GIOCATORE ----------
if can_edit:
    st.subheader("Aggiungi nuovo giocatore")
    
    with st.form("add_player_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nome completo", placeholder="es. Luca Rossi")
        with col2:
            nickname = st.text_input("Nickname", placeholder="es. Luke")
        
        submitted = st.form_submit_button("➕ Aggiungi")
        
        if submitted:
            if not name or not nickname:
                st.error("Compila sia il nome che il nickname.")
            else:
                success, message = add_player(name, nickname)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.divider()

# ---------- LISTA DEI GIOCATORI ----------
st.subheader("Lista giocatori")

players = get_all_players()

if not players:
    st.info("Nessun giocatore ancora inserito. Aggiungi il primo con il form qui sopra!")
else:
    st.write(f"**Totale: {len(players)} giocatori**")
    
    for player in players:
        col1, col2, col3 = st.columns([3, 3, 1])
        with col1:
            st.write(f"**{player['nickname']}**")
        with col2:
            st.write(player['name'])
        with col3:
            if can_edit:
                # Un bottoncino per eliminare, con conferma implicita
                if st.button("🗑️", key=f"del_{player['id']}", help="Elimina giocatore"):
                    success, message = delete_player(player['id'])
                    if success:
                        st.success(message)
                        st.rerun()  # ricarica la pagina per aggiornare la lista
                    else:
                        st.error(message)
                    
                    
st.divider()