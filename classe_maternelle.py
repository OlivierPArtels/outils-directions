from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def jour_semaine(d):
    return JOURS_FR[d.weekday()]


def _h(label, start, end=None):
    return {"label": label, "start": start, "end": end or start}


SCHOOL_YEARS = [
    {
        "label": "2026-2027",
        "rentree": date(2026, 8, 24),
        "fin": date(2027, 7, 2),
        "holidays": [
            _h("la fête de la Fédération Wallonie-Bruxelles", date(2026, 9, 27)),
            _h("le congé d'automne", date(2026, 10, 19), date(2026, 11, 1)),
            _h("l'Armistice", date(2026, 11, 11)),
            _h("les vacances d'hiver", date(2026, 12, 21), date(2027, 1, 3)),
            _h("le Mardi gras", date(2027, 2, 9)),
            _h("le congé de détente", date(2027, 2, 22), date(2027, 3, 7)),
            _h("le lundi de Pâques", date(2027, 3, 29)),
            _h("les vacances de printemps", date(2027, 4, 26), date(2027, 5, 9)),
            _h("le lundi de Pentecôte", date(2027, 5, 17)),
        ],
    },
    {
        "label": "2027-2028",
        "rentree": date(2027, 8, 30),
        "fin": date(2028, 7, 7),
        "holidays": [
            _h("la fête de la Fédération Wallonie-Bruxelles", date(2027, 9, 27)),
            _h("le congé d'automne", date(2027, 10, 25), date(2027, 11, 7)),
            _h("l'Armistice", date(2027, 11, 11)),
            _h("les vacances d'hiver", date(2027, 12, 27), date(2028, 1, 9)),
            _h("le congé de détente", date(2028, 2, 28), date(2028, 3, 12)),
            _h("le lundi de Pâques", date(2028, 4, 17)),
            _h("les vacances de printemps", date(2028, 5, 1), date(2028, 5, 14)),
            _h("l'Ascension", date(2028, 5, 25)),
            _h("le lundi de Pentecôte", date(2028, 6, 5)),
        ],
    },
    {
        "label": "2028-2029",
        "rentree": date(2028, 8, 28),
        "fin": date(2029, 7, 6),
        "holidays": [
            _h("la fête de la Fédération Wallonie-Bruxelles", date(2028, 9, 27)),
            _h("le congé d'automne", date(2028, 10, 23), date(2028, 11, 5)),
            _h("l'Armistice", date(2028, 11, 11)),
            _h("les vacances d'hiver", date(2028, 12, 25), date(2029, 1, 7)),
            _h("le Mardi gras", date(2029, 2, 13)),
            _h("le congé de détente", date(2029, 2, 26), date(2029, 3, 11)),
            _h("le lundi de Pâques", date(2029, 4, 2)),
            _h("les vacances de printemps", date(2029, 4, 30), date(2029, 5, 13)),
            _h("le lundi de Pentecôte", date(2029, 5, 21)),
        ],
    },
]


def _holiday_for(d, holidays):
    for h in holidays:
        if h["start"] <= d <= h["end"]:
            return h
    return None


def is_school_day(d, holidays):
    if d.weekday() >= 5:
        return False
    return _holiday_for(d, holidays) is None


def next_school_day(d, holidays):
    while not is_school_day(d, holidays):
        h = _holiday_for(d, holidays)
        if h is not None:
            d = h["end"] + timedelta(days=1)
        else:
            d += timedelta(days=1)
    return d


def build_explanation(theoretical, holidays):
    date_str = theoretical.strftime("%d/%m/%Y")
    jour = jour_semaine(theoretical)

    if is_school_day(theoretical, holidays):
        return theoretical, f"Le {date_str} est un jour de classe. L'entrée est donc possible dès cette date."

    h = _holiday_for(theoretical, holidays)
    entry = next_school_day(theoretical, holidays)
    entry_str = entry.strftime("%d/%m/%Y")
    entry_jour = jour_semaine(entry)

    if h is not None:
        periode = (h["end"] - h["start"]).days > 0
        if periode:
            return entry, (
                f"Le {date_str} tombe pendant {h['label']}. "
                f"L'entrée est donc reportée au {entry_jour} {entry_str}, jour de reprise des cours."
            )
        else:
            return entry, (
                f"Le {date_str} coïncide avec {h['label']} (jour de congé). "
                f"L'entrée est donc reportée au {entry_jour} {entry_str}, premier jour de classe suivant."
            )
    else:
        return entry, (
            f"Le {date_str} tombe un {jour}. "
            f"L'entrée est donc reportée au {entry_jour} {entry_str}, premier jour de classe suivant."
        )


def determine_entree_accueil(dob):
    theoretical = dob + relativedelta(years=2, months=6)

    first = SCHOOL_YEARS[0]
    if theoretical <= first["rentree"]:
        entry = first["rentree"]
        return {
            "dob": dob,
            "theoretical": theoretical,
            "school_year": first["label"],
            "entry_date": entry,
            "explanation": (
                f"L'enfant avait déjà 2 ans et 6 mois avant le début de l'année scolaire "
                f"{first['label']}. L'entrée est donc fixée au jour de la rentrée, "
                f"le {entry.strftime('%d/%m/%Y')}."
            ),
        }

    for i, sy in enumerate(SCHOOL_YEARS):
        if sy["rentree"] < theoretical <= sy["fin"]:
            entry, explanation = build_explanation(theoretical, sy["holidays"])
            return {
                "dob": dob,
                "theoretical": theoretical,
                "school_year": sy["label"],
                "entry_date": entry,
                "explanation": explanation,
            }
        if i + 1 < len(SCHOOL_YEARS):
            nxt = SCHOOL_YEARS[i + 1]
            if sy["fin"] < theoretical <= nxt["rentree"]:
                entry = nxt["rentree"]
                return {
                    "dob": dob,
                    "theoretical": theoretical,
                    "school_year": nxt["label"],
                    "entry_date": entry,
                    "explanation": (
                        f"L'enfant avait déjà 2 ans et 6 mois avant le début de l'année scolaire "
                        f"{nxt['label']}. L'entrée est donc fixée au jour de la rentrée, "
                        f"le {entry.strftime('%d/%m/%Y')}."
                    ),
                }

    return None
