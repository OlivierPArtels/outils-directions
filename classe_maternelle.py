from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


# ============================================================
# JOURS DE LA SEMAINE
# ============================================================

JOURS_FR = [
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche"
]


def jour_semaine(d):
    return JOURS_FR[d.weekday()]


# ============================================================
# OUTIL DE CRÉATION DES CONGÉS
# ============================================================

def _h(label, start, end=None):
    return {
        "label": label,
        "start": start,
        "end": end or start
    }


# ============================================================
# CALENDRIERS SCOLAIRES
# ============================================================

SCHOOL_YEARS = [
    {
        "label": "2026-2027",
        "rentree": date(2026, 8, 24),
        "fin": date(2027, 7, 2),
        "holidays": [
            _h(
                "la fête de la Fédération Wallonie-Bruxelles",
                date(2026, 9, 27)
            ),
            _h(
                "le congé d'automne",
                date(2026, 10, 19),
                date(2026, 11, 1)
            ),
            _h(
                "l'Armistice",
                date(2026, 11, 11)
            ),
            _h(
                "les vacances d'hiver",
                date(2026, 12, 21),
                date(2027, 1, 3)
            ),
            _h(
                "le Mardi gras",
                date(2027, 2, 9)
            ),
            _h(
                "le congé de détente",
                date(2027, 2, 22),
                date(2027, 3, 7)
            ),
            _h(
                "le lundi de Pâques",
                date(2027, 3, 29)
            ),
            _h(
                "les vacances de printemps",
                date(2027, 4, 26),
                date(2027, 5, 9)
            ),
            _h(
                "l'Ascension",
                date(2027, 5, 6)
            ),
            _h(
                "le lundi de Pentecôte",
                date(2027, 5, 17)
            ),
        ],
    },

    {
        "label": "2027-2028",
        "rentree": date(2027, 8, 30),
        "fin": date(2028, 7, 7),
        "holidays": [
            _h(
                "la fête de la Fédération Wallonie-Bruxelles",
                date(2027, 9, 27)
            ),
            _h(
                "le congé d'automne",
                date(2027, 10, 25),
                date(2027, 11, 7)
            ),
            _h(
                "l'Armistice",
                date(2027, 11, 11)
            ),
            _h(
                "les vacances d'hiver",
                date(2027, 12, 27),
                date(2028, 1, 9)
            ),
            _h(
                "le congé de détente",
                date(2028, 2, 28),
                date(2028, 3, 12)
            ),
            _h(
                "le lundi de Pâques",
                date(2028, 4, 17)
            ),
            _h(
                "les vacances de printemps",
                date(2028, 5, 1),
                date(2028, 5, 14)
            ),
            _h(
                "l'Ascension",
                date(2028, 5, 25)
            ),
            _h(
                "le lundi de Pentecôte",
                date(2028, 6, 5)
            ),
        ],
    },

    {
        "label": "2028-2029",
        "rentree": date(2028, 8, 28),
        "fin": date(2029, 7, 6),
        "holidays": [
            _h(
                "la fête de la Fédération Wallonie-Bruxelles",
                date(2028, 9, 27)
            ),
            _h(
                "le congé d'automne",
                date(2028, 10, 23),
                date(2028, 11, 5)
            ),
            _h(
                "l'Armistice",
                date(2028, 11, 11)
            ),
            _h(
                "les vacances d'hiver",
                date(2028, 12, 25),
                date(2029, 1, 7)
            ),
            _h(
                "le Mardi gras",
                date(2029, 2, 13)
            ),
            _h(
                "le congé de détente",
                date(2029, 2, 26),
                date(2029, 3, 11)
            ),
            _h(
                "le lundi de Pâques",
                date(2029, 4, 2)
            ),
            _h(
                "les vacances de printemps",
                date(2029, 4, 30),
                date(2029, 5, 13)
            ),
            _h(
                "l'Ascension",
                date(2029, 5, 10)
            ),
            _h(
                "le lundi de Pentecôte",
                date(2029, 5, 21)
            ),
        ],
    },
]


# ============================================================
# GESTION DES JOURS DE CLASSE
# ============================================================

