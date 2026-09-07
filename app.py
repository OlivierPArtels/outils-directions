import streamlit as st
from classe_maternelle import determine_entree_accueil


# ============================================================
# CONFIGURATION DE LA PAGE
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
        "Doc MDP"
    ]
)


# ============================================================
# ACCUEIL
# ============================================================

if outil == "Accueil":

    st.title("🏫 Outils pour directions d'école")

    st.write(
        "Choisissez un outil dans le menu à gauche."
    )

    st.markdown(
        """
        - **C4 Assistant** — calculateur de C4
        - **Classe Maternelle** — détermine la classe maternelle de l'enfant
        - **Doc MDP** — détermine les documents administratifs nécessaires selon la situation du membre du personnel
        """
    )


# ============================================================
# C4 ASSISTANT
# ============================================================

elif outil == "C4 Assistant":

    st.title("📄 C4 Assistant")

    st.info(
        "Cet outil est en cours de développement."
    )


# ============================================================
# CLASSE MATERNELLE
# ============================================================

elif outil == "Classe Maternelle":

    st.title("👶 Classe Maternelle")

    st.write(
        "Détermine la classe maternelle de l'enfant et, "
        "si nécessaire, sa première date possible d'entrée à l'école."
    )

    date_naissance = st.date_input(
        "Date de naissance de l'enfant",
        format="DD/MM/YYYY"
    )

    if st.button("Calculer"):

        resultat = determine_entree_accueil(
            date_naissance
        )

        if resultat is None:

            st.error(
                "Impossible de déterminer la situation pour cette date."
            )

        else:

            st.markdown(
                f"**Date de naissance :** "
                f"{resultat['dob'].strftime('%d/%m/%Y')}"
            )

            # ------------------------------------------------
            # DATE DES 2 ANS ET DEMI
            # ------------------------------------------------

            if resultat["theoretical"] is not None:

                st.markdown(
                    f"**Date des 2 ans et demi :** "
                    f"{resultat['theoretical'].strftime('%d/%m/%Y')}"
                )

            # ------------------------------------------------
            # CLASSE MATERNELLE
            # ------------------------------------------------

            st.markdown(
                f"**Classe maternelle :** "
                f"{resultat['classe']}"
            )

            # ------------------------------------------------
            # PREMIÈRE DATE POSSIBLE D'ENTRÉE
            # ------------------------------------------------

            if resultat["entry_date"] is not None:

                st.markdown(
                    f"**Première date possible d'entrée :** "
                    f"{resultat['entry_date'].strftime('%d/%m/%Y')}"
                )

            # ------------------------------------------------
            # EXPLICATION
            # ------------------------------------------------

            if resultat["explanation"] is not None:

                st.info(
                    resultat["explanation"]
                )


# ============================================================
# DOC MDP
# ============================================================

elif outil == "Doc MDP":

    st.title("📑 Doc MDP")

    st.write(
        "Détermine les documents administratifs à préparer "
        "et à transmettre selon la situation du membre du personnel."
    )

    st.info(
        "Cet outil est en cours de développement."
    )
