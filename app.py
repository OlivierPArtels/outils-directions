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
# CHAMP DATE PERSONNALISÉ
# ============================================================

DATE_INPUT_HTML = """
<div class="date-widget">

    <label for="date-naissance-input">
        Date de naissance de l'enfant
    </label>

    <input
        id="date-naissance-input"
        type="text"
        inputmode="numeric"
        maxlength="10"
        placeholder="JJ/MM/AAAA"
        autocomplete="off"
    />

    <button
        id="date-naissance-submit"
        type="button"
    >
        Calculer
    </button>

</div>
"""


DATE_INPUT_CSS = """
.date-widget {
    width: 100%;
    font-family: var(--st-font);
}

.date-widget label {
    display: block;
    margin-bottom: 0.4rem;
    font-size: 0.875rem;
    color: var(--st-text-color);
}

#date-naissance-input {
    width: 100%;
    box-sizing: border-box;

    padding: 0.55rem 0.75rem;

    font-family: var(--st-font);
    font-size: 1rem;

    color: var(--st-text-color);
    background-color: var(--st-secondary-background-color);

    border: 1px solid rgba(128, 128, 128, 0.5);
    border-radius: 0.5rem;

    outline: none;
}

#date-naissance-input:focus {
    border-color: var(--st-primary-color);
    box-shadow: 0 0 0 1px var(--st-primary-color);
}

#date-naissance-input::placeholder {
    opacity: 0.6;
}

#date-naissance-submit {
    margin-top: 0.75rem;

    padding: 0.4rem 0.8rem;

    font-family: var(--st-font);
    font-size: 0.875rem;

    color: var(--st-text-color);
    background-color: transparent;

    border: 1px solid rgba(128, 128, 128, 0.5);
    border-radius: 0.5rem;

    cursor: pointer;
}

#date-naissance-submit:hover {
    border-color: var(--st-primary-color);
    color: var(--st-primary-color);
}
"""


DATE_INPUT_JS = """
export default function({
    parentElement,
    data,
    setTriggerValue
}) {

    const input = parentElement.querySelector(
        "#date-naissance-input"
    );

    const button = parentElement.querySelector(
        "#date-naissance-submit"
    );

    if (!input || !button) {
        return;
    }

    // --------------------------------------------------------
    // INITIALISATION DU CHAMP
    // --------------------------------------------------------

    if (!input.dataset.initialized) {

        input.value = data?.value ?? "";

        input.dataset.initialized = "true";
    }


    // --------------------------------------------------------
    // FORMATAGE AUTOMATIQUE JJ/MM/AAAA
    // --------------------------------------------------------

    function formatDate(value) {

        const digits = value
            .replace(/\\D/g, "")
            .slice(0, 8);

        if (digits.length <= 2) {
            return digits;
        }

        if (digits.length <= 4) {
            return (
                digits.slice(0, 2)
                + "/"
                + digits.slice(2)
            );
        }

        return (
            digits.slice(0, 2)
            + "/"
            + digits.slice(2, 4)
            + "/"
            + digits.slice(4)
        );
    }


    // --------------------------------------------------------
    // FORMATAGE PENDANT LA FRAPPE
    // --------------------------------------------------------

    input.oninput = function() {

        input.value = formatDate(
            input.value
        );
    };


    // --------------------------------------------------------
    // ENVOI DE LA DATE À STREAMLIT
    // --------------------------------------------------------

    function submitDate() {

        setTriggerValue(
            "submitted_date",
            input.value
        );
    }


    button.onclick = function() {
        submitDate();
    };


    // Permet aussi d'appuyer sur Entrée
    input.onkeydown = function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            submitDate();
        }
    };


    // --------------------------------------------------------
    // NETTOYAGE
    // --------------------------------------------------------

    return () => {

        input.oninput = null;
        input.onkeydown = null;
        button.onclick = null;
    };
}
"""


date_input_component = st.components.v2.component(
    name="date_naissance_masked",
    html=DATE_INPUT_HTML,
    css=DATE_INPUT_CSS,
    js=DATE_INPUT_JS
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
        1. 1. **Doc MDP** — détermine les documents à envoyer au bureau de traitement
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
        "Outil en construction — "
        "la liste des documents sera ajoutée ici."
    )