def _holiday_for(d, holidays):
    """
    Retourne le congé dans lequel se trouve la date.
    Retourne None si la date n'est pas pendant un congé.
    """

    for holiday in holidays:
        if holiday["start"] <= d <= holiday["end"]:
            return holiday

    return None


def is_school_day(d, holidays):
    """
    Vérifie si une date est un jour de classe.
    """

    # Samedi ou dimanche
    if d.weekday() >= 5:
        return False

    # Congé scolaire
    if _holiday_for(d, holidays) is not None:
        return False

    return True


def next_school_day(d, holidays):
    """
    Retourne le premier jour de classe
    à partir de la date donnée.
    """

    current = d

    while not is_school_day(current, holidays):

        holiday = _holiday_for(current, holidays)

        if holiday is not None:
            current = holiday["end"] + timedelta(days=1)
        else:
            current += timedelta(days=1)

    return current


# ============================================================
# ANNÉE SCOLAIRE ACTUELLE
# ============================================================

def get_current_school_year(today):
    """
    Détermine l'année scolaire à utiliser pour déterminer
    la classe actuelle de l'enfant.

    Pendant les vacances d'été, la prochaine année scolaire
    est utilisée.
    """

    # Année scolaire en cours
    for school_year in SCHOOL_YEARS:

        if school_year["rentree"] <= today <= school_year["fin"]:
            return school_year

    # Entre deux années scolaires :
    # utiliser la prochaine rentrée
    for school_year in SCHOOL_YEARS:

        if today < school_year["rentree"]:
            return school_year

    return None


# ============================================================
# DÉTERMINATION DE LA CLASSE MATERNELLE
# ============================================================

def determine_classe(dob, school_year):
    """
    Détermine la classe maternelle selon l'année de naissance.

    Pour 2026-2027 :
    - né en 2024 : Accueil
    - né en 2023 : M1
    - né en 2022 : M2
    - né en 2021 : M3
    """

    annee_rentree = school_year["rentree"].year
    difference = annee_rentree - dob.year

    if difference <= 2:
        return "Accueil"

    if difference == 3:
        return "M1"

    if difference == 4:
        return "M2"

    if difference == 5:
        return "M3"

    return "Hors maternelle"


# ============================================================
# CALCUL DE LA DATE D'ENTRÉE EN ACCUEIL
# ============================================================

def calculate_entry_date(theoretical):
    """
    Calcule la première date possible d'entrée à l'école
    lorsque l'enfant atteint 2 ans et demi.

    Retourne :
    - la date réelle d'entrée ;
    - une explication uniquement lorsque cette date
      est différente de la date des 2 ans et demi.
    """

    for i, school_year in enumerate(SCHOOL_YEARS):

        # ----------------------------------------------------
        # 2 ans et demi avant la rentrée
        # ----------------------------------------------------

        if theoretical < school_year["rentree"]:

            entry_date = school_year["rentree"]

            explanation = (
                f"L'enfant atteint 2 ans et demi le "
                f"{theoretical.strftime('%d/%m/%Y')}, "
                f"avant la rentrée scolaire. "
                f"L'entrée est donc possible à partir du "
                f"{jour_semaine(entry_date)} "
                f"{entry_date.strftime('%d/%m/%Y')}."
            )

            return entry_date, explanation

        # ----------------------------------------------------
        # 2 ans et demi exactement le jour de la rentrée
        # ----------------------------------------------------

        if theoretical == school_year["rentree"]:
            return theoretical, None

        # ----------------------------------------------------
        # 2 ans et demi pendant l'année scolaire
        # ----------------------------------------------------

        if school_year["rentree"] < theoretical <= school_year["fin"]:

            # Jour normal de classe
            if is_school_day(
                theoretical,
                school_year["holidays"]
            ):
                return theoretical, None

            # Date d'entrée réelle
            entry_date = next_school_day(
                theoretical,
                school_year["holidays"]
            )

            holiday = _holiday_for(
                theoretical,
                school_year["holidays"]
            )

            # ------------------------------------------------
            # Congé scolaire
            # ------------------------------------------------

            if holiday is not None:

                explanation = (
                    f"Le {theoretical.strftime('%d/%m/%Y')} tombe pendant "
                    f"{holiday['label']}. "
                    f"L'entrée est donc reportée au "
                    f"{jour_semaine(entry_date)} "
                    f"{entry_date.strftime('%d/%m/%Y')}, "
                    f"jour de reprise des cours."
                )

                return entry_date, explanation

            # ------------------------------------------------
            # Week-end
            # ------------------------------------------------

            explanation = (
                f"Le {theoretical.strftime('%d/%m/%Y')} tombe un "
                f"{jour_semaine(theoretical)}. "
                f"L'entrée est donc reportée au "
                f"{jour_semaine(entry_date)} "
                f"{entry_date.strftime('%d/%m/%Y')}, "
                f"premier jour de classe suivant."
            )

            return entry_date, explanation

        # ----------------------------------------------------
        # 2 ans et demi pendant les vacances d'été
        # ----------------------------------------------------

        if i + 1 < len(SCHOOL_YEARS):

            next_year = SCHOOL_YEARS[i + 1]

            if (
                school_year["fin"]
                < theoretical
                < next_year["rentree"]
            ):

                entry_date = next_year["rentree"]

                explanation = (
                    f"L'enfant atteint 2 ans et demi le "
                    f"{theoretical.strftime('%d/%m/%Y')}, "
                    f"pendant les vacances d'été. "
                    f"L'entrée est donc possible à la rentrée scolaire, "
                    f"le {jour_semaine(entry_date)} "
                    f"{entry_date.strftime('%d/%m/%Y')}."
                )

                return entry_date, explanation

    return None, None


