from copy import deepcopy

from doc_mdp_data import (
    ACS_APE_DOCS,
    AUTO_DIMONA_CASES,
    CASES,
    DEF_CASES,
    DEF_DOCS,
    DEF_MATRIX,
    N1_DOCS,
    QUESTION_ENGAGEMENT_CASES,
    SITUATIONS,
    STATUS_ORDER,
    TEMP_CASES,
    TEMP_DOCS,
    TEMP_MATRIX,
)


# ============================================================
# CRÉATION D'UN DOCUMENT À PARTIR DE LA MATRICE
# ============================================================

def _doc_with_status(
    doc_id,
    source,
    status,
):
    item = deepcopy(
        source[doc_id]
    )

    item["id"] = doc_id
    item["status"] = status

    item.setdefault(
        "note",
        None,
    )

    return item


# ============================================================
# REGROUPEMENT PAR STATUT
# ============================================================

def _group_matrix_docs(
    source,
    matrix,
    case_id,
):
    grouped = {
        status: []
        for status in STATUS_ORDER
    }

    for doc_id, status in matrix[case_id].items():

        grouped[status].append(
            _doc_with_status(
                doc_id=doc_id,
                source=source,
                status=status,
            )
        )

    return grouped


# ============================================================
# CAS DISPONIBLES SELON LA SITUATION
# ============================================================

def get_cases_for_situation(
    situation,
):
    if situation not in SITUATIONS:
        return []

    return SITUATIONS[
        situation
    ]["cases"]


# ============================================================
# LIBELLÉ D'UN CAS
# ============================================================

def get_case_label(
    case_id,
):
    return CASES.get(
        case_id,
        "",
    )


# ============================================================
# LIBELLÉ DE SITUATION DANS LE RÉSULTAT
# ============================================================

def get_situation_result_label(
    situation,
):
    if situation not in SITUATIONS:
        return situation

    return SITUATIONS[
        situation
    ]["result_label"]


# ============================================================
# QUESTION SUR L'ENGAGEMENT
# ============================================================

def case_requires_engagement_question(
    case_id,
):
    return (
        case_id
        in QUESTION_ENGAGEMENT_CASES
    )


# ============================================================
# CALCUL DIMONA
# ============================================================

def compute_dimona(
    case_id,
    engagement_answer=None,
):

    # --------------------------------------------------------
    # Dimona automatique
    # T1, T6 et N1
    # --------------------------------------------------------

    if case_id in AUTO_DIMONA_CASES:

        return (
            True,
            None,
        )

    # --------------------------------------------------------
    # Cas dans lesquels la direction doit indiquer
    # s'il s'agit d'un engagement.
    # --------------------------------------------------------

    if case_id in QUESTION_ENGAGEMENT_CASES:

        if engagement_answer == "Oui":

            return (
                True,
                None,
            )

        if engagement_answer == "Non":

            return (
                False,
                None,
            )

        return (
            False,
            (
                "Vérifier si cette démarche correspond "
                "à un engagement. "
                "Si oui, ouvrir une Dimona."
            ),
        )

    # --------------------------------------------------------
    # D1 : simple rentrée scolaire
    # --------------------------------------------------------

    return (
        False,
        None,
    )


# ============================================================
# CALCUL COMPLET DU DOSSIER
# ============================================================

def compute_case_result(
    situation,
    case_id,
    engagement_answer=None,
    fiche_change_answer=None,
):

    # --------------------------------------------------------
    # Vérification de la situation
    # --------------------------------------------------------

    if situation not in SITUATIONS:

        raise ValueError(
            "Situation inconnue."
        )

    # --------------------------------------------------------
    # Vérification du cas
    # --------------------------------------------------------

    if (
        case_id
        not in SITUATIONS[situation]["cases"]
    ):

        raise ValueError(
            "Cas incompatible avec "
            "la situation sélectionnée."
        )

    # --------------------------------------------------------
    # Structure vide du résultat
    # --------------------------------------------------------

    grouped = {
        status: []
        for status in STATUS_ORDER
    }

    contract = None

    # ========================================================
    # TEMPORAIRES T1 À T6
    # ========================================================

    if case_id in TEMP_CASES:

        grouped = _group_matrix_docs(
            source=TEMP_DOCS,
            matrix=TEMP_MATRIX,
            case_id=case_id,
        )

        # Le contrat est obligatoire pour T1 à T6.
        # Il est conservé à l'école / remis au MDP.
        # Il n'est pas envoyé au bureau de traitement.

        contract = {
            "id": "temp_contract",

            "label": (
                "Contrat de travail — obligatoire"
            ),

            "notes": [
                (
                    "Un exemplaire à conserver à l’école."
                ),

                (
                    "Un exemplaire à remettre au MDP."
                ),

                (
                    "Ne pas envoyer au bureau de traitement."
                ),
            ],
        }

    # ========================================================
    # DÉFINITIFS D1 À D5
    # ========================================================

    elif case_id in DEF_CASES:

        grouped = _group_matrix_docs(
            source=DEF_DOCS,
            matrix=DEF_MATRIX,
            case_id=case_id,
        )

        # ----------------------------------------------------
        # Traitement de la fiche signalétique
        # qui reste toujours en "Si modification".
        # ----------------------------------------------------

        for item in grouped["M"]:

            if item["id"] != "fiche":
                continue

            if fiche_change_answer == "Oui":

                item["note"] = (
                    "Fiche signalétique à transmettre "
                    "au bureau de traitement."
                )

            elif fiche_change_answer == "Non":

                item["note"] = (
                    "Aucun nouvel envoi nécessaire "
                    "au titre de cette règle."
                )

            else:

                item["note"] = (
                    "Vérifier si les informations ont changé."
                )

    # ========================================================
    # N1 - ENGAGEMENT À TITRE DÉFINITIF
    # ========================================================

    elif case_id == "N1":

        grouped["O"] = []

        for item in deepcopy(
            N1_DOCS
        ):

            item["status"] = "O"

            grouped["O"].append(
                item
            )

    # ========================================================
    # ACS/(PART-)APE
    # ========================================================

    elif case_id == "ACS_APE_1":

        grouped["O"] = []

        for item in deepcopy(
            ACS_APE_DOCS
        ):

            item["status"] = "O"

            grouped["O"].append(
                item
            )

    # ========================================================
    # DIMONA
    # ========================================================

    dimona, dimona_point = compute_dimona(
        case_id=case_id,
        engagement_answer=engagement_answer,
    )

    # ========================================================
    # POINTS À CONFIRMER
    # ========================================================

    points_to_confirm = []

    if dimona_point:

        points_to_confirm.append(
            dimona_point
        )

    # ========================================================
    # RÉSULTAT
    # ========================================================

    return {
        "situation": (
            get_situation_result_label(
                situation
            )
        ),

        "case_id": case_id,

        "case_label": (
            CASES[case_id]
        ),

        "engagement_answer": (
            engagement_answer
            if (
                case_id
                in QUESTION_ENGAGEMENT_CASES
            )
            else None
        ),

        "dimona": dimona,

        "contract": contract,

        "documents": grouped,

        "points_to_confirm": (
            points_to_confirm
        ),
    }
