"""
Pagina per modificare una partita esistente.
Accessibile via bottone dalla pagina Partite.
"""
import streamlit as st
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import require_manager
from utils.db import get_all_players, get_match_details, update_match

st.set_page_config(page_title="Modifica Partita", page_icon="✏️")
user = require_manager()

st.title("✏️ Modifica Partita")

# L'id della partita viene passato tramite session_state (vedi pagina Partite)
match_id = st.session_state.get("editing_match_id")

if match_id is None:
    st.warning("Nessuna partita selezionata.")
    st.info("Torna alla pagina **📋 Partite** e clicca su **Modifica** sulla partita che vuoi editare.")
    st.stop()

details = get_match_details(match_id)
if details is None:
    st.error("Partita non trovata.")
    st.session_state.pop("editing_match_id", None)
    st.stop()

# Carica lista giocatori
players = get_all_players()
id_to_nickname = {p['id']: p['nickname'] for p in players}
nickname_to_id = {p['nickname']: p['id'] for p in players}
all_nicknames = [p['nickname'] for p in players]

# ---------- INIZIALIZZAZIONE SESSION_STATE ----------
# Quando apriamo la pagina per la prima volta per questa partita,
# precarichiamo i goal esistenti in session_state
init_key = f"edit_init_{match_id}"
if not st.session_state.get(init_key):
    # Popola i goal di partenza
    st.session_state.edit_goals = []
    for g in details['goals']:
        st.session_state.edit_goals.append({
            "scorer_nickname": g['scorer_nickname'],
            "scorer_id": nickname_to_id.get(g['scorer_nickname']) if g['scorer_nickname'] else None,
            "assist_nickname": g['assist_nickname'],
            "assist_id": nickname_to_id.get(g['assist_nickname']) if g['assist_nickname'] else None,
            "team": g['team'],
            "is_own_goal": bool(g['is_own_goal'])
        })
    st.session_state[init_key] = True

st.caption(f"Stai modificando la partita del **{details['date']}** — ID: {match_id}")

# ---------- DATI BASE ----------
st.subheader("📅 Dati della partita")

col1, col2 = st.columns(2)
with col1:
    current_date = datetime.strptime(details['date'], "%Y-%m-%d").date()
    new_date = st.date_input("Data", value=current_date, key="edit_date")
with col2:
    new_location = st.text_input("Luogo", value=details['location'] or "", key="edit_location")

new_notes = st.text_area("Note", value=details['notes'] or "", key="edit_notes")

st.divider()

# ---------- SQUADRE ----------
st.subheader("👥 Composizione squadre")

default_team_a = [p['nickname'] for p in details['team_a']]
default_team_b = [p['nickname'] for p in details['team_b']]

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🟢 Squadra A")
    team_a_nicks = st.multiselect(
        "Giocatori squadra A",
        options=all_nicknames,
        default=default_team_a,
        key="edit_team_a"
    )
with col2:
    st.markdown("### 🔴 Squadra B")
    team_b_nicks = st.multiselect(
        "Giocatori squadra B",
        options=all_nicknames,
        default=default_team_b,
        key="edit_team_b"
    )

# Controllo duplicati
duplicates = set(team_a_nicks) & set(team_b_nicks)
if duplicates:
    st.error(f"⚠️ Questi giocatori sono in entrambe le squadre: {', '.join(duplicates)}.")

# Riepilogo
if team_a_nicks or team_b_nicks:
    st.info(f"**Squadra A:** {len(team_a_nicks)} giocatori — **Squadra B:** {len(team_b_nicks)} giocatori")

# Avviso se un giocatore con goal sta per essere rimosso
players_in_match = set(team_a_nicks) | set(team_b_nicks)
scorers_with_goals = {
    g['scorer_nickname'] for g in st.session_state.edit_goals 
    if g['scorer_nickname'] is not None
}
removed_scorers = scorers_with_goals - players_in_match

if removed_scorers:
    st.warning(
        f"⚠️ Stai rimuovendo questi giocatori che avevano segnato: **{', '.join(removed_scorers)}**. "
        f"Al salvataggio, i loro goal diventeranno 'goal sconosciuti'."
    )

st.divider()

# ---------- GOAL ----------
st.subheader("⚽ Goal")

all_players_in_match = team_a_nicks + team_b_nicks

if not all_players_in_match:
    st.info("Seleziona prima i giocatori delle due squadre.")
