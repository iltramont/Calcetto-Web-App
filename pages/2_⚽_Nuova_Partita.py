"""
Pagina per inserire una nuova partita.
"""
import streamlit as st
import sys
from datetime import date
from pathlib import Path
from utils.auth import require_manager

sys.path.append(str(Path(__file__).parent.parent))

from utils.db import get_all_players, create_match

st.set_page_config(page_title="Nuova Partita", page_icon="⚽")
user = require_manager()

st.title("⚽ Nuova Partita")

# Carica tutti i giocatori disponibili
players = get_all_players()

if len(players) < 2:
    st.warning("Aggiungi almeno 2 giocatori prima di creare una partita.")
    st.stop()

# Dizionari di comodo per passare da id a nickname e viceversa
id_to_nickname = {p['id']: p['nickname'] for p in players}
nickname_to_id = {p['nickname']: p['id'] for p in players}

# ---------- DATI BASE DELLA PARTITA ----------
st.subheader("📅 Dati della partita")

col1, col2 = st.columns(2)
with col1:
    match_date = st.date_input("Data", value=date.today())
with col2:
    location = st.text_input("Luogo (opzionale)", placeholder="es. Centro Sportivo X")

notes = st.text_area("Note (opzionale)", placeholder="es. Partita combattuta, brutto tempo...")

st.divider()

# ---------- SELEZIONE SQUADRE ----------
st.subheader("👥 Composizione squadre")
st.caption("Seleziona i giocatori per ogni squadra. Lo stesso giocatore non può stare in entrambe.")

all_nicknames = [p['nickname'] for p in players]

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🟢 Squadra A")
    team_a_nicks = st.multiselect(
        "Giocatori squadra A",
        options=all_nicknames,
        key="team_a"
    )

with col2:
    st.markdown("### 🔴 Squadra B")
    team_b_nicks = st.multiselect(
        "Giocatori squadra B",
        options=all_nicknames,
        key="team_b"
    )

# Controlla se ci sono giocatori in entrambe le squadre
duplicates = set(team_a_nicks) & set(team_b_nicks)
if duplicates:
    st.error(f"⚠️ Questi giocatori sono in entrambe le squadre: {', '.join(duplicates)}. Rimuovili da una delle due.")

# Mostra un riepilogo
if team_a_nicks or team_b_nicks:
    st.info(f"**Squadra A:** {len(team_a_nicks)} giocatori — **Squadra B:** {len(team_b_nicks)} giocatori")
    
st.divider()

# ---------- INSERIMENTO GOAL ----------
st.subheader("⚽ Goal")
st.caption("Aggiungi i goal segnati durante la partita.")

if "goals" not in st.session_state:
    st.session_state.goals = []

all_players_in_match = team_a_nicks + team_b_nicks

if not all_players_in_match:
    st.info("Seleziona prima i giocatori delle due squadre.")
