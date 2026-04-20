import streamlit as st

st.set_page_config(page_title="Calcetto Tracker", page_icon="⚽")

st.title("⚽ Calcetto Tracker")
st.write("Benvenuto! Questa è la web app del nostro gruppo di calcetto.")

st.markdown("""
### Cosa puoi fare:
- 👥 **Giocatori** — gestisci la rosa del gruppo
- *(prossimamente)* ⚽ **Partite** — visualizza e aggiungi partite
- *(prossimamente)* 📊 **Statistiche** — classifiche e numeri
""")

st.info("Usa il menù a sinistra per navigare.")