else:
    # Radio FUORI dal form per reagire dinamicamente
    goal_type = st.radio(
        "Tipo di goal",
        options=["Normale", "Autogoal", "Sconosciuto (senza marcatore)"],
        horizontal=True,
        key="edit_goal_type"
    )
    
    with st.form("add_goal_edit_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        if goal_type == "Normale":
            with col1:
                scorer = st.selectbox(
                    "Marcatore",
                    options=all_players_in_match,
                    key="edit_normal_scorer"
                )
            with col2:
                # Mettiamo tutte le opzioni (incluso il marcatore, sarà validato al submit)
                assist = st.selectbox(
                    "Assist (opzionale)",
                    options=["(nessuno)"] + all_players_in_match,
                    key="edit_normal_assist"
                )
        elif goal_type == "Autogoal":
            with col1:
                scorer = st.selectbox(
                    "Chi ha fatto autogoal",
                    options=all_players_in_match,
                    help="Il goal va alla squadra avversaria"
                )
            with col2:
                st.caption("🔄 Il punto va alla squadra avversaria")
            assist = "(nessuno)"
        else:
            with col1:
                scoring_team = st.selectbox(
                    "Quale squadra ha segnato?",
                    options=["Squadra A 🟢", "Squadra B 🔴"]
                )
            with col2:
                st.caption("⚠️ Goal senza marcatore")
            scorer = None
            assist = "(nessuno)"
        
        if st.form_submit_button("➕ Aggiungi goal"):
            if goal_type == "Normale":
                # Validazione: marcatore e assist non possono essere la stessa persona
                if assist != "(nessuno)" and assist == scorer:
                    st.error("Il marcatore e l'assistman non possono essere la stessa persona.")
                else:
                    team = "A" if scorer in team_a_nicks else "B"
                    st.session_state.edit_goals.append({
                        "scorer_nickname": scorer,
                        "scorer_id": nickname_to_id[scorer],
                        "assist_nickname": assist if assist != "(nessuno)" else None,
                        "assist_id": nickname_to_id[assist] if assist != "(nessuno)" else None,
                        "team": team,
                        "is_own_goal": False
                    })
            elif goal_type == "Autogoal":
                scorer_team = "A" if scorer in team_a_nicks else "B"
                team = "B" if scorer_team == "A" else "A"
                st.session_state.edit_goals.append({
                    "scorer_nickname": scorer,
                    "scorer_id": nickname_to_id[scorer],
                    "assist_nickname": None,
                    "assist_id": None,
                    "team": team,
                    "is_own_goal": True
                })
            else:
                team = "A" if scoring_team.startswith("Squadra A") else "B"
                st.session_state.edit_goals.append({
                    "scorer_nickname": None,
                    "scorer_id": None,
                    "assist_nickname": None,
                    "assist_id": None,
                    "team": team,
                    "is_own_goal": False
                })

# DEBUG TEMPORANEO
#st.write("🐛 DEBUG edit_goals:", st.session_state.edit_goals)

# Mostra i goal correnti
if st.session_state.edit_goals:
    st.markdown("**Goal della partita:**")
    goals_a = sum(1 for g in st.session_state.edit_goals if g['team'] == 'A')
    goals_b = sum(1 for g in st.session_state.edit_goals if g['team'] == 'B')
    st.markdown(f"### 🟢 {goals_a} — {goals_b} 🔴")
    
    for i, goal in enumerate(st.session_state.edit_goals):
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
            if st.button("🗑️", key=f"rm_edit_goal_{i}"):
                st.session_state.edit_goals.pop(i)
                st.rerun()

st.divider()

# ---------- AZIONI ----------
col1, col2 = st.columns(2)

with col1:
    if st.button("💾 Salva modifiche", type="primary", use_container_width=True):
        duplicates = set(team_a_nicks) & set(team_b_nicks)
        if duplicates:
            st.error(f"⚠️ Rimuovi i giocatori duplicati: {', '.join(duplicates)}")
        elif not team_a_nicks or not team_b_nicks:
            st.error("Entrambe le squadre devono avere almeno un giocatore.")
        else:
            team_a_ids = [nickname_to_id[n] for n in team_a_nicks]
            team_b_ids = [nickname_to_id[n] for n in team_b_nicks]
            
            success, msg = update_match(
                match_id=match_id,
                match_date=new_date,
                location=new_location,
                notes=new_notes,
                team_a_ids=team_a_ids,
                team_b_ids=team_b_ids,
                goals=st.session_state.edit_goals
            )
            
            if success:
                st.success("✅ " + msg)
                # Pulisci lo state della modifica
                st.session_state.pop("editing_match_id", None)
                st.session_state.pop(init_key, None)
                st.session_state.pop("edit_goals", None)
                st.balloons()
                st.info("Torna alla pagina 📋 Partite per vedere le modifiche.")
            else:
                st.error(msg)

with col2:
    if st.button("❌ Annulla modifiche", use_container_width=True):
        st.session_state.pop("editing_match_id", None)
        st.session_state.pop(init_key, None)
        st.session_state.pop("edit_goals", None)
        st.switch_page("pages/3_📋_Partite.py")