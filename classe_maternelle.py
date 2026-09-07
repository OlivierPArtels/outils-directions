from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


# ============================================================
# CALENDRIERS SCOLAIRES
# ============================================================

def _h(label, start, end=None):
    return {
        "label": label,
        "start": start,
        "end": end or start
    }


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
# JOURS DE CLASSE
# ============================================================

def _holiday_for(d, holidays):
    """
    Retourne le congé correspondant à la date d,
    ou None si la date n'est pas pendant un congé.
    """
    for holiday in holidays:
        if holiday["start"] <= d <= holiday["end"]:
            return holiday

    return None


def is_school_day(d, holidays):
    """
    Retourne True si la date est un jour de classe.

    Samedi = 5
    Dimanche = 6
    """

    if d.weekday() >= 5:
        return False

    if _holiday_for(d, holidays) is not None:
        return False

    return True


def next_school_day(d, holidays):
    """
    Cherche le premier jour de classe à partir de la date donnée.

    Si la date est déjà un jour de classe,
    elle est conservée.
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
# ANNÉE SCOLAIRE DE RÉFÉRENCE
# ============================================================

def get_current_school_year(today):
    """
    Détermine l'année scolaire à utiliser pour connaître
    la classe actuelle de l'enfant.

    Pendant les vacances d'été, l'année scolaire suivante
    est utilisée.
    """

    # Année scolaire en cours
    for school_year in SCHOOL_YEARS:

        if school_year["rentree"] <= today <= school_year["fin"]:
            return school_year

    # Vacances d'été :
    # prendre la prochaine rentrée disponible
    for school_year in SCHOOL_YEARS:

        if today < school_year["rentree"]:
            return school_year

    return None


# ============================================================
# CLASSE MATERNELLE
# ============================================================

def determine_classe(dob, school_year):
    """
    Détermine la classe de l'enfant selon son année de naissance.

    Exemple pour 2026-2027 :
    - né en 2024 -> Accueil
    - né en 2023 -> M1
    - né en 2022 -> M2
    - né en 2021 -> M3
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
# PREMIÈRE DATE POSSIBLE D'ENTRÉE
# ============================================================

def calculate_entry_date(theoretical):
    """
    Calcule la première date possible d'entrée à l'école
    à partir de la date à laquelle l'enfant atteint
    2 ans et 6 mois.

    La fonction tient compte :
    - des week-ends ;
    - des congés scolaires ;
    - des vacances d'été ;
    - des dates de rentrée.
    """

    for i, school_year in enumerate(SCHOOL_YEARS):

        # ----------------------------------------------------
        # L'enfant atteint 2 ans et demi avant la rentrée
        # ----------------------------------------------------

        if theoretical <= school_year["rentree"]:
            return school_year["rentree"]

        # ----------------------------------------------------
        # L'enfant atteint 2 ans et demi pendant
        # l'année scolaire
        # ----------------------------------------------------

        if school_year["rentree"] < theoretical <= school_year["fin"]:

            return next_school_day(
                theoretical,
                school_year["holidays"]
            )

        # ----------------------------------------------------
        # L'enfant atteint 2 ans et demi pendant
        # les vacances d'été
        # ----------------------------------------------------

        if i + 1 < len(SCHOOL_YEARS):

            next_year = SCHOOL_YEARS[i + 1]

            if school_year["fin"] < theoretical < next_year["rentree"]:
                return next_year["rentree"]

    # Date située au-delà des calendriers connus
    return None


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def determine_entree_accueil(dob):
    """
    Fonction utilisée par Streamlit.

    Retourne :
    - la date de naissance ;
    - la date des 2 ans et 6 mois uniquement si
      l'enfant n'a pas encore cet âge ;
    - la classe maternelle ;
    - la date d'entrée en accueil uniquement si
      l'enfant n'est pas encore scolarisable.
    """

    today = date.today()

    # Date à laquelle l'enfant atteint 2 ans et 6 mois
    theoretical = dob + relativedelta(
        years=2,
        months=6
    )

    # --------------------------------------------------------
    # Déterminer l'année scolaire de référence
    # --------------------------------------------------------

    current_school_year = get_current_school_year(today)

    if current_school_year is None:
        return None

    # --------------------------------------------------------
    # Déterminer la classe
    # --------------------------------------------------------

    classe = determine_classe(
        dob,
        current_school_year
    )

    # --------------------------------------------------------
    # Calculer la première date possible de scolarisation
    # --------------------------------------------------------

    first_entry_date = calculate_entry_date(theoretical)

    # --------------------------------------------------------
    # L'enfant a-t-il déjà 2 ans et demi ?
    # --------------------------------------------------------

    has_not_reached_age = today < theoretical

    # --------------------------------------------------------
    # L'enfant est-il déjà scolarisable ?
    #
    # Important :
    # un enfant peut déjà avoir 2 ans et demi mais être
    # encore pendant un week-end ou un congé scolaire.
    # --------------------------------------------------------

    not_yet_scholarisable = (
        first_entry_date is not None
        and today < first_entry_date
    )

    # --------------------------------------------------------
    # Résultat envoyé à Streamlit
    # --------------------------------------------------------

    return {
        "dob": dob,

        # Affiché seulement si l'enfant n'a pas encore
        # atteint 2 ans et 6 mois
        "theoretical": (
            theoretical
            if has_not_reached_age
            else None
        ),

        "classe": classe,

        # Affiché seulement si l'enfant ne peut pas
        # encore commencer l'école
        "entry_date": (
            first_entry_date
            if not_yet_scholarisable
            else None
        ),
    }
