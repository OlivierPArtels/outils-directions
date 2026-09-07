import streamlit as st

from classe_maternelle import determine_entree_accueil
from doc_mdp import render_doc_mdp


# ============================================================
# CONFIGURATION DE LA PAGE
# ============================================================

st.set_page_config(
    page_title="Outils Directions",
    page_icon="🏫",
    layout="centered",
)


# ============================================================
# MENU LATÉRAL
# ============================================================

st.sidebar.title(
    "🏫 Outils Directions"
)

outil = st.sidebar.radio(
    "Choisir un outil",
    [
        "Accueil",
        "C4 Assistant",
        "Classe Maternelle",
        "Doc MDP",
    ],
)


# ============================================================
# ACCUEIL
# ============================================================

if outil == "Accueil":

    st.title(
        "🏫 Outils pour directions d'école"
    )

    st.write(
        "Choisissez un outil dans le menu à gauche."
    )

    st.markdown(
        """
- **C4 Assistant** — calculateur de C4
- **Classe Maternelle** — détermine la classe et la première date possible d'entrée lorsque cela est nécessaire
- **Doc MDP** — détermine les documents à préparer et à transmettre selon la situation du MDP
        """
    )


# ============================================================
# C4 ASSISTANT
# ============================================================

elif outil == "C4 Assistant":

    st.title(
        "C4 Assistant"
    )

    st.info(
        "Cet outil sera ajouté prochainement."
    )


# ============================================================
# CLASSE MATERNELLE
# ============================================================

elif outil == "Classe Maternelle":

    st.title(
        "Classe Maternelle"
    )

    st.write(
        (
            "Indiquez la date de naissance de l'enfant "
            "pour déterminer sa classe maternelle "
            "et, si nécessaire, sa première date possible d'entrée."
        )
    )

    date_naissance = st.date_input(
        "Date de naissance de l'enfant",
        value=None,
        format="DD/MM/YYYY",
    )

    if date_naissance is not None:

        resultat = determine_entree_accueil(
            date_naissance
        )

        if resultat is None:

            st.error(
                (
                    "La date ne peut pas être traitée "
                    "avec les années scolaires actuellement configurées."
                )
            )

        else:

            st.subheader(
                "Résultat"
            )

            st.write(
                (
                    "**Date de naissance :** "
                    f"{resultat['dob'].strftime('%d/%m/%Y')}"
                )
            )

            st.write(
                (
                    "**Classe :** "
                    f"{resultat['classe']}"
                )
            )

            if (
                resultat.get(
                    "theoretical"
                )
                is not None
            ):

                st.write(
                    (
                        "**Date des 2 ans et demi :** "
                        f"{resultat['theoretical'].strftime('%d/%m/%Y')}"
                    )
                )

            if (
                resultat.get(
                    "entry_date"
                )
                is not None
            ):

                st.write(
                    (
                        "**Première date possible d'entrée :** "
                        f"{resultat['entry_date'].strftime('%d/%m/%Y')}"
                    )
                )

            if resultat.get(
                "explanation"
            ):

                st.info(
                    resultat[
                        "explanation"
                    ]
                )


# ============================================================
# DOC MDP
# ============================================================

elif outil == "Doc MDP":

    render_doc_mdp()