else:
    with st.form("add_goal_form", clear_on_submit=True):
        # Tipo di goal
        goal_type = st.radio(
            "Tipo di goal",
            options=["Normale", "Autogoal", "Sconosciuto (senza marcatore)"],
            horizontal=True
        )
        
        col1, col2 = st.columns(2)
        
        if goal_type == "Normale":
            with col1:
                scorer = st.selectbox("Marcatore", options=all_players_in_match)
            with col2:
                assist_options = ["(nessuno)"] + [n for n in all_players_in_match if n != scorer]
                assist = st.selectbox("Assist (opzionale)", options=assist_options)
        
        elif goal_type == "Autogoal":
            with col1:
                scorer = st.selectbox(
                    "Chi ha fatto autogoal", 
                    options=all_players_in_match,
                    help="Il goal andrà a favore della squadra avversaria"
                )
            with col2:
                st.write("")  # spazio vuoto per allineamento
                st.caption("🔄 Il punto va alla squadra avversaria")
            assist = "(nessuno)"  # niente assist per autogoal
        
        else:  # Sconosciuto
            with col1:
                scoring_team = st.selectbox(
                    "Quale squadra ha segnato?",
                    options=["Squadra A 🟢", "Squadra B 🔴"]
                )
            with col2:
                st.caption("⚠️ Goal senza marcatore registrato")
            scorer = None
            assist = "(nessuno)"
        
        add_goal_btn = st.form_submit_button("➕ Aggiungi goal")
        
        if add_goal_btn:
            if goal_type == "Normale":
                team = "A" if scorer in team_a_nicks else "B"
                st.session_state.goals.append({
                    "scorer_nickname": scorer,
                    "scorer_id": nickname_to_id[scorer],
                    "assist_nickname": assist if assist != "(nessuno)" else None,
                    "assist_id": nickname_to_id[assist] if assist != "(nessuno)" else None,
                    "team": team,
                    "is_own_goal": False
                })
            elif goal_type == "Autogoal":
                # La squadra che prende il punto è quella AVVERSARIA al marcatore
                scorer_team = "A" if scorer in team_a_nicks else "B"
                team = "B" if scorer_team == "A" else "A"
                st.session_state.goals.append({
                    "scorer_nickname": scorer,
                    "scorer_id": nickname_to_id[scorer],
                    "assist_nickname": None,
                    "assist_id": None,
                    "team": team,
                    "is_own_goal": True
                })
            else:  # Sconosciuto
                team = "A" if scoring_team.startswith("Squadra A") else "B"
                st.session_state.goals.append({
                    "scorer_nickname": None,
                    "scorer_id": None,
                    "assist_nickname": None,
                    "assist_id": None,
                    "team": team,
                    "is_own_goal": False
                })

# Mostra i goal aggiunti
if st.session_state.goals:
    st.markdown("**Goal aggiunti:**")
    
    goals_a = sum(1 for g in st.session_state.goals if g['team'] == 'A')
    goals_b = sum(1 for g in st.session_state.goals if g['team'] == 'B')
    st.markdown(f"### 🟢 {goals_a} — {goals_b} 🔴")
    
    for i, goal in enumerate(st.session_state.goals):
        col1, col2 = st.columns([5, 1])
        with col1:
            team_emoji = "🟢" if goal['team'] == 'A' else "🔴"
            
            if goal['is_own_goal']:
                label = f"{team_emoji} **Autogoal di {goal['scorer_nickname']}** ⚠️"
            elif goal['scorer_nickname'] is None:
                label = f"{team_emoji} *Goal sconosciuto*"
            else:
                assist_str = f" (assist: {goal['assist_nickname']})" if goal['assist_nickname'] else ""
                label = f"{team_emoji} **{goal['scorer_nickname']}**{assist_str}"
            
            st.write(label)
        with col2:
            if st.button("🗑️", key=f"rm_goal_{i}"):
                st.session_state.goals.pop(i)
                st.rerun()

st.divider()

# ---------- SALVATAGGIO ----------
if st.button("💾 Salva partita", type="primary", use_container_width=True):
    # Validazioni
    duplicates = set(team_a_nicks) & set(team_b_nicks)
    if duplicates:
        st.error(f"⚠️ Rimuovi i giocatori duplicati prima di salvare: {', '.join(duplicates)}")
    elif not team_a_nicks or not team_b_nicks:
        st.error("Entrambe le squadre devono avere almeno un giocatore.")
    else:
        team_a_ids = [nickname_to_id[n] for n in team_a_nicks]
        team_b_ids = [nickname_to_id[n] for n in team_b_nicks]
        
        success, result = create_match(
            match_date=match_date,
            location=location,
            notes=notes,
            team_a_ids=team_a_ids,
            team_b_ids=team_b_ids,
            goals=st.session_state.goals
        )
        
        if success:
            st.success(f"✅ Partita salvata correttamente! (ID: {result})")
            st.session_state.goals = []
            st.balloons()
        else:
            st.error(result)