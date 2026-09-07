import streamlit as st

st.set_page_config(page_title="Outils Directions", page_icon="🏫", layout="centered")

st.sidebar.title("🏫 Outils Directions")
outil = st.sidebar.radio(
    "Choisir un outil",
    ["Accueil", "C4 Assistant", "Classe Maternelle", "Doc MDP", "Congés MDP"]
)

if outil == "Accueil":
    st.title("Outils pour directions d'école")
    st.write("Bienvenue ! Choisissez un outil dans le menu à gauche.")
    st.markdown("""
    - **C4 Assistant** — calculateur de C4
    - **Classe Maternelle** — orientation de l'élève selon son âge
    - **Doc MDP** — documents à communiquer
    - **Congés MDP** — congés dont bénéficie un membre du personnel
    """)

elif outil == "C4 Assistant":
    st.title("📄 C4 Assistant")
    st.info("Outil en construction — la logique de calcul sera ajoutée ici.")

elif outil == "Classe Maternelle":
    st.title("🧒 Classe Maternelle")
    st.info("Outil en construction — la logique de calcul sera ajoutée ici.")

elif outil == "Doc MDP":
    st.title("📁 Doc MDP")
    st.info("Outil en construction — la liste des documents sera ajoutée ici.")

elif outil == "Congés MDP":
    st.title("🗓️ Congés MDP")
    st.info("Outil en construction — l'import Excel et le calcul seront ajoutés ici.")
