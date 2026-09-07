import html
import json

import streamlit as st
import streamlit.components.v1 as components

from doc_mdp_data import (
    ANNEE_REFERENCE,
    CASES,
    SITUATIONS,
    STATUS_META,
    STATUS_ORDER,
)

from doc_mdp_logic import (
    case_requires_engagement_question,
    compute_case_result,
    get_cases_for_situation,
)


# ============================================================
# CONSTANTES
# ============================================================

SITUATION_PLACEHOLDER = (
    "Sélectionnez une situation"
)

CASE_PLACEHOLDER = (
    "Sélectionnez un cas de figure"
)

STATE_PREFIX = "docmdp_"


# ============================================================
# GESTION DES DONNÉES TEMPORAIRES STREAMLIT
# ============================================================

def _clear_keys(
    prefixes,
    excluded=None,
):

    excluded = set(
        excluded or []
    )

    for key in list(
        st.session_state.keys()
    ):

        if key in excluded:
            continue

        if any(
            key.startswith(prefix)
            for prefix in prefixes
        ):

            del st.session_state[key]


# ============================================================
# RÉINITIALISER LES RÉPONSES LIÉES À UN CAS
# ============================================================

def _reset_case_dependent_state():

    _clear_keys(
        [
            "docmdp_engagement",
            "docmdp_fiche_change",
            "docmdp_track_",
        ]
    )


# ============================================================
# RÉINITIALISER COMPLÈTEMENT DOC MDP
# ============================================================

def _reset_all_doc_mdp():

    for key in list(
        st.session_state.keys()
    ):

        if (
            key.startswith(
                STATE_PREFIX
            )
            and key
            != "docmdp_reset_button"
        ):

            del st.session_state[key]


# ============================================================
# NOM COMPLET D'UN DOCUMENT
# ============================================================

def _document_display_name(
    document,
):

    label = (
        document["label"]
        + document.get(
            "display_suffix",
            "",
        )
    )

    reference = document.get(
        "ref"
    )

    if reference:

        return (
            f"{label} ({reference})"
        )

    return label


# ============================================================
# AFFICHAGE D'UN DOCUMENT À L'ÉCRAN
# ============================================================

def _render_tracking_document(
    document,
    case_id,
    allow_tracking=True,
):

    display_name = (
        _document_display_name(
            document
        )
    )

    note = document.get(
        "note"
    )

    # --------------------------------------------------------
    # Document à préparer :
    # case de suivi
    # --------------------------------------------------------

    if allow_tracking:

        st.checkbox(
            display_name,
            key=(
                f"docmdp_track_"
                f"{case_id}_"
                f"{document['id']}"
            ),
        )

    # --------------------------------------------------------
    # Document à ne pas envoyer :
    # aucune case à l'écran
    # --------------------------------------------------------

    else:

        st.markdown(
            f"**{display_name}**"
        )

    # --------------------------------------------------------
    # Remarque
    # --------------------------------------------------------

    if note:

        st.caption(
            note
        )


# ============================================================
# ALERTE DIMONA
# ============================================================

