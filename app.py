"""
Entrypoint dell'app: gestisce il login e la navigazione tra le pagine.
"""
import streamlit as st
from utils.auth import get_authenticator, get_current_user_role, hash_password
from utils.db import create_user, get_players_without_user

st.set_page_config(page_title="Calcetto Tracker", page_icon="⚽")

# Crea l'authenticator UNA SOLA VOLTA per run dello script.
# Se è None, significa che non ci sono ancora utenti (primo avvio).
authenticator = get_authenticator()


def home_page():
    """Contenuto della pagina Home."""
    st.title("⚽ Calcetto Tracker")

    # ---------- PRIMO AVVIO: nessun utente esiste ancora ----------
    if authenticator is None:
        st.warning("🚀 Primo avvio: crea l'account admin per iniziare.")

        players_without_user = get_players_without_user()

        with st.form("create_first_user"):
            st.subheader("Crea primo account (sarà admin)")
            
            link_to_player = st.checkbox(
                "Collega a un giocatore esistente?",
                value=bool(players_without_user),
                help="Se sei uno dei giocatori, collegalo per vedere le tue statistiche."
            )
            
            selected_player_id = None
            if link_to_player:
                if not players_without_user:
                    st.warning("Nessun giocatore disponibile. Crea prima un giocatore oppure deseleziona questa opzione.")
                else:
                    nickname_to_id = {p['nickname']: p['id'] for p in players_without_user}
                    selected_nick = st.selectbox(
                        "Giocatore",
                        options=list(nickname_to_id.keys())
                    )
                    selected_player_id = nickname_to_id[selected_nick]
            
            username = st.text_input("Username (per il login)", placeholder="es. luca")
            password = st.text_input("Password", type="password")
            password_confirm = st.text_input("Conferma password", type="password")

            if st.form_submit_button("Crea account admin"):
                if not username or not password:
                    st.error("Compila tutti i campi.")
                elif password != password_confirm:
                    st.error("Le due password non coincidono.")
                elif len(password) < 4:
                    st.error("La password deve essere di almeno 4 caratteri.")
                elif link_to_player and selected_player_id is None:
                    st.error("Seleziona un giocatore o deseleziona il collegamento.")
                else:
                    pwd_hash = hash_password(password)
                    success, msg = create_user(
                        username=username,
                        password_hash=pwd_hash,
                        role='admin',
                        player_id=selected_player_id
                    )
                    if success:
                        st.success(msg + " Ricarica la pagina per effettuare il login.")
                    else:
                        st.error(msg)
        return

    # ---------- LOGIN ----------
    try:
        authenticator.login(location="main")
    except Exception as e:
        st.error(f"Errore login: {e}")

    auth_status = st.session_state.get("authentication_status")

    if auth_status is False:
        st.error("❌ Username o password errati.")
    elif auth_status is None:
        st.info("👆 Inserisci le credenziali per accedere.")
    elif auth_status:
        name = st.session_state.get("name")
        role = get_current_user_role()
        
        role_badges = {
            "admin": "👑 Admin",
            "manager": "🛠️ Manager",
            "viewer": "👁️ Viewer"
        }
        role_badge = role_badges.get(role, "❓")
        
        st.success(f"👋 Benvenuto, **{name}**! ({role_badge})")

        if role == "admin":
            st.markdown("""
            ### Cosa puoi fare:
            - 👥 **Giocatori** — gestisci la rosa del gruppo
            - ⚽ **Nuova Partita** — registra una nuova partita
            - 📋 **Partite** — visualizza tutte le partite giocate
            - 👤 **Utenti** — gestisci gli account di accesso
            """)
        elif role == "manager":
            st.markdown("""
            ### Cosa puoi fare:
            - 👥 **Giocatori** — gestisci la rosa del gruppo
            - ⚽ **Nuova Partita** — registra una nuova partita
            - 📋 **Partite** — visualizza tutte le partite giocate
            """)
        else:
            st.markdown("""
            ### Cosa puoi fare:
            - 👥 **Giocatori** — visualizza la rosa del gruppo
            - 📋 **Partite** — visualizza tutte le partite giocate
            """)

        st.info("Usa il menù a sinistra per navigare.")


# ---------- REGISTRAZIONE PAGINE ----------
home = st.Page(home_page, title="Home", icon="🏠", default=True)
giocatori = st.Page("pages/1_👥_Giocatori.py", title="Giocatori", icon="👥")
nuova_partita = st.Page("pages/2_⚽_Nuova_Partita.py", title="Nuova Partita", icon="⚽")
partite = st.Page("pages/3_📋_Partite.py", title="Partite", icon="📋")
utenti = st.Page("pages/4_👤_Utenti.py", title="Utenti", icon="👤")

# Menu dinamico in base al ruolo
role = get_current_user_role()

if role == "admin":
    pages = [home, giocatori, nuova_partita, partite, utenti]
elif role == "manager":
    pages = [home, giocatori, nuova_partita, partite]
elif role == "viewer":
    pages = [home, giocatori, partite]
else:
    pages = [home]

# Logout globale nella sidebar (visibile su tutte le pagine se loggato)
# Usiamo l'authenticator già creato in cima al file, senza crearne uno nuovo.
if st.session_state.get("authentication_status") and authenticator is not None:
    with st.sidebar:
        st.divider()
        st.caption(f"👤 Loggato come **{st.session_state.get('name')}**")
        authenticator.logout(location="sidebar")

pg = st.navigation(pages)
pg.run()