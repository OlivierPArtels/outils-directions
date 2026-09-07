ANNEE_REFERENCE = "2026-2027"


# ============================================================
# SITUATIONS
# ============================================================

SITUATIONS = {
    "Temporaire": {
        "result_label": "Temporaire",
        "help": "MDP temporaire en prise ou reprise de fonction.",
        "cases": [
            "T1",
            "T2",
            "T3",
            "T4",
            "T5",
            "T6",
        ],
    },

    "Définitif": {
        "result_label": "Définitif",
        "help": "MDP déjà définitif.",
        "cases": [
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
        ],
    },

    "Engagement à titre définitif / nomination": {
        "result_label": "Engagement à titre définitif",
        "help": "MDP temporaire qui devient définitif.",
        "cases": [
            "N1",
        ],
    },

    "ACS/(PART-)APE": {
        "result_label": "ACS/(PART-)APE",
        "help": (
            "Dossier administratif et pécuniaire spécifique "
            "ACS/(PART-)APE."
        ),
        "cases": [
            "ACS_APE_1",
        ],
    },
}


# ============================================================
# CAS DE FIGURE
# ============================================================

CASES = {
    "T1": (
        "Prise de fonction d’un nouveau temporaire."
    ),

    "T2": (
        "Reprise de fonction dans le même PO d’un temporaire "
        "qui n’a pas eu de fonctions depuis moins de 6 mois."
    ),

    "T3": (
        "Reprise de fonction dans le même PO d’un temporaire "
        "qui n’a pas eu de fonctions depuis plus de 6 mois."
    ),

    "T4": (
        "Reprise de fonction dans un autre PO d’un temporaire "
        "qui n’a pas eu de fonctions depuis moins de 6 mois."
    ),

    "T5": (
        "Reprise de fonction dans un autre PO d’un temporaire "
        "qui n’a pas eu de fonctions depuis plus de 6 mois."
    ),

    "T6": (
        "Prise de fonction d’un temporaire provenant de "
        "l’enseignement organisé et entrant dans "
        "l’enseignement libre subventionné."
    ),

    "D1": (
        "Rentrée scolaire dans l’enseignement fondamental."
    ),

    "D2": (
        "Reprise de fonction dans le même PO après interruption "
        "de moins de 6 mois."
    ),

    "D3": (
        "Reprise de fonction dans le même PO après interruption "
        "de plus de 6 mois."
    ),

    "D4": (
        "Prise ou reprise de fonction dans un autre PO directement "
        "ou après une interruption de moins de 6 mois."
    ),

    "D5": (
        "Prise ou reprise de fonction dans un autre PO directement "
        "ou après une interruption de plus de 6 mois."
    ),

    "N1": (
        "MDP temporaire qui devient définitif."
    ),

    "ACS_APE_1": (
        "Constitution du dossier administratif et pécuniaire."
    ),
}


# ============================================================
# DOCUMENTS DES TEMPORAIRES
# ============================================================

