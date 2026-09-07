import streamlit as st
from classe_maternelle import determine_entree_accueil


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Outils Directions",
    page_icon="🏫",
    layout="centered"
)


# ============================================================
# MENU LATÉRAL
# ============================================================

st.sidebar.title("🏫 Outils Directions")

outil = st.sidebar.radio(
    "Choisir un outil",
    [
        "Accueil",
        "C4 Assistant",
        "Classe Maternelle",
        "Doc MDP",
        "Congés MDP"
    ]
)


# ============================================================
# ACCUEIL
# ============================================================

if outil == "Accueil":

    st.title("Outils pour directions d'école")

    st.write(
        "Bienvenue ! Choisissez un outil dans le menu à gauche."
    )

    st.markdown("""
    - **C4 Assistant** — calculateur de C4
    - **Classe Maternelle** — orientation de l'élève selon son âge
    - **Doc MDP** — documents à communiquer
    - **Congés MDP** — congés dont bénéficie un membre du personnel
    """)


# ============================================================
# C4 ASSISTANT
# ============================================================

elif outil == "C4 Assistant":

    st.title("📄 C4 Assistant")

    st.info(
        "Outil en construction — la logique de calcul sera ajoutée ici."
    )


# ============================================================
# CLASSE MATERNELLE
# ============================================================

elif outil == "Classe Maternelle":

    st.title("🧒 Classe Maternelle")

    st.write(
        "Détermine la classe maternelle de l'enfant et, "
        "si nécessaire, sa première date possible d'entrée à l'école."
    )

    dob = st.date_input(
        "Date de naissance de l'enfant",
        format="DD/MM/YYYY"
    )

    if st.button("Calculer"):

        result = determine_entree_accueil(dob)

        if result is None:

            st.warning(
                "La date introduite ne peut pas être traitée "
                "avec les calendriers scolaires actuellement disponibles."
            )

        else:

            # ------------------------------------------------
            # DATE DE NAISSANCE
            # ------------------------------------------------

            st.write(
                f"**Date de naissance :** "
                f"{result['dob'].strftime('%d/%m/%Y')}"
            )

            # ------------------------------------------------
            # DATE DES 2 ANS ET DEMI
            # Affichée uniquement si l'enfant
            # n'a pas encore atteint cet âge
            # ------------------------------------------------

            if result["theoretical"] is not None:

                st.write(
                    f"**L'enfant aura 2 ans et demi le :** "
                    f"{result['theoretical'].strftime('%d/%m/%Y')}"
                )

            # ------------------------------------------------
            # CLASSE
            # ------------------------------------------------

            st.write(
                f"**Classe maternelle :** "
                f"{result['classe']}"
            )

            # ------------------------------------------------
            # DATE D'ENTRÉE
            # Affichée uniquement si l'enfant
            # n'est pas encore scolarisable
            # ------------------------------------------------

            if result["entry_date"] is not None:

                st.write(
                    f"**Date d'entrée possible en accueil :** "
                    f"{result['entry_date'].strftime('%d/%m/%Y')}"
                )


# ============================================================
# DOCUMENTS MDP
# ============================================================

elif outil == "Doc MDP":

    st.title("📁 Doc MDP")

    st.info(
        "Outil en construction — la liste des documents sera ajoutée ici."
    )


# ============================================================
# CONGÉS MDP
# ============================================================

elif outil == "Congés MDP":

    st.title("🗓️ Congés MDP")

    st.info(
        "Outil en construction — l'import Excel et le calcul seront ajoutés ici."
    )
