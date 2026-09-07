from datetime import datetime
import html
import json

import streamlit as st
import streamlit.components.v1 as components

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
# CONSTANTES GÉNÉRALES
# ============================================================

ANNEE_REFERENCE = "2026-2027"

SITUATION_PLACEHOLDER = "Sélectionnez une situation"
CASE_PLACEHOLDER = "Sélectionnez un cas de figure"

SITUATION_TEMPORAIRE = "Temporaire"
SITUATION_DEFINITIF = "Définitif"
SITUATION_NOMINATION = "Engagement à titre définitif / nomination"
SITUATION_ACS_APE = "ACS/(PART-)APE"

SITUATIONS = [
    SITUATION_PLACEHOLDER,
    SITUATION_TEMPORAIRE,
    SITUATION_DEFINITIF,
    SITUATION_NOMINATION,
    SITUATION_ACS_APE,
]


# ============================================================
# DONNÉES DOC MDP
# ============================================================

TEMP_CASES = {
    "T1": "Prise de fonction d’un nouveau temporaire",
    "T2": (
        "Reprise de fonction dans le même PO d’un temporaire "
        "qui n’a pas eu de fonctions depuis moins de 6 mois"
    ),
    "T3": (
        "Reprise de fonction dans le même PO d’un temporaire "
        "qui n’a pas eu de fonctions depuis plus de 6 mois"
    ),
    "T4": (
        "Reprise de fonction dans un autre PO d’un temporaire "
        "qui n’a pas eu de fonctions depuis moins de 6 mois"
    ),
    "T5": (
        "Reprise de fonction dans un autre PO d’un temporaire "
        "qui n’a pas eu de fonctions depuis plus de 6 mois"
    ),
    "T6": (
        "Prise de fonction d’un temporaire provenant de "
        "l’enseignement organisé et entrant dans "
        "l’enseignement libre subventionné"
    ),
}

DEF_CASES = {
    "D1": "Rentrée scolaire dans l’enseignement fondamental",
    "D2": (
        "Reprise de fonction dans le même PO après interruption "
        "de moins de 6 mois"
    ),
    "D3": (
        "Reprise de fonction dans le même PO après interruption "
        "de plus de 6 mois"
    ),
    "D4": (
        "Prise ou reprise de fonction dans un autre PO directement "
        "ou après une interruption de moins de 6 mois"
    ),
    "D5": (
        "Prise ou reprise de fonction dans un autre PO directement "
        "ou après une interruption de plus de 6 mois"
    ),
}

DIRECT_CASES = {
    "N1": "MDP temporaire qui devient définitif",
    "ACS_APE_1": "Constitution du dossier administratif et pécuniaire",
}


TEMP_DOCUMENTS = {
    "fiche": {
        "label": "Fiche signalétique",
        "ref": "A3",
    },
    "doc12": {
        "label": "Doc12",
        "ref": "A1",
    },
    "ecj": {
        "label": "Extrait du casier judiciaire, Mod.2",
        "ref": "EC1",
    },
    "titres": {
        "label": "Copie du diplôme, annexes et équivalence",
        "ref": "Titres",
    },
    "pvc": {
        "label": "PVC",
        "ref": "PVC",
    },
    "derogation": {
        "label": "Dérogation linguistique",
        "ref": "A9 / A9bis / A9ter / A9quater",
    },
    "services": {
        "label": "Services antérieurs",
        "ref": "A5 ou A5bis",
    },
    "cumul": {
        "label": "Déclaration de cumul interne",
        "ref": "A2",
    },
    "serment": {
        "label": "Prestation de serment",
        "ref": "A4",
    },
    "foyer": {
        "label": "Attestation pour allocation de foyer",
        "ref": "A7",
    },
    "precompte": {
        "label": "Déclaration de précompte professionnel",
        "ref": "A8",
    },
}


