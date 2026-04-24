"""
Funzioni di autenticazione basate su streamlit-authenticator.
"""
import streamlit as st
import streamlit_authenticator as stauth
from utils.db import get_all_users_for_auth

import os
from dotenv import load_dotenv
load_dotenv()


def get_authenticator():
    """
    Crea e restituisce un oggetto Authenticator configurato con gli utenti del DB.
    Salva anche i ruoli in session_state per controllare i permessi nelle pagine.
    """
    credentials, roles = get_all_users_for_auth()
    
    if not credentials["usernames"]:
        return None
    
    # Salva i ruoli in session_state per riferimento futuro
    st.session_state["_user_roles"] = roles
    
    authenticator = stauth.Authenticate(
        credentials=credentials,
        cookie_name="calcetto_auth",
        cookie_key=os.getenv("COOKIE_KEY", "dev_cookie_key_not_for_production"),
        cookie_expiry_days=30,
    )
    return authenticator


def hash_password(password: str) -> str:
    """Genera l'hash bcrypt di una password."""
    return stauth.Hasher.hash(password)


def get_current_user_role():
    """Restituisce il ruolo dell'utente loggato, o None se non loggato."""
    if not st.session_state.get("authentication_status"):
        return None
    username = st.session_state.get("username")
    roles = st.session_state.get("_user_roles", {})
    return roles.get(username)


def is_admin():
    """True se l'utente loggato è admin."""
    return get_current_user_role() == "admin"

def is_manager():
    """True se l'utente loggato è admin o manager (cioè può modificare dati)."""
    return get_current_user_role() in ("admin", "manager")


def require_login():
    """Richiede che l'utente sia loggato. Blocca la pagina altrimenti."""
    if not st.session_state.get("authentication_status"):
        st.warning("🔒 Devi effettuare il login per accedere a questa pagina.")
        st.info("Torna alla Home per effettuare il login.")
        st.stop()
    
    return {
        "username": st.session_state.get("username"),
        "name": st.session_state.get("name"),
        "role": get_current_user_role(),
    }


def require_admin():
    """Richiede che l'utente sia admin. Blocca la pagina altrimenti."""
    user = require_login()
    if user["role"] != "admin":
        st.error("🚫 Solo gli admin possono accedere a questa pagina.")
        st.info("Se pensi che sia un errore, contatta un amministratore.")
        st.stop()
    return user


def require_manager():
    """Richiede che l'utente sia admin o manager. Blocca altrimenti."""
    user = require_login()
    if user["role"] not in ("admin", "manager"):
        st.error("🚫 Solo admin e manager possono accedere a questa pagina.")
        st.info("Se pensi che sia un errore, contatta un amministratore.")
        st.stop()
    return user