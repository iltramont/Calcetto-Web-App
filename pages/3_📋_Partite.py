"""
Pagina per visualizzare l'elenco delle partite e il dettaglio di ognuna.
"""
import streamlit as st
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.db import get_all_matches, get_match_details, delete_match

from utils.auth import require_login, is_manager

st.set_page_config(page_title="Partite", page_icon="📋")
user = require_login()
can_edit = is_manager()

st.title("📋 Partite")

matches = get_all_matches()

if not matches:
    st.info("Nessuna partita ancora registrata. Crea la prima dalla pagina ⚽ Nuova Partita!")
    st.stop()

st.write(f"**Totale partite giocate: {len(matches)}**")
st.divider()

# ---------- LISTA PARTITE ----------
# Mostriamo ogni partita in un expander con dentro tutti i dettagli
for match in matches:
    # Formatta la data in italiano (dd/mm/yyyy)
    date_obj = datetime.strptime(match['match_date'], "%Y-%m-%d").date()
    date_str = date_obj.strftime("%d/%m/%Y")
    
    # Etichetta dell'expander con data e punteggio
    location_str = f" — {match['location']}" if match['location'] else ""
    label = f"📅 {date_str}{location_str}  →  🟢 {match['score_a']} - {match['score_b']} 🔴"
    
    with st.expander(label):
        # Carica i dettagli completi solo quando l'utente apre l'expander
        details = get_match_details(match['id'])
        
        if details['notes']:
            st.caption(f"📝 *{details['notes']}*")
        
        # Punteggio in grande
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.markdown(f"<h2 style='text-align: center;'>🟢 {details['score_a']}</h2>", 
                       unsafe_allow_html=True)
        with col2:
            st.markdown("<h3 style='text-align: center; padding-top: 10px;'>vs</h3>", 
                       unsafe_allow_html=True)
        with col3:
            st.markdown(f"<h2 style='text-align: center;'>{details['score_b']} 🔴</h2>", 
                       unsafe_allow_html=True)
        
        st.divider()
        
        # Squadre
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 🟢 Squadra A")
            for p in details['team_a']:
                # Conta i goal di questo giocatore in questa partita
                player_goals = sum(1 for g in details['goals'] 
                                  if g['scorer_nickname'] == p['nickname'] 
                                  and not g['is_own_goal'])
                goals_str = f" ⚽×{player_goals}" if player_goals > 0 else ""
                st.write(f"• **{p['nickname']}**{goals_str}")
        
        with col_b:
            st.markdown("### 🔴 Squadra B")
            for p in details['team_b']:
                player_goals = sum(1 for g in details['goals'] 
                                  if g['scorer_nickname'] == p['nickname'] 
                                  and not g['is_own_goal'])
                goals_str = f" ⚽×{player_goals}" if player_goals > 0 else ""
                st.write(f"• **{p['nickname']}**{goals_str}")
        
        # Lista goal cronologica
        if details['goals']:
            st.divider()
            st.markdown("### ⚽ Marcatori")
            for i, goal in enumerate(details['goals'], start=1):
                team_emoji = "🟢" if goal['team'] == 'A' else "🔴"
                
                if goal['is_own_goal']:
                    line = f"{i}. {team_emoji} ⚠️ **Autogoal di {goal['scorer_nickname']}**"
                elif goal['scorer_nickname'] is None:
                    line = f"{i}. {team_emoji} *Goal sconosciuto*"
                else:
                    assist_str = f" *(assist: {goal['assist_nickname']})*" if goal['assist_nickname'] else ""
                    line = f"{i}. {team_emoji} **{goal['scorer_nickname']}**{assist_str}"
                
                st.write(line)
        else:
            st.info("Nessun goal registrato per questa partita.")
        
        # Azioni: modifica + elimina (solo manager/admin)
        if can_edit:
            st.divider()
            col_edit, col_del = st.columns(2)
            
            # --- Bottone Modifica ---
            with col_edit:
                if st.button("✏️ Modifica partita", key=f"edit_btn_{match['id']}", use_container_width=True):
                    st.session_state["editing_match_id"] = match['id']
                    # Pulisci eventuale stato residuo di una modifica precedente
                    st.session_state.pop("edit_goals", None)
                    for k in list(st.session_state.keys()):
                        if k.startswith("edit_init_"):
                            st.session_state.pop(k, None)
                    st.switch_page("pages/5_✏️_Modifica_Partita.py")
            
            # --- Bottone Elimina (con conferma a doppio click) ---
            with col_del:
                confirm_key = f"confirm_delete_{match['id']}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False
                
                if not st.session_state[confirm_key]:
                    if st.button("🗑️ Elimina partita", key=f"del_btn_{match['id']}", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.warning("⚠️ Sei sicuro?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Sì", key=f"confirm_yes_{match['id']}", type="primary", use_container_width=True):
                            success, msg = delete_match(match['id'])
                            if success:
                                st.success(msg)
                                del st.session_state[confirm_key]
                                st.rerun()
                            else:
                                st.error(msg)
                    with c2:
                        if st.button("❌ No", key=f"confirm_no_{match['id']}", use_container_width=True):
                            st.session_state[confirm_key] = False
                            st.rerun()