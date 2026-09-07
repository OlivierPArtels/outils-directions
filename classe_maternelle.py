from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

def _ranges(*pairs):
    """pairs = (start, end) tuples, ou une seule date pour un jour isolé"""
    result = []
    for p in pairs:
        if isinstance(p, tuple):
            result.append(p)
        else:
            result.append((p, p))
    return result

SCHOOL_YEARS = [
    {
        "label": "2026-2027",
        "rentree": date(2026, 8, 24),
        "fin": date(2027, 7, 2),
        "holidays": _ranges(
            date(2026, 9, 27),
            (date(2026, 10, 19), date(2026, 11, 1)),
            date(2026, 11, 11),
            (date(2026, 12, 21), date(2027, 1, 3)),
            date(2027, 2, 9),
            (date(2027, 2, 22), date(2027, 3, 7)),
            date(2027, 3, 29),
            (date(2027, 4, 26), date(2027, 5, 9)),
            date(2027, 5, 17),
        ),
    },
    {
        "label": "2027-2028",
        "rentree": date(2027, 8, 30),
        "fin": date(2028, 7, 7),
        "holidays": _ranges(
            date(2027, 9, 27),
            (date(2027, 10, 25), date(2027, 11, 7)),
            date(2027, 11, 11),
            (date(2027, 12, 27), date(2028, 1, 9)),
            (date(2028, 2, 28), date(2028, 3, 12)),
            date(2028, 4, 17),
            (date(2028, 5, 1), date(2028, 5, 14)),
            date(2028, 5, 25),
            date(2028, 6, 5),
        ),
    },
    {
        "label": "2028-2029",
        "rentree": date(2028, 8, 28),
        "fin": date(2029, 7, 6),
        "holidays": _ranges(
            date(2028, 9, 27),
            (date(2028, 10, 23), date(2028, 11, 5)),
            date(2028, 11, 11),
            (date(2028, 12, 25), date(2029, 1, 7)),
            date(2029, 2, 13),
            (date(2029, 2, 26), date(2029, 3, 11)),
            date(2029, 4, 2),
            (date(2029, 4, 30), date(2029, 5, 13)),
            date(2029, 5, 21),
        ),
    },
]


def is_school_day(d, holidays):
    if d.weekday() >= 5:  # samedi/dimanche
        return False
    for start, end in holidays:
        if start <= d <= end:
            return False
    return True


def next_school_day(d, holidays):
    while not is_school_day(d, holidays):
        jumped = False
        for start, end in holidays:
            if start <= d <= end:
                d = end + timedelta(days=1)
                jumped = True
                break
        if not jumped:
            d += timedelta(days=1)
    return d


def explanation_for(theoretical, holidays):
    if is_school_day(theoretical, holidays):
        return "date directe"
    if theoretical.weekday() >= 5:
        for start, end in holidays:
            if start <= theoretical <= end and (end - start).days > 0:
                return "report après vacances scolaires"
        return "report après week-end"
    for start, end in holidays:
        if start <= theoretical <= end:
            return "report après vacances scolaires" if (end - start).days > 0 else "report après jour férié"
    return "report après jour férié"


def determine_entree_accueil(dob):
    """Retourne un dict avec le résultat, ou None si l'enfant n'est pas concerné
    par les 3 années scolaires couvertes."""
    theoretical = dob + relativedelta(years=2, months=6)

    first = SCHOOL_YEARS[0]
    if theoretical <= first["rentree"]:
        return {
            "dob": dob,
            "theoretical": theoretical,
            "school_year": first["label"],
            "entry_date": first["rentree"],
            "explanation": "date directe (rentrée scolaire — l'enfant avait déjà 2 ans et 6 mois avant le début de l'année)",
        }

    for i, sy in enumerate(SCHOOL_YEARS):
        if sy["rentree"] < theoretical <= sy["fin"]:
            entry = next_school_day(theoretical, sy["holidays"]) if not is_school_day(theoretical, sy["holidays"]) else theoretical
            return {
                "dob": dob,
                "theoretical": theoretical,
                "school_year": sy["label"],
                "entry_date": entry,
                "explanation": explanation_for(theoretical, sy["holidays"]),
            }
        if i + 1 < len(SCHOOL_YEARS):
            nxt = SCHOOL_YEARS[i + 1]
            if sy["fin"] < theoretical <= nxt["rentree"]:
                return {
                    "dob": dob,
                    "theoretical": theoretical,
                    "school_year": nxt["label"],
                    "entry_date": nxt["rentree"],
                    "explanation": "date directe (rentrée scolaire — l'enfant avait déjà 2 ans et 6 mois avant le début de l'année)",
                }

    return None