TEMP_MATRIX = {
    "T1": {
        "fiche": "O",
        "doc12": "O",
        "ecj": "O",
        "titres": "O",
        "pvc": "N",
        "derogation": "N",
        "services": "N",
        "cumul": "O",
        "serment": "O",
        "foyer": "N",
        "precompte": "N",
    },
    "T2": {
        "fiche": "N",
        "doc12": "O",
        "ecj": "X",
        "titres": "X",
        "pvc": "N",
        "derogation": "N",
        "services": "N",
        "cumul": "N",
        "serment": "X",
        "foyer": "N",
        "precompte": "N",
    },
    "T3": {
        "fiche": "N",
        "doc12": "O",
        "ecj": "O",
        "titres": "X",
        "pvc": "N",
        "derogation": "N",
        "services": "N",
        "cumul": "N",
        "serment": "X",
        "foyer": "N",
        "precompte": "N",
    },
    "T4": {
        "fiche": "N",
        "doc12": "O",
        "ecj": "O",
        "titres": "X",
        "pvc": "N",
        "derogation": "N",
        "services": "N",
        "cumul": "N",
        "serment": "X",
        "foyer": "N",
        "precompte": "N",
    },
    "T5": {
        "fiche": "N",
        "doc12": "O",
        "ecj": "O",
        "titres": "X",
        "pvc": "N",
        "derogation": "N",
        "services": "N",
        "cumul": "N",
        "serment": "X",
        "foyer": "N",
        "precompte": "N",
    },
    "T6": {
        "fiche": "N",
        "doc12": "O",
        "ecj": "O",
        "titres": "N",
        "pvc": "N",
        "derogation": "N",
        "services": "N",
        "cumul": "N",
        "serment": "X",
        "foyer": "N",
        "precompte": "N",
    },
}


DEF_DOCUMENTS = {
    "fiche": {
        "label": "Fiche signalétique",
        "ref": "A3",
    },
    "doc12": {
        "label": "Doc12",
        "ref": "A1",
    },
    "ecj": {
        "label": "Extrait du casier judiciaire, Mod.2",
        "ref": "EC1",
    },
    "cumul": {
        "label": "Déclaration de cumul interne",
        "ref": "A2",
    },
    "foyer": {
        "label": "Attestation pour allocation de foyer",
        "ref": "A7",
    },
    "precompte": {
        "label": "Déclaration de précompte professionnel",
        "ref": "A8",
    },
}


DEF_MATRIX = {
    "D1": {
        "fiche": "M",
        "doc12": "O",
        "ecj": "X",
        "cumul": "N",
        "foyer": "N",
        "precompte": "N",
    },
    "D2": {
        "fiche": "M",
        "doc12": "O",
        "ecj": "X",
        "cumul": "N",
        "foyer": "N",
        "precompte": "N",
    },
    "D3": {
        "fiche": "M",
        "doc12": "O",
        "ecj": "O",
        "cumul": "N",
        "foyer": "N",
        "precompte": "N",
    },
    "D4": {
        "fiche": "M",
        "doc12": "O",
        "ecj": "X",
        "cumul": "N",
        "foyer": "N",
        "precompte": "N",
    },
    "D5": {
        "fiche": "M",
        "doc12": "O",
        "ecj": "O",
        "cumul": "N",
        "foyer": "N",
        "precompte": "N",
    },
}


NOMINATION_DOCUMENTS = [
    {
        "id": "doc12",
        "label": "Doc12",
        "ref": "A1",
        "note": (
            "À la date d’effet de l’engagement à titre définitif. "
            "À envoyer dès que le PO est en possession du PV signé "
            "ou de la dépêche d’approbation."
        ),
    },
    {
        "id": "ecj",
        "label": "Extrait du casier judiciaire, Mod.2",
        "ref": "EC1",
    },
    {
        "id": "pv_definitif",
        "label": "PV d’engagement à titre définitif",
        "ref": None,
    },
]


