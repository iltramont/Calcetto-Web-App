"""
Pagina di gestione utenti (solo admin).
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import require_admin, hash_password
from utils.db import (
    get_all_users, create_user, update_user_role, delete_user,
    count_admins, get_players_without_user
)

st.set_page_config(page_title="Utenti", page_icon="👤")
user = require_admin()

st.title("👤 Gestione Utenti")
st.caption("Qui puoi creare, modificare ed eliminare gli account utente.")

# ---------- CREA NUOVO UTENTE ----------
st.subheader("➕ Nuovo account")

players_without_user = get_players_without_user()

with st.form("create_user_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("Username", placeholder="es. marco")
    with col2:
        new_role = st.selectbox("Ruolo", options=["viewer", "manager", "admin"])
    
    new_password = st.text_input("Password iniziale", type="password", 
                                 placeholder="min. 4 caratteri")
    
    link_to_player = st.checkbox(
        "Collega a un giocatore?",
        help="Spunta se questo utente è uno dei giocatori del gruppo."
    )
    
    selected_player_id = None
    if link_to_player:
        if not players_without_user:
            st.info("Nessun giocatore disponibile da collegare.")
        else:
            nick_to_id = {p['nickname']: p['id'] for p in players_without_user}
            selected_nick = st.selectbox("Giocatore", options=list(nick_to_id.keys()))
            selected_player_id = nick_to_id[selected_nick]
    
    if st.form_submit_button("Crea account"):
        if not new_username or not new_password:
            st.error("Compila username e password.")
        elif len(new_password) < 4:
            st.error("La password deve essere di almeno 4 caratteri.")
        else:
            pwd_hash = hash_password(new_password)
            success, msg = create_user(
                username=new_username,
                password_hash=pwd_hash,
                role=new_role,
                player_id=selected_player_id
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

st.divider()

# ---------- LISTA UTENTI ----------
st.subheader("Utenti esistenti")

users = get_all_users()
current_username = user["username"]
admin_count = count_admins()

for u in users:
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        
        with col1:
            role_emojis = {"admin": "👑", "manager": "🛠️", "viewer": "👁️"}
            role_emoji = role_emojis.get(u['role'], "❓")
            player_str = f" → {u['player_nickname']}" if u['player_nickname'] else ""
            is_you = " **(tu)**" if u['username'] == current_username else ""
            st.markdown(f"{role_emoji} **{u['username']}**{player_str}{is_you}")
        
        with col2:
            st.caption(f"Ruolo: `{u['role']}`")
        
        with col3:
            # Cambia ruolo tramite selectbox
            would_leave_no_admin = (u['role'] == "admin" and admin_count == 1)
            
            if would_leave_no_admin:
                st.caption("⚠️ Ultimo admin")
            else:
                role_options = ["admin", "manager", "viewer"]
                current_idx = role_options.index(u['role'])
                new_role_choice = st.selectbox(
                    "Ruolo",
                    options=role_options,
                    index=current_idx,
                    key=f"role_sel_{u['id']}",
                    label_visibility="collapsed"
                )
                if new_role_choice != u['role']:
                    if st.button(
                        f"💾 Salva", 
                        key=f"save_role_{u['id']}"
                    ):
                        success, msg = update_user_role(u['id'], new_role_choice)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        
        with col4:
            # Bottone elimina
            if u['username'] == current_username:
                st.caption("🔒 Non puoi eliminare te stesso")
            elif u['role'] == "admin" and admin_count == 1:
                st.caption("⚠️ Ultimo admin")
            else:
                if st.button("🗑️ Elimina", key=f"del_user_{u['id']}"):
                    success, msg = delete_user(u['id'])
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)