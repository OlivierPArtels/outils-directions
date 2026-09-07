from datetime import datetime

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
        "Doc MDP",
        "Classe Maternelle",
        "C4 Assistant"
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
        1. **Doc MDP** — détermine les documents à communiquer
        2. **Classe Maternelle** — détermine la classe maternelle et la date éventuelle d'entrée
        3. **C4 Assistant** — calculateur de C4
        """
    )


# ============================================================
# DOC MDP
# ============================================================

elif outil == "Doc MDP":

    st.title("📁 Doc MDP")

    st.info(
        "Outil en construction — la liste des documents sera ajoutée ici."
    )


# ============================================================
# CLASSE MATERNELLE
# ============================================================

elif outil == "Classe Maternelle":

    st.title("Classe Maternelle")

    st.write(
        "Indiquez la date de naissance de l'enfant pour déterminer "
        "sa classe maternelle et, si nécessaire, sa première date possible d'entrée."
    )

    # --------------------------------------------------------
    # SAISIE MANUELLE DE LA DATE DE NAISSANCE
    # --------------------------------------------------------

    dob_text = st.text_input(
        "Date de naissance de l'enfant",
        placeholder="JJ/MM/AAAA"
    )

    # --------------------------------------------------------
    # BOUTON CALCULER
    # --------------------------------------------------------

    if st.button("Calculer"):

        if not dob_text.strip():

            st.warning(
                "Veuillez indiquer une date de naissance."
            )

        else:

            try:

                dob = datetime.strptime(
                    dob_text.strip(),
                    "%d/%m/%Y"
                ).date()

                result = determine_entree_accueil(dob)

                # ------------------------------------------------
                # CAS NON TRAITABLE
                # ------------------------------------------------

                if result is None:

                    st.warning(
                        "La date introduite ne peut pas être traitée "
                        "avec les calendriers scolaires actuellement disponibles."
                    )

                # ------------------------------------------------
                # AFFICHAGE DU RÉSULTAT
                # ------------------------------------------------

                else:

                    st.write("")

                    # Date de naissance
                    st.write(
                        f"**Date de naissance :** "
                        f"{result['dob'].strftime('%d/%m/%Y')}"
                    )

                    # Date des 2 ans et demi
                    if result["theoretical"] is not None:

                        st.write(
                            f"**L'enfant aura 2 ans et demi le :** "
                            f"{result['theoretical'].strftime('%d/%m/%Y')}"
                        )

                    # Classe maternelle
                    st.write(
                        f"**Classe maternelle :** "
                        f"{result['classe']}"
                    )

                    # Date d'entrée possible
                    if result["entry_date"] is not None:

                        st.write(
                            f"**Date d'entrée possible en accueil :** "
                            f"{result['entry_date'].strftime('%d/%m/%Y')}"
                        )

                    # Explication
                    if result["explanation"] is not None:

                        st.write(
                            f"**Explication :** "
                            f"{result['explanation']}"
                        )

            except ValueError:

                st.error(
                    "Date invalide. Utilisez le format JJ/MM/AAAA, "
                    "par exemple : 27/08/2024."
                )


# ============================================================
# C4 ASSISTANT
# ============================================================

elif outil == "C4 Assistant":

    st.title("📄 C4 Assistant")

    st.info(
        "Outil en construction — la logique de calcul sera ajoutée ici."
    )