ACS_APE_DOCUMENTS = [
    {
        "id": "fiche",
        "label": "Fiche signalétique",
        "ref": None,
    },
    {
        "id": "depeche_engagement",
        "label": "Dépêche d’autorisation d’engagement",
        "ref": None,
        "note": "Préalable obligatoire à l’engagement.",
    },
    {
        "id": "autorisation_remplacement",
        "label": "Autorisation de remplacement et dépêche initiale",
        "ref": None,
    },
    {
        "id": "contrat",
        "label": "Contrat de travail ou contrat de remplacement",
        "ref": None,
        "note": (
            "À envoyer au bureau de traitement. "
            "Un exemplaire à conserver à l’école et "
            "un exemplaire à remettre au MDP."
        ),
    },
    {
        "id": "forem_actiris",
        "label": (
            "État de droit FOREM pour la Région wallonne "
            "ou document A6 Actiris pour la Région de Bruxelles-Capitale"
        ),
        "ref": None,
    },
    {
        "id": "doc12",
        "label": "Demande d’avance (DOC12)",
        "ref": None,
        "note": (
            "Prévoir une demande par établissement où le MDP exerce."
        ),
    },
    {
        "id": "ecj596",
        "label": "Extrait de casier judiciaire modèle 596.2",
        "ref": None,
        "note": "À obtenir avant l’engagement.",
    },
    {
        "id": "diplomes",
        "label": "Copie du ou des diplômes ou attestation provisoire",
        "ref": None,
    },
    {
        "id": "precompte",
        "label": "Déclaration de précompte professionnel",
        "ref": None,
        "note": "À renouveler chaque année.",
    },
    {
        "id": "foyer",
        "label": "Demande d’allocation de foyer/résidence",
        "ref": None,
        "note": "À joindre avec une fiche signalétique.",
    },
    {
        "id": "services",
        "label": (
            "Services antérieurs valorisables, "
            "avec les attestations correspondantes"
        ),
        "ref": None,
        "note": "Joindre les attestations correspondantes.",
    },
]


STATUS_META = {
    "O": {
        "title": "🟢 Obligatoire",
        "print_title": "● Obligatoire",
        "description": "À envoyer au bureau de traitement.",
    },
    "N": {
        "title": "▲ Si nécessaire",
        "print_title": "▲ Si nécessaire",
        "description": (
            "À envoyer au bureau de traitement si la situation "
            "du MDP le nécessite."
        ),
    },
    "M": {
        "title": "🟦 Si modification",
        "print_title": "■ Si modification",
        "description": (
            "À envoyer au bureau de traitement si les informations "
            "précédemment communiquées ont changé."
        ),
    },
    "X": {
        "title": "❌ À ne pas envoyer",
        "print_title": "✕ À ne pas envoyer",
        "description": (
            "Ne pas transmettre ces documents au bureau de traitement "
            "pour cette situation."
        ),
    },
}


# ============================================================
# FONCTIONS DOC MDP
# ============================================================

def _document_text(document):
    label = document["label"]
    reference = document.get("ref")

    if reference:
        return f"{label} ({reference})"

    return label


def _copy_document(document, document_id=None):
    copied = dict(document)

    if document_id is not None:
        copied["id"] = document_id
    elif "id" not in copied:
        copied["id"] = document.get("label", "document")

    return copied


def get_grouped_documents(case_code):
    grouped = {
        "O": [],
        "N": [],
        "M": [],
        "X": [],
    }

    if case_code in TEMP_MATRIX:
        for document_id, status in TEMP_MATRIX[case_code].items():
            document = _copy_document(
                TEMP_DOCUMENTS[document_id],
                document_id,
            )
            grouped[status].append(document)

    elif case_code in DEF_MATRIX:
        for document_id, status in DEF_MATRIX[case_code].items():
            document = _copy_document(
                DEF_DOCUMENTS[document_id],
                document_id,
            )
            grouped[status].append(document)

    elif case_code == "N1":
        grouped["O"] = [
            _copy_document(document)
            for document in NOMINATION_DOCUMENTS
        ]

    elif case_code == "ACS_APE_1":
        grouped["O"] = [
            _copy_document(document)
            for document in ACS_APE_DOCUMENTS
        ]

    return grouped


def has_dimona(case_code):
    """
    Nouvelles règles :
    - tous les temporaires : Dimona obligatoire ;
    - engagement à titre définitif / nomination : Dimona obligatoire ;
    - ACS/(PART-)APE : Dimona obligatoire ;
    - définitifs D1 à D5 : aucune mention de Dimona.
    """

    if case_code in TEMP_CASES:
        return True

    if case_code in {"N1", "ACS_APE_1"}:
        return True

    return False


def temporary_contract(case_code):
    """
    Le contrat distinct « À établir et à conserver » existe
    uniquement pour T1 à T6.

    Le contrat ACS/(PART-)APE est déjà présent dans les
    onze documents obligatoires à envoyer au bureau de traitement.
    """

    if case_code not in TEMP_CASES:
        return None

    return {
        "id": "contrat_temporaire",
        "label": "Contrat de travail — obligatoire",
        "ref": None,
        "note": (
            "Un exemplaire à conserver à l’école. "
            "Un exemplaire à remettre au MDP. "
            "Ne pas envoyer au bureau de traitement."
        ),
    }