# ============================================================
# CLASSE MATERNELLE
# ============================================================

elif outil == "Classe Maternelle":

    st.title("Classe Maternelle")

    st.write(
        "Indiquez la date de naissance de l'enfant pour "
        "déterminer sa classe maternelle et, si nécessaire, "
        "sa première date possible d'entrée."
    )

    # --------------------------------------------------------
    # DERNIÈRE DATE INTRODUITE
    # --------------------------------------------------------

    previous_date = st.session_state.get(
        "last_birthdate",
        ""
    )


    # --------------------------------------------------------
    # CHAMP DATE
    # --------------------------------------------------------

    date_result = date_input_component(
        data={
            "value": previous_date
        },
        on_submitted_date_change=lambda: None,
        key="date_naissance_component",
        width="stretch"
    )


    # --------------------------------------------------------
    # DATE ENVOYÉE AU CLIC SUR CALCULER
    # --------------------------------------------------------

    dob_text = date_result.submitted_date


    if dob_text is not None:

        dob_text = dob_text.strip()

        # Conserver la dernière date
        st.session_state["last_birthdate"] = dob_text


        # ----------------------------------------------------
        # CHAMP VIDE
        # ----------------------------------------------------

        if not dob_text:

            st.warning(
                "Veuillez indiquer une date de naissance."
            )


        # ----------------------------------------------------
        # TRAITEMENT
        # ----------------------------------------------------

        else:

            try:

                # Conversion en date Python
                dob = datetime.strptime(
                    dob_text,
                    "%d/%m/%Y"
                ).date()


                # ------------------------------------------------
                # CALCUL
                # ------------------------------------------------

                result = determine_entree_accueil(
                    dob
                )


                # ------------------------------------------------
                # CAS NON TRAITABLE
                # ------------------------------------------------

                if result is None:

                    st.warning(
                        "La date introduite ne peut pas être "
                        "traitée avec les calendriers scolaires "
                        "actuellement disponibles."
                    )


                # ------------------------------------------------
                # AFFICHAGE DU RÉSULTAT
                # ------------------------------------------------

                else:

                    st.write("")


                    # --------------------------------------------
                    # DATE DE NAISSANCE
                    # --------------------------------------------

                    st.write(
                        f"**Date de naissance :** "
                        f"{result['dob'].strftime('%d/%m/%Y')}"
                    )


                    # --------------------------------------------
                    # DATE DES 2 ANS ET DEMI
                    # --------------------------------------------

                    if result["theoretical"] is not None:

                        st.write(
                            f"**L'enfant aura 2 ans et demi le :** "
                            f"{result['theoretical'].strftime('%d/%m/%Y')}"
                        )


                    # --------------------------------------------
                    # CLASSE MATERNELLE
                    # --------------------------------------------

                    st.write(
                        f"**Classe maternelle :** "
                        f"{result['classe']}"
                    )


                    # --------------------------------------------
                    # DATE D'ENTRÉE POSSIBLE
                    # --------------------------------------------

                    if result["entry_date"] is not None:

                        st.write(
                            f"**Date d'entrée possible en accueil :** "
                            f"{result['entry_date'].strftime('%d/%m/%Y')}"
                        )


                    # --------------------------------------------
                    # EXPLICATION
                    # --------------------------------------------

                    if result["explanation"] is not None:

                        st.write(
                            f"**Explication :** "
                            f"{result['explanation']}"
                        )


            # ----------------------------------------------------
            # DATE INCORRECTE
            # ----------------------------------------------------

            except ValueError:

                st.error(
                    "Date invalide. Introduisez une date complète "
                    "au format JJ/MM/AAAA."
                )


# ============================================================
# C4 ASSISTANT
# ============================================================

elif outil == "C4 Assistant":

    st.title("📄 C4 Assistant")

    st.info(
        "Outil en construction — "
        "la logique de calcul sera ajoutée ici."
    )