def _render_dimona(
    case_id,
):

    st.markdown(
        """
        <div style="
            border: 2px solid #c62828;
            border-radius: 8px;
            padding: 12px 14px;
            margin: 12px 0;
            background: #fff5f5;
        ">
            <span style="
                color: #c62828;
                font-weight: 800;
                font-size: 1.05rem;
            ">
                Ouvrir une Dimona
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.checkbox(
        "Dimona effectuée",
        key=(
            f"docmdp_track_"
            f"{case_id}_dimona"
        ),
    )


# ============================================================
# CONTRAT TEMPORAIRE
# ============================================================

def _render_contract(
    contract,
    case_id,
):

    st.subheader(
        "À établir et à conserver"
    )

    st.checkbox(
        contract["label"],
        key=(
            f"docmdp_track_"
            f"{case_id}_"
            f"{contract['id']}"
        ),
    )

    for note in contract["notes"]:

        if (
            note
            == "Ne pas envoyer au bureau de traitement."
        ):

            st.markdown(
                f"**{note}**"
            )

        else:

            st.caption(
                note
            )


# ============================================================
# DOCUMENTS POUR LE BUREAU DE TRAITEMENT
# ============================================================

def _render_documents(
    result,
):

    st.subheader(
        "Documents pour le bureau de traitement"
    )

    for status in STATUS_ORDER:

        documents = (
            result["documents"].get(
                status,
                [],
            )
        )

        # ----------------------------------------------------
        # Ne pas afficher une rubrique vide
        # ----------------------------------------------------

        if not documents:
            continue

        meta = STATUS_META[
            status
        ]

        # ----------------------------------------------------
        # Titre de rubrique
        # ----------------------------------------------------

        if status == "N":

            st.markdown(
                """
                ### <span style="color:#c99a00;">▲</span> Si nécessaire
                """,
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                f"### {meta['title']}"
            )

        # ----------------------------------------------------
        # Explication
        # ----------------------------------------------------

        st.markdown(
            f"**{meta['description']}**"
        )

        # ----------------------------------------------------
        # Documents
        # ----------------------------------------------------

        for document in documents:

            _render_tracking_document(
                document=document,
                case_id=result["case_id"],
                allow_tracking=(
                    status != "X"
                ),
            )


# ============================================================
# POINTS À CONFIRMER
# ============================================================

def _render_points_to_confirm(
    result,
):

    if not result[
        "points_to_confirm"
    ]:

        return

    st.subheader(
        "Points à confirmer"
    )

    for point in result[
        "points_to_confirm"
    ]:

        st.warning(
            point
        )


# ============================================================
# LÉGENDE
# ============================================================

def _render_legend():

    st.subheader(
        "Légende"
    )

    st.markdown(
        """
- 🟢 **Obligatoire** — à envoyer au bureau de traitement.
- <span style="color:#c99a00;">▲</span> **Si nécessaire** — à envoyer si la situation du MDP le nécessite.
- 🟦 **Si modification** — à envoyer si les informations précédemment communiquées ont changé.
- ❌ **À ne pas envoyer** — ne pas transmettre au bureau de traitement.
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# BLOC DOCUMENT POUR L'IMPRESSION
# ============================================================

def _print_doc_block(
    document,
):

    name = html.escape(
        _document_display_name(
            document
        )
    )

    note = document.get(
        "note"
    )

    if note:

        note_html = (
            '<div class="doc-note">'
            f"{html.escape(note)}"
            "</div>"
        )

    else:

        note_html = ""

    return f"""
        <div class="doc-block">

            <span class="print-circle"></span>

            <div class="doc-content">

                <div class="doc-name">
                    {name}
                </div>

                {note_html}

            </div>

        </div>
    """


# ============================================================
# CRÉATION DE LA VERSION IMPRIMABLE
# ============================================================

def _build_printable_html(
    result,
):

    situation = html.escape(
        result["situation"]
    )

    case_label = html.escape(
        result["case_label"]
    )

    # ========================================================
    # ENGAGEMENT
    # ========================================================

    engagement_html = ""

    if case_requires_engagement_question(
        result["case_id"]
    ):

        engagement_answer = (
            result["engagement_answer"]
            if result["engagement_answer"]
            else "À confirmer"
        )

        engagement_html = (
            '<div class="summary-line">'
            '<strong>Engagement :</strong> '
            f"{html.escape(engagement_answer)}"
            "</div>"
        )

    # ========================================================
    # DIMONA
    # ========================================================

    dimona_html = ""

    if result["dimona"]:

        dimona_html = """
            <div class="dimona-box doc-block">

                <span class="print-circle"></span>

                <div class="doc-content dimona-text">
                    Ouvrir une Dimona
                </div>

            </div>
        """

    # ========================================================
    # CONTRAT DES TEMPORAIRES
    # ========================================================

    contract_html = ""

    if result["contract"]:

        contract_label = html.escape(
            result["contract"]["label"]
        )

        notes_html = ""

        for note in result[
            "contract"
        ]["notes"]:

            notes_html += (
                '<div class="doc-note">'
                f"{html.escape(note)}"
                "</div>"
            )

        contract_html = f"""
            <section>

                <h2>
                    À établir et à conserver
                </h2>

                <div class="doc-block">

                    <span class="print-circle"></span>

                    <div class="doc-content">

                        <div class="doc-name">
                            {contract_label}
                        </div>

                        {notes_html}

                    </div>

                </div>

            </section>
        """

    # ========================================================
    # DOCUMENTS DU BUREAU DE TRAITEMENT
    # ========================================================

    documents_sections = []

    for status in STATUS_ORDER:

        documents = (
            result["documents"].get(
                status,
                [],
            )
        )

        if not documents:
            continue

        meta = STATUS_META[
            status
        ]

        docs_html = ""

        for document in documents:

            docs_html += (
                _print_doc_block(
                    document
                )
            )

        # ----------------------------------------------------
        # Titre
        # ----------------------------------------------------

        if status == "N":

            title_html = (
                '<span class="yellow-triangle">'
                "▲"
                "</span> "
                "Si nécessaire"
            )

        else:

            title_html = html.escape(
                meta["title"]
            )

        # ----------------------------------------------------
        # Note spécifique À ne pas envoyer
        # ----------------------------------------------------

        x_note = ""

        if status == "X":

            x_note = """
                <div class="x-print-note">
                    Le cercle permet de marquer le document
                    comme vérifié, sans indiquer qu’il faut
                    l’envoyer.
                </div>
            """

        documents_sections.append(
            f"""
            <section>

                <h3>
                    {title_html}
                </h3>

                <div class="section-description">
                    {
                        html.escape(
                            meta["description"]
                        )
                    }
                </div>

                {docs_html}

                {x_note}

            </section>
            """
        )

    documents_html = "".join(
        documents_sections
    )

    # ========================================================
    # POINTS À CONFIRMER
    # ========================================================

    points_html = ""

    if result[
        "points_to_confirm"
    ]:

        points_items = ""

        for point in result[
            "points_to_confirm"
        ]:

            points_items += (
                "<li>"
                f"{html.escape(point)}"
                "</li>"
            )

        points_html = f"""
            <section>

                <h2>
                    Points à confirmer
                </h2>

                <ul>
                    {points_items}
                </ul>

            </section>
        """

    # ========================================================
    # HTML FINAL
    # ========================================================

    return f"""
<!doctype html>

<html lang="fr">

<head>

<meta charset="utf-8">

<title>Doc MDP</title>

<style>

    @page {{
        size: A4 portrait;
        margin: 15mm;
    }}

    * {{
        box-sizing: border-box;
    }}

    body {{
        font-family: Arial, Helvetica, sans-serif;
        color: #111;
        font-size: 10.5pt;
        line-height: 1.35;
        margin: 0;
        background: white;
    }}

    h1 {{
        font-size: 20pt;
        margin: 0 0 4mm 0;
    }}

    h2 {{
        font-size: 14pt;
        margin: 7mm 0 3mm 0;

        break-after: avoid;
        page-break-after: avoid;
    }}

    h3 {{
        font-size: 12pt;
        margin: 5mm 0 1.5mm 0;

        break-after: avoid;
        page-break-after: avoid;
    }}

    section {{
        margin: 0;
    }}

    .year {{
        font-size: 9.5pt;
        color: #444;
        margin-bottom: 5mm;
    }}

    .summary {{
        border: 1px solid #bbb;
        border-radius: 2mm;

        padding: 3mm 4mm;
        margin-bottom: 5mm;
    }}

    .summary-line {{
        margin: 1mm 0;
    }}

    .dimona-box {{
        border: 1.8px solid #c62828;
        border-radius: 2mm;

        padding: 3mm;
        margin: 4mm 0;

        color: #c62828;
        font-weight: 800;

        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}

    .dimona-text {{
        color: #c62828;
        font-weight: 800;
    }}

    .yellow-triangle {{
        color: #c99a00;

        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}

    .section-description {{
        font-weight: 700;
        margin-bottom: 2.5mm;
    }}

    .doc-block {{
        display: flex;
        align-items: flex-start;

        gap: 2.5mm;
        margin: 2.2mm 0;

        break-inside: avoid;
        page-break-inside: avoid;
    }}

    .print-circle {{
        display: inline-block;

        width: 4.5mm;
        height: 4.5mm;

        min-width: 4.5mm;
        min-height: 4.5mm;

        border: 1.4px solid #000;
        border-radius: 50%;

        background: transparent;

        margin-top: 0.2mm;
    }}

    .doc-content {{
        flex: 1;
    }}

    .doc-name {{
        font-weight: 700;
    }}

    .doc-note {{
        margin-top: 0.6mm;
        color: #333;
    }}

    .x-print-note {{
        font-size: 9pt;
        font-style: italic;

        margin-top: 2mm;
    }}

    ul {{
        padding-left: 6mm;
        margin-top: 2mm;
    }}

    .legend {{
        border-top: 1px solid #aaa;

        margin-top: 6mm;
        padding-top: 3mm;

        break-inside: avoid;
        page-break-inside: avoid;
    }}

    .legend div {{
        margin: 1mm 0;
    }}

</style>

</head>


<body>


    <h1>
        Doc MDP
    </h1>


    <div class="year">
        Année de référence : {html.escape(ANNEE_REFERENCE)}
    </div>


    <div class="summary">

        <div class="summary-line">

            <strong>
                Situation :
            </strong>

            {situation}

        </div>


        <div class="summary-line">

            <strong>
                Cas de figure :
            </strong>

            {case_label}

        </div>


        {engagement_html}

    </div>


    {dimona_html}


    {contract_html}


    <section>

        <h2>
            Documents pour le bureau de traitement
        </h2>

        {documents_html}

    </section>


    {points_html}


    <section class="legend">

        <h2>
            Légende
        </h2>


        <div>
            🟢
            <strong>
                Obligatoire
            </strong>
            — à envoyer au bureau de traitement.
        </div>


        <div>

            <span class="yellow-triangle">
                ▲
            </span>

            <strong>
                Si nécessaire
            </strong>

            — à envoyer si la situation du MDP le nécessite.

        </div>


        <div>
            🟦
            <strong>
                Si modification
            </strong>
            — à envoyer si les informations précédemment
            communiquées ont changé.
        </div>


        <div>
            ❌
            <strong>
                À ne pas envoyer
            </strong>
            — ne pas transmettre au bureau de traitement.
        </div>


    </section>


</body>

</html>
"""


# ============================================================
# BOUTON IMPRESSION / PDF
# ============================================================

def _render_print_button(
    result,
):

    printable_html = (
        _build_printable_html(
            result
        )
    )

    printable_json = json.dumps(
        printable_html,
        ensure_ascii=False,
    )

    component_html = f"""
<!doctype html>

<html lang="fr">

<head>

<meta charset="utf-8">

<style>

    body {{
        margin: 0;
        padding: 0;

        font-family: Arial, Helvetica, sans-serif;
        background: transparent;
    }}

    button {{
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 8px;

        background: white;
        color: rgb(49, 51, 63);

        padding: 0.55rem 0.9rem;

        font-size: 0.95rem;
        font-weight: 600;

        cursor: pointer;
    }}

    button:hover {{
        border-color: #ff4b4b;
        color: #ff4b4b;
    }}

    iframe {{
        position: fixed;

        width: 0;
        height: 0;

        border: 0;

        visibility: hidden;
    }}

</style>

</head>


<body>


    <button
        type="button"
        onclick="printCurrentDoc()"
    >
        Imprimer / Enregistrer en PDF
    </button>


    <iframe
        id="printFrame"
        title="Version imprimable"
    >
    </iframe>


    <script>

        const printHtml = {printable_json};


        function prepareFrame() {{

            const frame =
                document.getElementById(
                    "printFrame"
                );

            const doc =
                frame.contentWindow.document;

            doc.open();

            doc.write(
                printHtml
            );

            doc.close();

            return frame;
        }}


        function printCurrentDoc() {{

            const frame =
                prepareFrame();

            setTimeout(
                function() {{

                    frame.contentWindow.focus();

                    frame.contentWindow.print();

                }},
                150
            );
        }}

    </script>


</body>

</html>
    """

    components.html(
        component_html,
        height=58,
    )


# ============================================================
# INTERFACE PRINCIPALE
# ============================================================

def render_doc_mdp():

    # ========================================================
    # TITRE
    # ========================================================

    st.title(
        "Doc MDP"
    )

    st.caption(
        (
            "Libre subventionné — "
            f"Année de référence {ANNEE_REFERENCE}"
        )
    )

    st.write(
        (
            "Sélectionnez la situation du membre du personnel "
            "puis le cas de figure. "
            "L’outil indique les documents à transmettre, "
            "les documents à établir ou conserver et "
            "les démarches complémentaires."
        )
    )

    # ========================================================
    # AIDE
    # ========================================================

    with st.expander(
        "Comment choisir la situation ?"
    ):

        st.markdown(
            """
- **Temporaire** : MDP temporaire en prise ou reprise de fonction.
- **Définitif** : MDP déjà définitif.
- **Engagement à titre définitif / nomination** : MDP temporaire qui devient définitif.
- **ACS/(PART-)APE** : dossier administratif et pécuniaire spécifique ACS/(PART-)APE.
            """
        )

    # ========================================================
    # PREMIER MENU
    # ========================================================

    situation_options = (
        [SITUATION_PLACEHOLDER]
        + list(
            SITUATIONS.keys()
        )
    )

    situation = st.selectbox(
        "Quelle est la situation du MDP ?",
        situation_options,
        key="docmdp_situation",
    )

    # ========================================================
    # DÉTECTION DU CHANGEMENT DE SITUATION
    # ========================================================

    previous_situation = (
        st.session_state.get(
            "docmdp_previous_situation"
        )
    )

    if (
        previous_situation
        != situation
    ):

        _reset_case_dependent_state()

        if (
            "docmdp_case"
            in st.session_state
        ):

            del st.session_state[
                "docmdp_case"
            ]

        st.session_state[
            "docmdp_previous_case"
        ] = None

        st.session_state[
            "docmdp_previous_situation"
        ] = situation

    # ========================================================
    # AUCUNE SITUATION CHOISIE
    # ========================================================

    if (
        situation
        == SITUATION_PLACEHOLDER
    ):

        st.info(
            (
                "Sélectionnez une situation "
                "pour afficher les cas de figure."
            )
        )

        st.button(
            "Réinitialiser",
            key="docmdp_reset_button",
            on_click=_reset_all_doc_mdp,
        )

        return

    # ========================================================
    # SECOND MENU
    # ========================================================

    case_ids = (
        get_cases_for_situation(
            situation
        )
    )

    case_options = (
        [None]
        + case_ids
    )

    case_id = st.selectbox(
        "Quel est le cas de figure ?",
        case_options,
        format_func=lambda value: (
            CASE_PLACEHOLDER
            if value is None
            else CASES[value]
        ),
        key="docmdp_case",
    )

    # ========================================================
    # INTERRUPTION EXACTEMENT DE 6 MOIS
    # ========================================================

    if situation in {
        "Temporaire",
        "Définitif",
    }:

        st.caption(
            (
                "Pour une interruption d’exactement 6 mois, "
                "le cas applicable doit être vérifié."
            )
        )

    # ========================================================
    # DÉTECTION DU CHANGEMENT DE CAS
    # ========================================================

    previous_case = (
        st.session_state.get(
            "docmdp_previous_case"
        )
    )

    if (
        previous_case
        != case_id
    ):

        _reset_case_dependent_state()

        st.session_state[
            "docmdp_previous_case"
        ] = case_id

    # ========================================================
    # AUCUN CAS CHOISI
    # ========================================================

    if case_id is None:

        st.info(
            (
                "Sélectionnez un cas de figure "
                "pour afficher les documents."
            )
        )

        st.button(
            "Réinitialiser",
            key="docmdp_reset_button",
            on_click=_reset_all_doc_mdp,
        )

        return

    # ========================================================
    # QUESTION ENGAGEMENT
    # ========================================================

    engagement_answer = None

    if (
        case_requires_engagement_question(
            case_id
        )
    ):

        engagement_answer = st.radio(
            (
                "Cette démarche correspond-elle "
                "à un engagement du MDP ?"
            ),
            [
                "Oui",
                "Non",
                "À confirmer",
            ],
            index=None,
            key="docmdp_engagement",
            horizontal=True,
        )

    # ========================================================
    # QUESTION FICHE SIGNALÉTIQUE
    # ========================================================

    fiche_change_answer = None

    if case_id in {
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
    }:

        fiche_change_answer = st.radio(
            (
                "Les informations de la fiche signalétique "
                "ont-elles changé depuis le dernier envoi ?"
            ),
            [
                "Oui",
                "Non",
                "Je ne sais pas",
            ],
            index=None,
            key="docmdp_fiche_change",
            horizontal=True,
        )

    # ========================================================
    # CALCUL DU RÉSULTAT
    # ========================================================

    result = compute_case_result(
        situation=situation,
        case_id=case_id,
        engagement_answer=engagement_answer,
        fiche_change_answer=fiche_change_answer,
    )

    # ========================================================
    # RÉCAPITULATIF
    # ========================================================

    st.divider()

    st.subheader(
        "Situation sélectionnée"
    )

    st.markdown(
        (
            "**Situation :** "
            f"{result['situation']}"
        )
    )

    st.markdown(
        (
            "**Cas de figure :** "
            f"{result['case_label']}"
        )
    )

    # ========================================================
    # RÉPONSE ENGAGEMENT
    # ========================================================

    if (
        case_requires_engagement_question(
            case_id
        )
    ):

        engagement_display = (
            engagement_answer
            if engagement_answer
            else "À confirmer"
        )

        st.markdown(
            f"**Engagement :** {engagement_display}"
        )

    # ========================================================
    # DIMONA
    # ========================================================

    if result["dimona"]:

        _render_dimona(
            case_id
        )

    # ========================================================
    # CONTRAT TEMPORAIRE
    # ========================================================

    if result["contract"]:

        _render_contract(
            result["contract"],
            case_id,
        )

    # ========================================================
    # DOCUMENTS
    # ========================================================

    _render_documents(
        result
    )

    # ========================================================
    # POINTS À CONFIRMER
    # ========================================================

    _render_points_to_confirm(
        result
    )

    # ========================================================
    # LÉGENDE
    # ========================================================

    _render_legend()

    # ========================================================
    # IMPRESSION
    # ========================================================

    st.divider()

    _render_print_button(
        result
    )

    # ========================================================
    # RÉINITIALISATION
    # ========================================================

    st.button(
        "Réinitialiser",
        key="docmdp_reset_button",
        on_click=_reset_all_doc_mdp,
    )