def get_case_label(case_code):
    if case_code in TEMP_CASES:
        return TEMP_CASES[case_code]

    if case_code in DEF_CASES:
        return DEF_CASES[case_code]

    return DIRECT_CASES.get(case_code, "")


def _clear_docmdp_followup_state():
    keys_to_delete = []

    for key in st.session_state.keys():
        if (
            key.startswith("docmdp_check_")
            or key.startswith("docmdp_fiche_")
            or key.startswith("docmdp_dimona_done_")
        ):
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del st.session_state[key]


def on_docmdp_situation_change():
    _clear_docmdp_followup_state()

    if "docmdp_case" in st.session_state:
        st.session_state["docmdp_case"] = CASE_PLACEHOLDER


def on_docmdp_case_change():
    _clear_docmdp_followup_state()


def reset_docmdp():
    keys_to_delete = [
        key
        for key in st.session_state.keys()
        if key.startswith("docmdp_")
    ]

    for key in keys_to_delete:
        del st.session_state[key]


def render_document_screen(document, case_code, status):
    st.markdown(f"**{_document_text(document)}**")

    note = document.get("note")
    if note:
        st.caption(note)

    # Les pièces « À ne pas envoyer » n'ont pas de case
    # interactive de préparation à l'écran.
    if status != "X":
        st.checkbox(
            "Document préparé / vérifié",
            key=(
                f"docmdp_check_{case_code}_"
                f"{status}_{document['id']}"
            ),
        )

    st.write("")


def fiche_signal_note(case_code):
    """
    La fiche signalétique « Si modification » concerne
    uniquement les cas D1 à D5.
    """

    if case_code not in DEF_CASES:
        return None

    answer = st.selectbox(
        "Les informations de la fiche signalétique ont-elles changé "
        "depuis le dernier envoi ?",
        [
            "Je ne sais pas",
            "Oui",
            "Non",
        ],
        key=f"docmdp_fiche_answer_{case_code}",
    )

    if answer == "Oui":
        return "Fiche signalétique à transmettre au bureau de traitement."

    if answer == "Non":
        return "Aucun nouvel envoi nécessaire au titre de cette règle."

    return "Vérifier si les informations ont changé."