TEMP_DOCS = {
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
        "ref": "ECJ",
    },

    "titres": {
        "label": "Copie du diplôme, annexes et équivalence",
        "ref": "Titres",
    },

    "pvc": {
        "label": "PVC",
        "ref": "PVC",
    },

    "derog_lang": {
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


# ============================================================
# MATRICE TEMPORAIRES
#
# O = Obligatoire
# N = Si nécessaire
# M = Si modification
# X = À ne pas envoyer
#
# Ces codes sont internes.
# ============================================================

TEMP_MATRIX = {
    "T1": {
        "fiche": "O",
        "doc12": "O",
        "ecj": "O",
        "titres": "O",
        "pvc": "N",
        "derog_lang": "N",
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
        "derog_lang": "N",
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
        "derog_lang": "N",
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
        "derog_lang": "N",
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
        "derog_lang": "N",
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
        "derog_lang": "N",
        "services": "N",
        "cumul": "N",
        "serment": "X",
        "foyer": "N",
        "precompte": "N",
    },
}


# ============================================================
# DOCUMENTS DES DÉFINITIFS
# ============================================================

DEF_DOCS = {
    "fiche": {
        "label": "Fiche signalétique",
        "ref": "A3",
    },

    "doc12": {
        "label": "Doc12",
        "ref": "A1",
    },

    "ecj": {
        "label": "Extrait du casier judiciaire, Mod.2 de moins de 6 mois",
        "ref": "ECJ",
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


# ============================================================
# MATRICE DÉFINITIFS
# ============================================================

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


# ============================================================
# ENGAGEMENT À TITRE DÉFINITIF
# ============================================================

N1_DOCS = [
    {
        "id": "n1_doc12",
        "label": "Doc12",
        "ref": "A1",
        "note": (
            "À la date d’effet de l’engagement à titre définitif. "
            "À envoyer dès que le PO est en possession du PV signé "
            "ou de la dépêche d’approbation."
        ),
    },

    {
        "id": "n1_ecj",
        "label": "Extrait du casier judiciaire, Mod.2 de moins de 6 mois",
        "ref": "ECJ",
        "note": None,
    },

    {
        "id": "n1_pv",
        "label": "PV d’engagement à titre définitif",
        "ref": None,
        "note": None,
    },
]


# ============================================================
# ACS/(PART-)APE
#
# Aucun numéro d'annexe n'est ajouté.
# Les 11 documents sont obligatoires.
# ============================================================

ACS_APE_DOCS = [
    {
        "id": "acs_fiche",
        "label": "Fiche signalétique",
        "note": None,
    },

    {
        "id": "acs_depeche",
        "label": "Dépêche d’autorisation d’engagement",
        "note": (
            "Préalable obligatoire à l’engagement."
        ),
    },

    {
        "id": "acs_remplacement",
        "label": "Autorisation de remplacement et dépêche initiale",
        "note": None,
    },

    {
        "id": "acs_contrat",
        "label": "Contrat de travail ou contrat de remplacement",
        "display_suffix": " — obligatoire",
        "note": (
            "À envoyer au bureau de traitement. "
            "Un exemplaire à conserver à l’école et "
            "un exemplaire à remettre au MDP."
        ),
    },

    {
        "id": "acs_droit",
        "label": (
            "État de droit FOREM pour la Région wallonne "
            "ou document A6 Actiris pour la Région de Bruxelles-Capitale"
        ),
        "note": None,
    },

    {
        "id": "acs_doc12",
        "label": "Demande d’avance (DOC12)",
        "note": (
            "Prévoir une demande par établissement "
            "où le MDP exerce."
        ),
    },

    {
        "id": "acs_casier",
        "label": "Extrait de casier judiciaire modèle 596.2",
        "note": (
            "À obtenir avant l’engagement."
        ),
    },

    {
        "id": "acs_diplomes",
        "label": "Copie du ou des diplômes ou attestation provisoire",
        "note": None,
    },

    {
        "id": "acs_precompte",
        "label": "Déclaration de précompte professionnel",
        "note": (
            "À renouveler chaque année."
        ),
    },

    {
        "id": "acs_foyer",
        "label": "Demande d’allocation de foyer/résidence",
        "note": (
            "À joindre avec une fiche signalétique."
        ),
    },

    {
        "id": "acs_services",
        "label": (
            "Services antérieurs valorisables, "
            "avec les attestations correspondantes"
        ),
        "note": (
            "Joindre les attestations correspondantes."
        ),
    },
]


# ============================================================
# DIMONA
# ============================================================

AUTO_DIMONA_CASES = {
    "T1",
    "T6",
    "N1",
}


QUESTION_ENGAGEMENT_CASES = {
    "T2",
    "T3",
    "T4",
    "T5",
    "D2",
    "D3",
    "D4",
    "D5",
    "ACS_APE_1",
}


# ============================================================
# GROUPES DE CAS
# ============================================================

TEMP_CASES = {
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "T6",
}


DEF_CASES = {
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
}


# ============================================================
# STATUTS DOCUMENTAIRES
# ============================================================

STATUS_META = {
    "O": {
        "title": "🟢 Obligatoire",
        "description": (
            "À envoyer au bureau de traitement."
        ),
    },

    "N": {
        "title": "▲ Si nécessaire",
        "description": (
            "À envoyer au bureau de traitement si la situation "
            "du MDP le nécessite."
        ),
    },

    "M": {
        "title": "🟦 Si modification",
        "description": (
            "À envoyer au bureau de traitement si les informations "
            "précédemment communiquées ont changé."
        ),
    },

    "X": {
        "title": "❌ À ne pas envoyer",
        "description": (
            "Ne pas transmettre ces documents au bureau de traitement "
            "pour cette situation."
        ),
    },
}


STATUS_ORDER = [
    "O",
    "N",
    "M",
    "X",
]