# ============================================================
# FONCTION PRINCIPALE UTILISÉE PAR STREAMLIT
# ============================================================

def determine_entree_accueil(dob):
    """
    Fonction principale appelée depuis app.py.

    Structure de la réponse :

    - date de naissance ;
    - date des 2 ans et demi uniquement si l'enfant
      n'a pas encore atteint cet âge ;
    - classe maternelle ;
    - date d'entrée possible uniquement si l'enfant
      n'est pas encore scolarisable ;
    - explication uniquement lorsque la date d'entrée
      diffère de la date des 2 ans et demi.
    """

    today = date.today()

    # --------------------------------------------------------
    # Date des 2 ans et demi
    # --------------------------------------------------------

    theoretical = dob + relativedelta(
        years=2,
        months=6
    )

    # --------------------------------------------------------
    # Année scolaire actuelle
    # --------------------------------------------------------

    current_school_year = get_current_school_year(today)

    if current_school_year is None:
        return None

    # --------------------------------------------------------
    # Classe maternelle
    # --------------------------------------------------------

    classe = determine_classe(
        dob,
        current_school_year
    )

    # --------------------------------------------------------
    # Première date possible d'entrée
    # --------------------------------------------------------

    first_entry_date, explanation = calculate_entry_date(
        theoretical
    )

    # --------------------------------------------------------
    # L'enfant a-t-il déjà 2 ans et demi ?
    # --------------------------------------------------------

    has_not_reached_age = today < theoretical

    # --------------------------------------------------------
    # L'enfant est-il actuellement scolarisable ?
    # --------------------------------------------------------

    not_yet_scholarisable = (
        first_entry_date is not None
        and today < first_entry_date
    )

    # --------------------------------------------------------
    # Explication
    #
    # Elle n'est utile que si :
    # - l'enfant n'est pas encore scolarisable
    # - ET la date réelle d'entrée est différente
    #   de la date des 2 ans et demi
    # --------------------------------------------------------

    show_explanation = (
        not_yet_scholarisable
        and first_entry_date is not None
        and first_entry_date != theoretical
    )

    # --------------------------------------------------------
    # Résultat
    # --------------------------------------------------------

    return {
        "dob": dob,

        "theoretical": (
            theoretical
            if has_not_reached_age
            else None
        ),

        "classe": classe,

        "entry_date": (
            first_entry_date
            if not_yet_scholarisable
            else None
        ),

        "explanation": (
            explanation
            if show_explanation
            else None
        ),
    }
