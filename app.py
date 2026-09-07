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
        "Doc MDP",
        "Congés MDP"
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
        - **Classe Maternelle** — détermine la classe maternelle et la date éventuelle d'entrée
        - **Doc MDP** — détermine les documents à communiquer
        - **Congés MDP** — détermine les congés dont peut bénéficier un membre du personnel
        """
    )


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

    # --------------------------------------------------------
    # DATE DE NAISSANCE
    # --------------------------------------------------------

    dob = st.date_input(
        "Date de naissance de l'enfant",
        format="DD/MM/YYYY"
    )

    # --------------------------------------------------------
    # BOUTON DE CALCUL
    # --------------------------------------------------------

    if st.button("Calculer"):

        result = determine_entree_accueil(dob)

        # ----------------------------------------------------
        # CAS NON TRAITABLE
        # ----------------------------------------------------

        if result is None:

            st.warning(
                "La date introduite ne peut pas être traitée "
                "avec les calendriers scolaires actuellement disponibles."
            )

        # ----------------------------------------------------
        # RÉSULTAT
        # ----------------------------------------------------

        else:

            st.write("")

            # ------------------------------------------------
            # DATE DE NAISSANCE
            # ------------------------------------------------

            st.write(
                f"**Date de naissance :** "
                f"{result['dob'].strftime('%d/%m/%Y')}"
            )

            # ------------------------------------------------
            # DATE DES 2 ANS ET DEMI
            #
            # Affichée uniquement si l'enfant
            # n'a pas encore atteint 2 ans et demi.
            # ------------------------------------------------

            if result["theoretical"] is not None:

                st.write(
                    f"**L'enfant aura 2 ans et demi le :** "
                    f"{result['theoretical'].strftime('%d/%m/%Y')}"
                )

            # ------------------------------------------------
            # CLASSE MATERNELLE
            # ------------------------------------------------

            st.write(
                f"**Classe maternelle :** "
                f"{result['classe']}"
            )

            # ------------------------------------------------
            # DATE D'ENTRÉE POSSIBLE
            #
            # Affichée uniquement si l'enfant
            # n'est pas encore scolarisable.
            # ------------------------------------------------

            if result["entry_date"] is not None:

                st.write(
                    f"**Date d'entrée possible en accueil :** "
                    f"{result['entry_date'].strftime('%d/%m/%Y')}"
                )

            # ------------------------------------------------
            # EXPLICATION
            #
            # Affichée uniquement lorsque la date d'entrée
            # réelle est différente de la date des
            # 2 ans et demi.
            # ------------------------------------------------

            if result["explanation"] is not None:

                st.write(
                    f"**Explication :** "
                    f"{result['explanation']}"
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