def build_print_document(
    situation,
    case_code,
    case_label,
    grouped,
    dimona,
    contract,
    fiche_note,
):
    parts = []

    parts.append(
        f"""
        <h1>Doc MDP</h1>
        <p class="reference">
            Libre subventionné — Année de référence {html.escape(ANNEE_REFERENCE)}
        </p>
        <div class="summary">
            <p><strong>Situation :</strong> {html.escape(situation)}</p>
            <p><strong>Cas :</strong> {html.escape(case_label)}</p>
        </div>
        """
    )

    if dimona:
        parts.append(
            """
            <div class="dimona-block">
                <span class="print-circle"></span>
                <strong>Ouvrir une Dimona</strong>
            </div>
            """
        )

    if contract is not None:
        parts.append(
            """
            <section>
                <h2>À établir et à conserver</h2>
            """
        )
        parts.append(
            f"""
            <div class="document">
                <span class="print-circle"></span>
                <div>
                    <strong>{html.escape(_document_text(contract))}</strong>
                    <div class="note">{html.escape(contract["note"])}</div>
                </div>
            </div>
            """
        )
        parts.append("</section>")

    parts.append("<section><h2>Documents pour le bureau de traitement</h2>")

    for status in ["O", "N", "M", "X"]:
        documents = grouped[status]

        if not documents:
            continue

        meta = STATUS_META[status]
        parts.append(
            f"""
            <div class="status-section">
                <h3>{html.escape(meta["print_title"])}</h3>
                <p class="status-description">
                    {html.escape(meta["description"])}
                </p>
            """
        )

        for document in documents:
            extra_note = document.get("note")

            if status == "M" and document["id"] == "fiche" and fiche_note:
                if extra_note:
                    extra_note = f"{extra_note} {fiche_note}"
                else:
                    extra_note = fiche_note

            parts.append(
                f"""
                <div class="document">
                    <span class="print-circle"></span>
                    <div>
                        <strong>{html.escape(_document_text(document))}</strong>
                """
            )

            if extra_note:
                parts.append(
                    f"""
                    <div class="note">
                        {html.escape(extra_note)}
                    </div>
                    """
                )

            parts.append(
                """
                    </div>
                </div>
                """
            )

        if status == "X":
            parts.append(
                """
                <p class="verification-note">
                    Le cercle permet de marquer le document comme vérifié,
                    sans indiquer qu’il faut l’envoyer.
                </p>
                """
            )

        parts.append("</div>")

    parts.append("</section>")

    parts.append(
        """
        <section>
            <h2>Légende</h2>
            <p><strong>● Obligatoire</strong> — à envoyer.</p>
            <p><strong>▲ Si nécessaire</strong> — à envoyer si nécessaire.</p>
            <p><strong>■ Si modification</strong> — à envoyer si les informations ont changé.</p>
            <p><strong>✕ À ne pas envoyer</strong> — ne pas transmettre.</p>
        </section>
        """
    )

    body = "".join(parts)

    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="utf-8">
        <title>Doc MDP</title>
        <style>
            @page {{
                size: A4 portrait;
                margin: 16mm;
            }}

            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, Helvetica, sans-serif;
                color: #111;
                font-size: 11pt;
                line-height: 1.35;
                margin: 0;
            }}

            h1 {{
                margin: 0 0 4mm 0;
                font-size: 22pt;
            }}

            h2 {{
                margin-top: 7mm;
                margin-bottom: 3mm;
                font-size: 15pt;
                break-after: avoid;
            }}

            h3 {{
                margin-top: 5mm;
                margin-bottom: 1.5mm;
                font-size: 12.5pt;
                break-after: avoid;
            }}

            p {{
                margin: 1.5mm 0;
            }}

            .reference {{
                color: #555;
                margin-bottom: 5mm;
            }}

            .summary {{
                padding: 3mm 4mm;
                border: 1px solid #bbb;
                border-radius: 3mm;
                margin-bottom: 5mm;
            }}

            .dimona-block {{
                display: flex;
                align-items: flex-start;
                gap: 3mm;
                margin: 5mm 0;
                padding: 3mm 4mm;
                border: 1.5px solid #c62828;
                color: #c62828;
                border-radius: 3mm;
                font-size: 12pt;
                break-inside: avoid;
            }}

            .document {{
                display: flex;
                align-items: flex-start;
                gap: 3mm;
                margin: 3mm 0;
                break-inside: avoid;
            }}

            .print-circle {{
                display: inline-block;
                width: 4.5mm;
                height: 4.5mm;
                min-width: 4.5mm;
                border: 0.45mm solid #000;
                border-radius: 50%;
                background: transparent;
                margin-top: 0.4mm;
            }}

            .note {{
                margin-top: 1mm;
                color: #444;
                font-size: 9.5pt;
            }}

            .status-description {{
                font-style: italic;
                color: #444;
                margin-bottom: 2mm;
            }}

            .verification-note {{
                font-size: 9.5pt;
                font-style: italic;
                color: #444;
            }}

            .status-section {{
                break-inside: auto;
            }}

            section {{
                break-inside: auto;
            }}
        </style>
    </head>
    <body>
        {body}
    </body>
    </html>
    """


def render_print_button(print_document):
    document_json = json.dumps(print_document)

    component_html = f"""
    <div style="font-family: Arial, Helvetica, sans-serif;">
        <button
            id="print-button"
            style="
                padding: 0.5rem 0.85rem;
                border: 1px solid rgba(128,128,128,0.65);
                border-radius: 0.5rem;
                background: transparent;
                cursor: pointer;
                font-size: 0.95rem;
            "
        >
            Imprimer / Enregistrer en PDF
        </button>
    </div>

    <script>
        const documentHtml = {document_json};

        document.getElementById("print-button").addEventListener(
            "click",
            function() {{
                const printWindow = window.open("", "_blank");

                if (!printWindow) {{
                    return;
                }}

                printWindow.document.open();
                printWindow.document.write(documentHtml);
                printWindow.document.close();

                printWindow.focus();

                setTimeout(function() {{
                    printWindow.print();
                }}, 300);
            }}
        );
    </script>
    """

    components.html(
        component_html,
        height=55,
    )


def render_doc_mdp_result(situation, case_code):
    case_label = get_case_label(case_code)
    grouped = get_grouped_documents(case_code)
    dimona = has_dimona(case_code)
    contract = temporary_contract(case_code)

    st.divider()

    st.markdown(f"**Situation :** {situation}")
    st.markdown(f"**Cas :** {case_label}")

    # --------------------------------------------------------
    # DIMONA
    # --------------------------------------------------------

    if dimona:
        st.markdown(
            """
            <div style="
                border: 1px solid #d32f2f;
                border-radius: 8px;
                padding: 12px 14px;
                margin: 14px 0;
                color: #ff5a5f;
                font-weight: 700;
            ">
                Ouvrir une Dimona
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.checkbox(
            "Dimona effectuée",
            key=f"docmdp_dimona_done_{case_code}",
        )

    # --------------------------------------------------------
    # CONTRAT DES TEMPORAIRES
    # --------------------------------------------------------

    if contract is not None:
        st.subheader("À établir et à conserver")

        render_document_screen(
            contract,
            case_code,
            "CONTRAT",
        )

    # --------------------------------------------------------
    # QUESTION FICHE SIGNALÉTIQUE POUR LES DÉFINITIFS
    # --------------------------------------------------------

    fiche_note = None

    if case_code in DEF_CASES:
        st.write("")
        fiche_note = fiche_signal_note(case_code)

    # --------------------------------------------------------
    # DOCUMENTS BUREAU DE TRAITEMENT
    # --------------------------------------------------------

    st.subheader("Documents pour le bureau de traitement")

    for status in ["O", "N", "M", "X"]:
        documents = grouped[status]

        if not documents:
            continue

        meta = STATUS_META[status]

        if status == "N":
            st.markdown(
                """
                ### <span style="color:#d6a500;">▲</span> Si nécessaire
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"### {meta['title']}")

        st.caption(meta["description"])

        for document in documents:
            screen_document = dict(document)

            if (
                status == "M"
                and document["id"] == "fiche"
                and fiche_note
            ):
                screen_document["note"] = fiche_note

            render_document_screen(
                screen_document,
                case_code,
                status,
            )

    # --------------------------------------------------------
    # LÉGENDE
    # --------------------------------------------------------

    st.subheader("Légende")

    st.markdown(
        """
        - 🟢 **Obligatoire** — à envoyer au bureau de traitement.
        - <span style="color:#d6a500;">▲</span> **Si nécessaire** — à envoyer si nécessaire.
        - 🟦 **Si modification** — à envoyer si les informations ont changé.
        - ❌ **À ne pas envoyer** — ne pas transmettre.
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # IMPRESSION
    # --------------------------------------------------------

    print_document = build_print_document(
        situation=situation,
        case_code=case_code,
        case_label=case_label,
        grouped=grouped,
        dimona=dimona,
        contract=contract,
        fiche_note=fiche_note,
    )

    render_print_button(print_document)


# ============================================================
# CHAMP DATE PERSONNALISÉ — CLASSE MATERNELLE
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

    if (!input.dataset.initialized) {
        input.value = data?.value ?? "";
        input.dataset.initialized = "true";
    }

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

    input.oninput = function() {
        input.value = formatDate(
            input.value
        );
    };

    function submitDate() {
        setTriggerValue(
            "submitted_date",
            input.value
        );
    }

    button.onclick = function() {
        submitDate();
    };

    input.onkeydown = function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            submitDate();
        }
    };

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
        1. **Doc MDP** — détermine les documents à envoyer au bureau de traitement
        2. **Classe Maternelle** — détermine la classe maternelle et la date éventuelle d'entrée
        3. **C4 Assistant** — calculateur de C4
        """
    )


# ============================================================
# DOC MDP
# ============================================================

elif outil == "Doc MDP":

    st.title("Doc MDP")

    st.caption(
        f"Libre subventionné — Année de référence {ANNEE_REFERENCE}"
    )

    st.write(
        "Sélectionnez la situation du membre du personnel. "
        "L’outil indique les documents à transmettre, "
        "les documents à établir ou conserver "
        "et les démarches complémentaires."
    )

    situation = st.selectbox(
        "Quelle est la situation du MDP ?",
        SITUATIONS,
        key="docmdp_situation",
        on_change=on_docmdp_situation_change,
    )

    selected_case = None

    # --------------------------------------------------------
    # AUCUNE SITUATION
    # --------------------------------------------------------

    if situation == SITUATION_PLACEHOLDER:

        st.info(
            "Sélectionnez une situation pour afficher le résultat."
        )

    # --------------------------------------------------------
    # TEMPORAIRE
    # --------------------------------------------------------

    elif situation == SITUATION_TEMPORAIRE:

        temp_options = [CASE_PLACEHOLDER] + list(
            TEMP_CASES.values()
        )

        selected_label = st.selectbox(
            "Quel est le cas de figure ?",
            temp_options,
            key="docmdp_case",
            on_change=on_docmdp_case_change,
        )

        st.caption(
            "Pour une interruption d’exactement 6 mois, "
            "le cas applicable doit être vérifié."
        )

        if selected_label == CASE_PLACEHOLDER:

            st.info(
                "Sélectionnez un cas de figure pour afficher le résultat."
            )

        else:

            selected_case = next(
                code
                for code, label in TEMP_CASES.items()
                if label == selected_label
            )

            render_doc_mdp_result(
                situation,
                selected_case,
            )

    # --------------------------------------------------------
    # DÉFINITIF
    # --------------------------------------------------------

    elif situation == SITUATION_DEFINITIF:

        def_options = [CASE_PLACEHOLDER] + list(
            DEF_CASES.values()
        )

        selected_label = st.selectbox(
            "Quel est le cas de figure ?",
            def_options,
            key="docmdp_case",
            on_change=on_docmdp_case_change,
        )

        st.caption(
            "Pour une interruption d’exactement 6 mois, "
            "le cas applicable doit être vérifié."
        )

        if selected_label == CASE_PLACEHOLDER:

            st.info(
                "Sélectionnez un cas de figure pour afficher le résultat."
            )

        else:

            selected_case = next(
                code
                for code, label in DEF_CASES.items()
                if label == selected_label
            )

            render_doc_mdp_result(
                situation,
                selected_case,
            )

    # --------------------------------------------------------
    # ENGAGEMENT À TITRE DÉFINITIF / NOMINATION
    # Aucun menu « Quel est le cas de figure ? »
    # --------------------------------------------------------

    elif situation == SITUATION_NOMINATION:

        selected_case = "N1"

        render_doc_mdp_result(
            situation,
            selected_case,
        )

    # --------------------------------------------------------
    # ACS/(PART-)APE
    # Aucun menu « Quel est le cas de figure ? »
    # --------------------------------------------------------

    elif situation == SITUATION_ACS_APE:

        selected_case = "ACS_APE_1"

        render_doc_mdp_result(
            situation,
            selected_case,
        )

    st.write("")

    st.button(
        "Réinitialiser",
        on_click=reset_docmdp,
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

    previous_date = st.session_state.get(
        "last_birthdate",
        ""
    )

    date_result = date_input_component(
        data={
            "value": previous_date
        },
        on_submitted_date_change=lambda: None,
        key="date_naissance_component",
        width="stretch"
    )

    dob_text = date_result.submitted_date

    if dob_text is not None:

        dob_text = dob_text.strip()

        st.session_state["last_birthdate"] = dob_text

        if not dob_text:

            st.warning(
                "Veuillez indiquer une date de naissance."
            )

        else:

            try:

                dob = datetime.strptime(
                    dob_text,
                    "%d/%m/%Y"
                ).date()

                result = determine_entree_accueil(
                    dob
                )

                if result is None:

                    st.warning(
                        "La date introduite ne peut pas être "
                        "traitée avec les calendriers scolaires "
                        "actuellement disponibles."
                    )

                else:

                    st.write("")

                    st.write(
                        f"**Date de naissance :** "
                        f"{result['dob'].strftime('%d/%m/%Y')}"
                    )

                    if result["theoretical"] is not None:

                        st.write(
                            f"**L'enfant aura 2 ans et demi le :** "
                            f"{result['theoretical'].strftime('%d/%m/%Y')}"
                        )

                    st.write(
                        f"**Classe maternelle :** "
                        f"{result['classe']}"
                    )

                    if result["entry_date"] is not None:

                        st.write(
                            f"**Date d'entrée possible en accueil :** "
                            f"{result['entry_date'].strftime('%d/%m/%Y')}"
                        )

                    if result["explanation"] is not None:

                        st.write(
                            f"**Explication :** "
                            f"{result['explanation']}"
                        )

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
