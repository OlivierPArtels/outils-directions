import streamlit as st
from classe_maternelle import determine_entree_accueil

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
    st.write("Calcule la date d'entrée possible en classe d'accueil selon la date de naissance.")

    dob = st.date_input("Date de naissance de l'enfant", format="DD/MM/YYYY")

    if st.button("Calculer"):
        result = determine_entree_accueil(dob)
        if result is None:
            st.warning("Cet enfant n'est concerné par une entrée en classe d'accueil pendant aucune des trois années scolaires couvertes (2026-2027, 2027-2028, 2028-2029).")
        else:
            st.markdown(f"""
**Date de naissance :** {result['dob'].strftime('%d/%m/%Y')}
**2 ans et 6 mois :** {result['theoretical'].strftime('%d/%m/%Y')}
**Année scolaire concernée :** {result['school_year']}
**Classe :** Accueil
**Date d'entrée possible :** {result['entry_date'].strftime('%d/%m/%Y')}
**Explication :** {result['explanation']}
""")

elif outil == "Doc MDP":
    st.title("📁 Doc MDP")
    st.info("Outil en construction — la liste des documents sera ajoutée ici.")

elif outil == "Congés MDP":
    st.title("🗓️ Congés MDP")
    st.info("Outil en construction — l'import Excel et le calcul seront ajoutés ici.")
