from __future__ import annotations

import calendar
import io
import json
import re
from pathlib import Path
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import streamlit as st
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth


# ============================================================
# CONSTANTES
# ============================================================

# Circulaire FWB n° 9296 : pour le C4-Enseignement,
# seul le numéro BCE de la Communauté française - Enseignement
# doit être repris. Le numéro ONSS ne doit pas être complété.
BCE_FWB_ENSEIGNEMENT = "0220916609"

# Les fichiers du module sont résolus à partir de l'emplacement réel de
# c4_assistant.py et non du dossier de travail courant de Streamlit.
# Cela évite les erreurs de chemin sur Streamlit Community Cloud.
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

# Les PDF officiels vierges doivent être placés dans le dépôt GitHub.
# Ils servent de fond : le module écrit uniquement les données de la rubrique employeur.
TEMPLATE_C4_ENSEIGNEMENT = ASSETS_DIR / "c4_enseignement_officiel.pdf"
TEMPLATE_C4_CLASSIQUE = ASSETS_DIR / "c4_classique_officiel.pdf"
FASE_DATABASE_FILE = ASSETS_DIR / "etablissements_fase.json"

# Versions actuellement publiées par l'ONEM au moment de la création du module.
EXPECTED_C4_ENSEIGNEMENT_VERSION = "06.07.2023/830.10.015"
EXPECTED_C4_CLASSIQUE_VERSION = "06.07.2023/830.10.016"


# ============================================================
# FONCTIONS ENSEIGNEMENT
# ============================================================

# Liste reprise de ProEco à partir des fonctions communiquées.
# Le code est affiché dans le menu pour faciliter le choix, mais seul
# l’intitulé complet est imprimé sur le C4.
# La liste inclut les fonctions supplémentaires communiquées pour le module C4.
FONCTIONS_ENSEIGNEMENT: list[tuple[str, str]] = [
    ("DIM", "Directeur d'école maternelle"),
    ("DIF", "Directeur d'école fondamentale"),
    ("D", "Directeur d'école"),
    ("DC", "Directeur avec classe"),
    ("DIP", "Directeur d'école primaire"),
    ("IP", "Instituteur Primaire"),
    ("IINEE", "Instituteur Primaire Immersion en Néerlandais"),
    ("II", "Instituteur Primaire Immersion"),
    ("IIANG", "Instituteur Primaire Immersion en Anglais"),
    ("IIALL", "Instituteur Primaire Immersion en Allemand"),
    ("IISIG", "Instituteur Primaire Immersion en Langue des signes"),
    ("IM", "Instituteur Maternel"),
    ("IHNEE", "Instituteur Maternel Immersion en Néerlandais"),
    ("IH", "Instituteur Maternel Immersion"),
    ("IHANG", "Instituteur Maternel Immersion en Anglais"),
    ("IHALL", "Instituteur Maternel Immersion en Allemand"),
    ("IHSIG", "Instituteur Maternel Immersion en Langue des signes"),
    ("MP", "Maître de Psychomotricité"),
    ("MM", "Maître de Morale"),
    ("ML", "Maître de Seconde Langue"),
    ("MLNEE", "Maître de Seconde Langue : Néerlandais"),
    ("MLANG", "Maître de Seconde Langue : Anglais"),
    ("MLALL", "Maître de Seconde Langue : Allemand"),
    ("ME", "Maître d'Education Physique"),
    ("MC", "Maître de Travaux Manuels"),
    ("MU", "Maître d'Education Musicale"),
    ("MR", "Maître de Religion"),
    ("MRCAT", "Maître de Religion Catholique"),
    ("MRISL", "Maître de Religion Islamique"),
    ("MRISR", "Maître de Religion Israélite"),
    ("MRORT", "Maître de Religion Orthodoxe"),
    ("MRPRO", "Maître de Religion Protestante"),
    ("MI", "Maître Education Physique Immersion"),
    ("MINEE", "Maître Education Physique Immersion en Néerlandais"),
    ("MIANG", "Maître Education Physique Immersion en Anglais"),
    ("MIALL", "Maître Education Physique Immersion en Allemand"),
    ("MISIG", "Maître Education Physique Immersion en Langue des signes"),
    ("KI", "Kinésithérapeute"),
    ("LO", "Logopède"),
    ("PE", "Puériculteur"),
    ("NF", "Infirmier"),
    ("AS", "Assistant Social"),
    ("PS", "Psychologue"),
    ("SE", "Surveillant-Educateur"),
    ("EAEP", "Educateur - activité d'encadrement pédagogique"),
    ("DA", "Directeur adjoint"),
    ("IPMA", "Instituteur primaire maturité I et maturité II type 2"),
    ("MPC", "Maître de Philosophie et de Citoyenneté"),
    ("MLSIG", "Maître de langue des signes"),
    ("ER", "Ergothérapeute"),
    ("AP", "Aide aux instits primaires"),
    ("PU", "Puériculteur"),
    ("AM", "Aide aux instits maternelles"),
    ("COPT", "Coordonnateur pole territorial"),
    ("Z0003", "Fondamental"),
    ("PR-REL-F", "Professeur de REL au F"),
    ("ED", "Educateur"),
    ("PR-CG-F", "Professeur de CG au F"),
    ("PR-CS-F", "Professeur de CS au F"),
]

FONCTIONS_PAR_CODE = dict(FONCTIONS_ENSEIGNEMENT)


# ============================================================
# FONCTIONS PRIORITAIRES ACS / APE / PART-APE / PTP
# ============================================================

# Ces fonctions sont volontairement placées en tête du menu ACS/APE.
# Les autres fonctions ProEco restent disponibles ensuite.
FONCTIONS_ACS_APE_PRIORITAIRES: list[str] = [
    "Assistant(e) à l’instituteur(trice) maternel(le)",
    "Assistant(e) à l’instituteur(trice) primaire",
    "Assistant(e) à la gestion administrative",
    "Assistant(e) au personnel auxiliaire d'éducation",
    "Ouvrier(ère)",
    "Puériculteur(trice) PTP",
]

FONCTIONS_ACS_APE_OPTIONS: list[str] = (
    FONCTIONS_ACS_APE_PRIORITAIRES
    + [f"{code} — {label}" for code, label in FONCTIONS_ENSEIGNEMENT]
)

# Régimes horaires autorisés pour les situations ACS / APE / PART-APE / PTP.
# Le libellé est affiché à l'utilisateur ; Q et S restent calculés en interne
# car le formulaire C4 classique les attend.
REGIMES_HORAIRES_ACS_APE: dict[str, tuple[float, float]] = {
    "Mi-temps — 18/36": (18.0, 36.0),
    "4/5e temps — 32/36": (32.0, 36.0),
    "Temps plein — 36/36": (36.0, 36.0),
}


def _acs_ape_function_label(option: str) -> str:
    """Retourne l'intitulé de fonction sans le code ProEco éventuel."""
    if " — " in option:
        return option.split(" — ", 1)[1].strip()
    return option.strip()


def _format_fonction_option(code: str) -> str:
    if not code:
        return "— Sélectionner une fonction —"
    return f"{code} — {FONCTIONS_PAR_CODE[code]}"


# ============================================================
# CHAMP DATE AVEC / AUTOMATIQUES
# ============================================================

def _format_masked_date(value: str) -> str:
    """Transforme 25082025 en 25/08/2025 sans composant Streamlit v2."""
    digits = re.sub(r"\D", "", value or "")[:8]

    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}/{digits[2:]}"
    return f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"


def _sync_masked_date(widget_key: str, state_key: str) -> None:
    """Normalise la date quand l'utilisateur valide le champ ou le quitte."""
    formatted = _format_masked_date(st.session_state.get(widget_key, ""))
    st.session_state[widget_key] = formatted
    st.session_state[state_key] = formatted


def _masked_date_input(label: str, key: str, value: str = "") -> str:
    """Champ JJ/MM/AAAA robuste, sans st.components.v2.

    Les barres obliques sont ajoutées automatiquement dès que le champ est
    validé (Entrée) ou quitté. Cette solution évite l'erreur
    BidiComponentInvalidIdError rencontrée sur Streamlit Cloud.
    """
    state_key = f"{key}__masked_value"
    widget_key = f"{key}__input"

    if state_key not in st.session_state:
        st.session_state[state_key] = _format_masked_date(value or "")

    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state[state_key]

    st.text_input(
        label,
        key=widget_key,
        placeholder="JJ/MM/AAAA",
        max_chars=10,
        on_change=_sync_masked_date,
        args=(widget_key, state_key),
    )

    # Si la valeur a été modifiée autrement dans l'état de session, on garde
    # toujours une version normalisée pour les calculs.
    current = _format_masked_date(st.session_state.get(widget_key, ""))
    st.session_state[state_key] = current
    return current


# ============================================================
# MODELE DE DONNEES - FICHE DE PAIE
# ============================================================

@dataclass
class PayrollEntry:
    file_name: str
    page_number: int
    raw_text: str

    employee_name: str = ""
    employee_address: str = ""
    employee_matricule: str = ""

    establishment_name: str = ""
    establishment_address: str = ""

    q: Optional[float] = None
    s: Optional[float] = None

    liquidation_month: str = ""
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    status: str = ""
    salary_scale: str = ""
    seniority: str = ""
    annual_base_salary: Optional[float] = None
    pdf_index: Optional[float] = None

    gross: Optional[float] = None
    fr_amount: float = 0.0
    fr_found: bool = False

    absence_or_leave: str = ""
    deferred_pay_detected: bool = False


# ============================================================
# REPERTOIRE FASE DES ETABLISSEMENTS
# ============================================================

def _normalize_fase(value: str | int | float | None) -> str:
    """Normalise un numéro FASE pour permettre une recherche fiable."""
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    # Accepte notamment 765, 765.0 ou du texte copié avec espaces.
    match = re.search(r"\d+(?:[.,]0+)?", text)
    if not match:
        return ""

    number = match.group(0).replace(",", ".")
    try:
        return str(int(float(number)))
    except ValueError:
        return ""


def _load_fase_database() -> tuple[dict[str, dict], str]:
    """Charge le répertoire FASE dérivé du fichier signalétique FWB."""
    path = FASE_DATABASE_FILE

    if not path.exists():
        return {}, (
            "Le répertoire FASE est absent : "
            "assets/etablissements_fase.json. "
            "Ajoutez le fichier dans le dépôt GitHub."
        )

    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        return {}, f"Impossible de lire le répertoire FASE : {exc}"

    establishments = payload.get("etablissements", {})
    if not isinstance(establishments, dict) or not establishments:
        return {}, "Le répertoire FASE est vide ou invalide."

    return establishments, ""


def _fase_establishment_address(record: dict) -> str:
    parts = [
        str(record.get("adresse", "")).strip(),
        str(record.get("code_postal", "")).strip(),
        str(record.get("localite", "")).strip(),
    ]
    return " ".join(part for part in parts if part)


# ============================================================
# OUTILS DE PARSING
# ============================================================

def _clean_spaces(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def _parse_number(value: str | None) -> Optional[float]:
    if not value:
        return None

    cleaned = value.upper().replace("EUR", "")
    cleaned = cleaned.replace("\u00a0", " ").strip()
    cleaned = re.sub(r"[^0-9,\.\-]", "", cleaned)

    if not cleaned:
        return None

    # Format belge : 22.358,41 -> 22358.41
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(value: str | None) -> Optional[date]:
    if not value:
        return None

    value = value.strip()

    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def _format_date(value: Optional[date]) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _format_money(value: Optional[float]) -> str:
    if value is None:
        return "—"

    return (
        f"{value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
        + " €"
    )


def _find_first(patterns: list[str], text: str, flags=re.IGNORECASE | re.MULTILINE):
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match
    return None


def _extract_employee_identity(lines: list[str]) -> tuple[str, str, str]:
    if not lines:
        return "", "", ""

    matricule_index = None
    matricule = ""

    for i, line in enumerate(lines):
        match = re.match(r"Matricule\s*:?\s*([0-9]+)", line, re.IGNORECASE)
        if match:
            matricule_index = i
            matricule = match.group(1)
            break

    if matricule_index is None:
        return lines[0], "", ""

    name = lines[0]
    address = "\n".join(lines[1:matricule_index]).strip()
    return name, address, matricule


def _extract_establishment(lines: list[str]) -> tuple[str, str]:
    start = None
    first_value = ""

    for i, line in enumerate(lines):
        match = re.match(r"Etablissement\s*:\s*(.*)", line, re.IGNORECASE)
        if match:
            start = i
            first_value = match.group(1).strip()
            break

    if start is None:
        return "", ""

    name = first_value
    address_lines: list[str] = []

    for line in lines[start + 1:]:
        if re.match(r"Paiement\s+par\s*:", line, re.IGNORECASE):
            break

        # Sur les fiches FWB, une ligne numérique peut correspondre
        # à un identifiant d'établissement. Elle n'est pas une adresse.
        if re.fullmatch(r"[0-9]{8,14}", line.strip()):
            break

        address_lines.append(line)

    return name, "\n".join(address_lines).strip()


def parse_payroll_page(text: str, file_name: str, page_number: int) -> PayrollEntry:
    cleaned_text = text.replace("\u00a0", " ")
    lines = [_clean_spaces(line) for line in cleaned_text.splitlines() if _clean_spaces(line)]

    entry = PayrollEntry(
        file_name=file_name,
        page_number=page_number,
        raw_text=cleaned_text,
    )

    (
        entry.employee_name,
        entry.employee_address,
        entry.employee_matricule,
    ) = _extract_employee_identity(lines)

    (
        entry.establishment_name,
        entry.establishment_address,
    ) = _extract_establishment(lines)

    charge_match = _find_first(
        [
            r"Charge\s+Pay[ée]e?\s*:\s*([0-9]+(?:[,.][0-9]+)?)\s*/\s*([0-9]+(?:[,.][0-9]+)?)",
            r"Fraction\s*:\s*([0-9]+(?:[,.][0-9]+)?)\s*/\s*([0-9]+(?:[,.][0-9]+)?)",
        ],
        cleaned_text,
    )
    if charge_match:
        entry.q = _parse_number(charge_match.group(1))
        entry.s = _parse_number(charge_match.group(2))

    liquidation_match = _find_first(
        [r"Mois\s+de\s+liquidation\s*:\s*([^\n\r]+)"],
        cleaned_text,
    )
    if liquidation_match:
        entry.liquidation_month = _clean_spaces(liquidation_match.group(1))

    period_match = _find_first(
        [
            r"P[ée]riode\s+concern[ée]e?\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{2,4})\s+au\s+([0-9]{2}/[0-9]{2}/[0-9]{2,4})"
        ],
        cleaned_text,
    )
    if period_match:
        entry.period_start = _parse_date(period_match.group(1))
        entry.period_end = _parse_date(period_match.group(2))

    status_match = _find_first(
        [r"Statut\s*:\s*([^\n\r]+)"],
        cleaned_text,
    )
    if status_match:
        entry.status = _clean_spaces(status_match.group(1))

    scale_match = _find_first(
        [r"Echelle\s+bar[ée]mique\s*:\s*([^\n\r]+)"],
        cleaned_text,
    )
    if scale_match:
        entry.salary_scale = _clean_spaces(scale_match.group(1))

    seniority_match = _find_first(
        [r"Anciennet[ée]\s+p[ée]cuniaire\s*:\s*([^\n\r]+)"],
        cleaned_text,
    )
    if seniority_match:
        entry.seniority = _clean_spaces(seniority_match.group(1))

    tab_match = _find_first(
        [
            r"Bar[èe]me\s+annuel\s+[àa]\s+100\s*%\s*:\s*([0-9.\s]+,[0-9]{2})\s*EUR",
            r"Traitement\s+annuel\s+brut[^:\n]*:\s*([0-9.\s]+,[0-9]{2})\s*EUR",
        ],
        cleaned_text,
    )
    if tab_match:
        entry.annual_base_salary = _parse_number(tab_match.group(1))

    index_match = _find_first(
        [r"Index\s*:\s*([0-9]+[,.][0-9]{4,6})"],
        cleaned_text,
    )
    if index_match:
        entry.pdf_index = _parse_number(index_match.group(1))

    gross_match = _find_first(
        [
            r"(?:^|\n)\s*Brut\s+([0-9.\s]+,[0-9]{2})\s*EUR",
            r"Traitement\s+mensuel[\s\S]{0,100}?Brut\s+([0-9.\s]+,[0-9]{2})\s*EUR",
        ],
        cleaned_text,
    )
    if gross_match:
        entry.gross = _parse_number(gross_match.group(1))

    # L'allocation F/R peut être présentée sous plusieurs libellés.
    fr_patterns = [
        r"Allocation\s+(?:de\s+)?foyer\s*/\s*r[ée]sidence\s*:?[ \t]*([0-9.\s]+,[0-9]{2})\s*EUR",
        r"Allocation\s+(?:de\s+)?foyer\s*:?[ \t]*([0-9.\s]+,[0-9]{2})\s*EUR",
        r"Allocation\s+(?:de\s+)?r[ée]sidence\s*:?[ \t]*([0-9.\s]+,[0-9]{2})\s*EUR",
        r"(?:^|\n)\s*F/R\s*:?[ \t]*([0-9.\s]+,[0-9]{2})\s*EUR",
    ]

    fr_match = _find_first(fr_patterns, cleaned_text)
    if fr_match:
        parsed_fr = _parse_number(fr_match.group(1))
        entry.fr_amount = parsed_fr or 0.0
        entry.fr_found = True

    leave_match = _find_first(
        [r"Dispo\.\s*rempl\.\s*cong[ée]\s*:\s*([\s\S]+?)(?=Traitement\s+mensuel|$)"],
        cleaned_text,
    )
    if leave_match:
        entry.absence_or_leave = _clean_spaces(leave_match.group(1))

    entry.deferred_pay_detected = bool(
        re.search(r"(?:traitement|r[ée]mun[ée]ration)\s+diff[ée]r[ée]", cleaned_text, re.IGNORECASE)
    )

    return entry


def extract_payroll_entries(uploaded_files) -> tuple[list[PayrollEntry], list[str]]:
    entries: list[PayrollEntry] = []
    errors: list[str] = []

    for uploaded_file in uploaded_files:
        try:
            reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
        except Exception as exc:
            errors.append(f"{uploaded_file.name} : PDF illisible ({exc}).")
            continue

        for page_index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                errors.append(
                    f"{uploaded_file.name}, page {page_index} : extraction impossible ({exc})."
                )
                continue

            if not text.strip():
                errors.append(
                    f"{uploaded_file.name}, page {page_index} : aucun texte exploitable. "
                    "Le PDF est peut-être scanné sous forme d'image."
                )
                continue

            entries.append(
                parse_payroll_page(
                    text=text,
                    file_name=uploaded_file.name,
                    page_number=page_index,
                )
            )

    return entries, errors


# ============================================================
# CALCULS C4
# ============================================================

def calculate_monthly_indexed_salary(
    annual_base_salary: float,
    q: float,
    s: float,
    index_value: float,
    monthly_fr: float = 0.0,
) -> Optional[float]:
    if annual_base_salary < 0 or q < 0 or s <= 0 or index_value <= 0:
        return None

    result = (annual_base_salary * (q / s) * index_value) / 12
    result += monthly_fr
    return round(result, 2)


def reconstruct_monthly_fr(entry: Optional[PayrollEntry]) -> float:
    if not entry or not entry.fr_found:
        return 0.0

    if not entry.period_start or not entry.period_end:
        return round(entry.fr_amount, 2)

    if (
        entry.period_start.year != entry.period_end.year
        or entry.period_start.month != entry.period_end.month
    ):
        return round(entry.fr_amount, 2)

    total_days = calendar.monthrange(
        entry.period_start.year,
        entry.period_start.month,
    )[1]

    covered_days = (entry.period_end - entry.period_start).days + 1

    if covered_days <= 0:
        return round(entry.fr_amount, 2)

    if covered_days >= total_days:
        return round(entry.fr_amount, 2)

    return round((entry.fr_amount / covered_days) * total_days, 2)


def quarter_info(d: date) -> tuple[int, date, date, str]:
    quarter = ((d.month - 1) // 3) + 1
    start_month = 1 + (quarter - 1) * 3
    end_month = start_month + 2

    start = date(d.year, start_month, 1)
    end_day = calendar.monthrange(d.year, end_month)[1]
    end = date(d.year, end_month, end_day)

    label = f"{quarter:02d}/{d.year}"
    return quarter, start, end, label


def interruption_window(end_date: date) -> tuple[date, date]:
    # Si la fin tombe dans le premier mois d'un trimestre :
    # mois en cours + les trois mois précédents.
    if end_date.month in (1, 4, 7, 10):
        year = end_date.year
        month = end_date.month - 3
        while month <= 0:
            month += 12
            year -= 1
        return date(year, month, 1), end_date

    # Sinon : trimestre en cours.
    _, start, _, _ = quarter_info(end_date)
    return start, end_date


def _same_status(a: str, b: str) -> bool:
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()

    if not a or not b:
        return False

    if "temp" in a and "temp" in b:
        return True

    if ("déf" in a or "def" in a or "stat" in a) and (
        "déf" in b or "def" in b or "stat" in b
    ):
        return True

    return a == b


def _entry_in_quarter(entry: PayrollEntry, start: date, end: date) -> bool:
    if not entry.period_start or not entry.period_end:
        return False

    return not (entry.period_end < start or entry.period_start > end)


def _entry_label(entry: PayrollEntry) -> str:
    fraction = "?/?"
    if entry.q is not None and entry.s is not None:
        fraction = f"{entry.q:g}/{entry.s:g}"

    period = "période inconnue"
    if entry.period_start and entry.period_end:
        period = f"{_format_date(entry.period_start)} → {_format_date(entry.period_end)}"

    gross = _format_money(entry.gross)

    return (
        f"{entry.file_name} — p. {entry.page_number} — {period} — "
        f"{entry.status or 'statut ?'} — {fraction} — brut {gross}"
    )


def _parse_user_date(value: str) -> tuple[Optional[date], Optional[str]]:
    value = (value or "").strip()
    if not value:
        return None, "Date manquante."

    parsed = _parse_date(value)
    if not parsed:
        return None, "Date invalide. Utilisez JJ/MM/AAAA."

    return parsed, None


def _clear_occ_fields(prefix: str):
    suffixes = [
        "fonction",
        "statut",
        "q",
        "s",
        "tab",
        "fr_month",
        "start",
        "end",
        "period_additional",
        "mode_override",
        "onss_case",
        "dmfa_state",
        "exact_entries",
        "exact_manual",
        "july_estimate",
        "june_source",
    ]

    for suffix in suffixes:
        st.session_state.pop(f"{prefix}_{suffix}", None)


def _status_default_index(status: str) -> int:
    status = (status or "").lower()
    if "temp" in status:
        return 0
    if "déf" in status or "def" in status or "stat" in status:
        return 1
    if "premier emploi" in status:
        return 2
    return 3


def _status_value(index: int) -> str:
    return [
        "Temporaire",
        "Définitif / statutaire",
        "Convention premier emploi",
        "Autre",
    ][index]


def _default_unemployment_reason(end_reason: str) -> str:
    """Libellé proposé automatiquement pour la zone « Motif du chômage ».

    Le texte reste modifiable par la direction dans l'interface.
    """
    mapping = {
        "Fin de plein droit et sans préavis": "Fin de l'occupation de plein droit",
        "Le pouvoir organisateur a mis fin à l'occupation avec préavis": (
            "Fin de l'occupation à l'initiative du pouvoir organisateur avec préavis"
        ),
        "Le pouvoir organisateur a mis fin à l'occupation sans préavis": (
            "Fin de l'occupation à l'initiative du pouvoir organisateur sans préavis"
        ),
        "Le membre du personnel a quitté volontairement son emploi": (
            "Départ volontaire du membre du personnel"
        ),
    }
    return mapping.get(end_reason, "")


# ============================================================
# GENERATION PDF - FORMULAIRES OFFICIELS
# ============================================================

def _template_bytes(path: str | Path) -> tuple[Optional[bytes], Optional[str]]:
    try:
        with open(path, "rb") as f:
            return f.read(), None
    except FileNotFoundError:
        try:
            display_path = str(Path(path).relative_to(BASE_DIR))
        except Exception:
            display_path = str(path)
        return None, (
            f"Le modèle officiel est absent : {display_path}. "
            "Téléchargez le PDF officiel ONEM et placez-le à cet emplacement dans GitHub."
        )
    except Exception as exc:
        return None, f"Impossible de lire le modèle {path} : {exc}"


def _template_contains_version(pdf_bytes: bytes, expected_version: str) -> bool:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        first_pages = reader.pages[: min(2, len(reader.pages))]
        text = "\n".join((p.extract_text() or "") for p in first_pages)
        return expected_version in text
    except Exception:
        return False


def _pdf_overlay(width: float, height: float, draw_callback) -> bytes:
    stream = io.BytesIO()
    c = canvas.Canvas(stream, pagesize=(width, height))
    c.setFillColorRGB(0, 0, 0)
    draw_callback(c)
    c.save()
    stream.seek(0)
    return stream.read()


def _merge_overlays(template_pdf: bytes, page_drawers: dict[int, object]) -> bytes:
    reader = PdfReader(io.BytesIO(template_pdf))
    writer = PdfWriter()

    for page_index, page in enumerate(reader.pages):
        drawer = page_drawers.get(page_index)
        if drawer is not None:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay_bytes = _pdf_overlay(width, height, drawer)
            overlay_reader = PdfReader(io.BytesIO(overlay_bytes))
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _draw_text(c, x: float, y: float, text: object, size: float = 8.2, max_chars: Optional[int] = None):
    if text is None:
        return
    value = str(text).strip()
    if not value:
        return
    if max_chars and len(value) > max_chars:
        value = value[: max_chars - 1] + "…"
    c.setFont("Helvetica", size)
    c.drawString(x, y, value)


def _draw_multiline(c, x: float, y: float, text: object, size: float = 8.0, leading: float = 9.0, max_chars: int = 95):
    if text is None:
        return
    value = str(text).strip()
    if not value:
        return

    words = value.replace("\n", " \n ").split()
    lines: list[str] = []
    current = ""
    for word in words:
        if word == "\n":
            if current:
                lines.append(current)
                current = ""
            continue
        proposal = word if not current else f"{current} {word}"
        if len(proposal) <= max_chars:
            current = proposal
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    c.setFont("Helvetica", size)
    for idx, line in enumerate(lines[:3]):
        c.drawString(x, y - idx * leading, line)


def _draw_check(c, x: float, y: float, checked: bool):
    if not checked:
        return
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "X")


def _draw_date(c, x: float, y: float, value: Optional[date], size: float = 8.2):
    if value:
        _draw_text(c, x, y, value.strftime("%d/%m/%Y"), size=size)


def _draw_decimal(c, x: float, y: float, value: Optional[float], decimals: int = 2, size: float = 8.2):
    if value is None:
        return
    txt = f"{value:.{decimals}f}".replace(".", ",")
    _draw_text(c, x, y, txt, size=size)


def _draw_fraction_number(c, x: float, y: float, value: Optional[float], size: float = 8.0):
    """Affiche Q/S avec deux décimales, conformément au format du formulaire."""
    if value is None:
        return
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return

    txt = f"{numeric:.2f}".replace(".", ",")
    _draw_text(c, x, y, txt, size=size)


def _draw_form_x(c, x: float, y: float, checked: bool, size: float = 7.0):
    """Petit X calibré pour rester à l'intérieur des cases du C4-Enseignement."""
    if not checked:
        return
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, "X")


def _draw_niss(c, x: float, y: float, niss: str, size: float = 8.2):
    value = re.sub(r"\D", "", niss or "")
    if len(value) == 11:
        value = f"{value[:6]}/{value[6:9]}-{value[9:]}"
    _draw_text(c, x, y, value, size=size)


def _quarter_parts(label: str) -> tuple[str, str]:
    if not label or "/" not in label:
        return "", ""
    q, year = label.split("/", 1)
    return q, year


def _mask_pdf_area(c, x: float, y: float, width: float, height: float):
    """Masque uniquement la zone de saisie, sans toucher aux libellés du formulaire."""
    if width <= 0 or height <= 0:
        return
    c.saveState()
    c.setFillColorRGB(1, 1, 1)
    c.setStrokeColorRGB(1, 1, 1)
    c.rect(x, y, width, height, stroke=0, fill=1)
    c.restoreState()


def _fit_text_size(text: str, max_width: float, preferred: float, minimum: float = 5.8) -> float:
    value = str(text or "").strip()
    if not value or max_width <= 0:
        return preferred
    size = preferred
    while size > minimum and stringWidth(value, "Helvetica", size) > max_width:
        size -= 0.2
    return max(size, minimum)


def _draw_clean_value(
    c,
    x: float,
    y: float,
    text: object,
    *,
    size: float = 7.6,
    max_width: Optional[float] = None,
    mask_width: Optional[float] = None,
    align: str = "left",
):
    """
    Inscrit une valeur proprement sur le formulaire.

    Les pointillés / tirets préimprimés sont masqués uniquement sous la valeur afin
    d'éviter l'effet « texte posé sur les tirets » visible lors des premiers tests.
    """
    if text is None:
        return
    # Les champs de cette fonction sont des champs sur une seule ligne.
    # On remplace donc les retours à la ligne, tabulations et espaces insécables
    # par un espace normal. Cela évite notamment le carré noir qui apparaissait
    # entre le numéro de maison et le code postal dans l'adresse du MDP.
    value = str(text).replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return

    available = max_width if max_width is not None else 9999.0
    font_size = _fit_text_size(value, available, size)
    text_width = stringWidth(value, "Helvetica", font_size)

    if align == "right":
        text_x = x - text_width
        area_x = text_x - 1.2
    else:
        text_x = x
        area_x = x - 1.2

    area_width = mask_width if mask_width is not None else text_width + 2.6
    if align == "right" and mask_width is not None:
        area_x = x - mask_width

    _mask_pdf_area(c, area_x, y - 1.8, area_width, font_size + 3.1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", font_size)
    c.drawString(text_x, y, value)


def _draw_clean_date(c, x: float, y: float, value: Optional[date], mask_width: float = 91.0, size: float = 7.5):
    if not value:
        return
    _mask_pdf_area(c, x - 1.0, y - 1.8, mask_width, size + 3.1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", size)
    c.drawString(x, y, value.strftime("%d/%m/%Y"))


def _draw_clean_money(c, x_right: float, y: float, value: Optional[float], field_left: float, field_width: float, size: float = 7.5):
    if value is None:
        return
    txt = f"{float(value):.2f}".replace(".", ",")
    _mask_pdf_area(c, field_left, y - 1.8, field_width, size + 3.1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", size)
    c.drawRightString(x_right, y, txt)


def _draw_box_x(c, left: float, bottom: float, width: float = 6.5, height: float = 6.5):
    """Centre un X dans une case préimprimée du formulaire."""
    size = min(5.1, height * 0.82)
    x_width = stringWidth("X", "Helvetica-Bold", size)
    x = left + (width - x_width) / 2.0
    # Helvetica n'a pas de descendeur sur X; ce calcul centre le corps du glyphe.
    y = bottom + (height - size * 0.72) / 2.0
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, "X")


def _draw_clean_fraction(c, x: float, y: float, value: Optional[float], field_width: float = 65.0, size: float = 7.6):
    """Affiche toujours la fraction avec deux décimales : 4,00 / 24,00."""
    if value is None:
        return
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return

    txt = f"{numeric:.2f}".replace(".", ",")
    _mask_pdf_area(c, x - 1.0, y - 1.8, field_width, size + 3.1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", size)
    c.drawString(x, y, txt)


def generate_c4_enseignement_pdf(data: dict, template_pdf: bytes) -> bytes:
    """
    Génère le C4-Enseignement ONEM 06.07.2023/830.10.015.

    Cette version utilise une table de coordonnées relevées directement sur le
    formulaire officiel. Les zones préimprimées sont masquées uniquement sous les
    valeurs, ce qui donne un résultat nettement plus propre à l'impression.
    """
    occupations = data.get("occupations", [])
    interruptions = data.get("interruptions", [])

    # Coordonnées relevées sur les trois cadres du formulaire officiel.
    occ_layouts = [
        {
            "function_y": 571.2, "status_y": 555.7, "q_y": 538.2, "s_y": 524.3,
            "entry_y": 571.2, "end_y": 555.7, "salary_y": 536.2,
            "exact1_y": 521.9, "exact2_y": 505.8,
            "mode_boxes": [(325.2, 492.8, 4.8, 4.8), (341.5, 492.8, 4.8, 4.8), (357.8, 492.8, 4.8, 4.8)],
            "onss_boxes": [(186.2, 474.4, 5.8, 5.8), (186.2, 464.3, 5.8, 5.8), (186.2, 454.9, 5.8, 5.8), (186.2, 444.8, 5.8, 5.8)],
            "onss_date_y": 462.7,
        },
        {
            "function_y": 421.6, "status_y": 406.1, "q_y": 388.6, "s_y": 374.7,
            "entry_y": 421.6, "end_y": 406.1, "salary_y": 386.6,
            "exact1_y": 372.3, "exact2_y": 356.2,
            "mode_boxes": [(324.5, 338.8, 4.8, 4.8), (340.8, 338.8, 4.8, 4.8), (357.4, 338.8, 4.8, 4.8)],
            "onss_boxes": [(186.2, 325.3, 5.8, 5.8), (186.2, 315.2, 5.8, 5.8), (186.2, 305.9, 5.8, 5.8), (186.2, 295.8, 5.8, 5.8)],
            "onss_date_y": 313.5,
        },
        {
            "function_y": 272.4, "status_y": 256.9, "q_y": 239.4, "s_y": 225.5,
            "entry_y": 272.4, "end_y": 256.9, "salary_y": 237.4,
            "exact1_y": 223.1, "exact2_y": 207.0,
            "mode_boxes": [(324.5, 189.5, 4.8, 4.8), (340.8, 189.5, 4.8, 4.8), (357.4, 189.5, 4.8, 4.8)],
            "onss_boxes": [(186.2, 176.3, 5.8, 5.8), (186.2, 166.2, 5.8, 5.8), (186.2, 156.6, 5.8, 5.8), (186.2, 146.5, 5.8, 5.8)],
            "onss_date_y": 164.5,
        },
    ]

    def page1(c):
        # ----------------------------------------------------
        # IDENTITE / ETABLISSEMENT
        # ----------------------------------------------------
        niss = re.sub(r"\D", "", data.get("niss", "") or "")
        if len(niss) == 11:
            niss = f"{niss[:6]}/{niss[6:9]}-{niss[9:]}"

        _draw_clean_value(c, 91, 721.0, niss, size=7.7, max_width=96, mask_width=98)
        _draw_clean_value(c, 252, 721.0, data.get("employee_name", ""), size=7.7, max_width=285)
        _draw_clean_value(c, 88, 694.4, data.get("employee_address", ""), size=7.35, max_width=455)
        _draw_clean_value(c, 168, 668.2, data.get("establishment_name", ""), size=7.45, max_width=380)
        _draw_clean_value(c, 30, 643.6, data.get("establishment_address", ""), size=7.35, max_width=520)
        _draw_clean_value(c, 52, 618.0, BCE_FWB_ENSEIGNEMENT, size=7.7, max_width=95, mask_width=102)

        # ----------------------------------------------------
        # OCCUPATIONS - MAXIMUM 3
        # ----------------------------------------------------
        for idx, occ in enumerate(occupations[:3]):
            lay = occ_layouts[idx]

            _draw_clean_value(c, 62, lay["function_y"], occ.get("fonction", ""), size=7.35, max_width=172)
            _draw_clean_value(c, 55, lay["status_y"], occ.get("statut", ""), size=7.35, max_width=180)

            # On masque toute la zone Q/S afin de supprimer les virgules et tirets préimprimés.
            _draw_clean_fraction(c, 132.5, lay["q_y"], occ.get("q"), field_width=70, size=7.45)
            _draw_clean_fraction(c, 132.5, lay["s_y"], occ.get("s"), field_width=70, size=7.45)

            _draw_clean_date(c, 304, lay["entry_y"], occ.get("start_date"), mask_width=92, size=7.45)
            _draw_clean_date(c, 304, lay["end_y"], occ.get("end_date"), mask_width=92, size=7.45)

            # Montants alignés à droite dans leurs zones.
            _draw_clean_money(c, 431, lay["salary_y"], occ.get("salary_monthly"), 347, 86, size=7.45)

            if occ.get("dmfa_state") == "Non / le salaire brut exact doit être complété":
                _draw_clean_money(c, 416, lay["exact1_y"], occ.get("exact_total"), 327, 91, size=7.35)
                qtr, year = _quarter_parts(occ.get("quarter_label", ""))
                quarter_text = f"{qtr}/{year}" if qtr and year else ""
                _draw_clean_value(c, 493, lay["exact1_y"], quarter_text, size=7.2, max_width=61, mask_width=63)

            # Mode de paiement - les X sont centrés dans les cases réelles.
            mode = str(occ.get("mode_payment", ""))
            for value, box in zip(("10", "12", "20"), lay["mode_boxes"]):
                if mode == value:
                    _draw_box_x(c, *box)

            # Cotisations ONSS.
            onss_text = (occ.get("onss_text", "") or "").strip()
            box1, box2, box3, box4 = lay["onss_boxes"]

            if onss_text.startswith("ont été prélevées du"):
                _draw_box_x(c, *box2)
                _draw_clean_date(c, 252, lay["onss_date_y"], occ.get("start_date"), mask_width=84, size=6.8)
                _draw_clean_date(c, 348, lay["onss_date_y"], occ.get("end_date"), mask_width=92, size=6.8)
            elif onss_text.startswith("ont été prélevées"):
                _draw_box_x(c, *box1)
            elif onss_text.startswith("n'ont pas été prélevées"):
                _draw_box_x(c, *box3)
            elif onss_text.startswith("seront versées"):
                _draw_box_x(c, *box4)

        # ----------------------------------------------------
        # INTERRUPTIONS
        # ----------------------------------------------------
        if interruptions:
            _draw_box_x(c, 128.4, 93.2, 6.5, 6.5)  # avec interruption
            for row in interruptions[:2]:
                if row.get("kind") == "Protection de la maternité":
                    _draw_box_x(c, 204.0, 93.2, 6.5, 6.5)
                    _draw_clean_date(c, 328.5, 91.2, row.get("start"), mask_width=89, size=6.6)
                    _draw_clean_date(c, 433.0, 91.2, row.get("end"), mask_width=89, size=6.6)
                else:
                    _draw_box_x(c, 204.0, 81.2, 6.5, 6.5)
                    _draw_clean_date(c, 328.5, 79.2, row.get("start"), mask_width=89, size=6.6)
                    _draw_clean_date(c, 433.0, 79.2, row.get("end"), mask_width=89, size=6.6)
                    _draw_clean_value(c, 394, 68.5, row.get("nature", ""), size=6.5, max_width=140)
        else:
            _draw_box_x(c, 35.0, 93.2, 6.5, 6.5)  # sans interruption

        _draw_clean_value(c, 68, 50.4, data.get("remarks", ""), size=6.7, max_width=465)

    def page2(c):
        # ----------------------------------------------------
        # NISS
        # ----------------------------------------------------
        niss = re.sub(r"\D", "", data.get("niss", "") or "")
        if len(niss) == 11:
            niss = f"{niss[:6]}/{niss[6:9]}-{niss[9:]}"
        _draw_clean_value(c, 142, 803.6, niss, size=7.5, max_width=145, mask_width=147)

        end_date = data.get("final_end_date")
        end_reason = data.get("end_reason", "")

        # ----------------------------------------------------
        # DONNEES RELATIVES A LA FIN DE LA DERNIERE OCCUPATION
        # ----------------------------------------------------
        if end_reason == "Fin de plein droit et sans préavis":
            # Cette ligne n'a volontairement PAS de case à cocher sur le formulaire ONEM.
            _draw_clean_date(c, 211, 765.2, end_date, mask_width=92, size=7.4)

        elif end_reason == "Le pouvoir organisateur a mis fin à l'occupation avec préavis":
            _draw_box_x(c, 29.5, 719.2, 6.5, 6.5)
            _draw_clean_date(c, 209, 717.2, end_date, mask_width=90, size=7.2)

            notice_method = data.get("notice_method", "Lettre recommandée")
            if notice_method == "Lettre recommandée":
                _draw_box_x(c, 141.8, 701.2, 6.5, 6.5)
            elif notice_method == "Exploit d'huissier":
                _draw_box_x(c, 141.8, 683.2, 6.5, 6.5)

            _draw_clean_date(c, 157, 663.2, data.get("notice_start"), mask_width=89, size=7.0)
            _draw_clean_date(c, 261, 663.2, data.get("notice_end"), mask_width=89, size=7.0)

            suspended = bool(data.get("notice_suspended"))
            if suspended:
                _draw_box_x(c, 251.8, 647.2, 6.5, 6.5)
            else:
                _draw_box_x(c, 159.6, 647.2, 6.5, 6.5)

            if suspended:
                suspension_reason = data.get("notice_suspension_reason", "")
                if suspension_reason == "Maladie":
                    _draw_box_x(c, 377.3, 647.2, 6.5, 6.5)
                elif suspension_reason == "Vacances":
                    _draw_box_x(c, 377.3, 629.2, 6.5, 6.5)
                elif suspension_reason:
                    _draw_box_x(c, 377.3, 611.2, 6.5, 6.5)
                    _draw_clean_value(c, 412, 610.4, suspension_reason, size=6.8, max_width=125)
                _draw_clean_date(c, 189, 594.0, data.get("notice_extended_until"), mask_width=90, size=7.0)

            transition = bool(data.get("transition"))
            if transition:
                _draw_box_x(c, 106.8, 560.0, 5.8, 5.8)
                _draw_clean_date(c, 141, 558.0, data.get("transition_start"), mask_width=89, size=6.8)
                _draw_clean_date(c, 246, 558.0, data.get("transition_end"), mask_width=89, size=6.8)
            else:
                _draw_box_x(c, 79.0, 560.0, 6.0, 5.8)

        elif end_reason == "Le pouvoir organisateur a mis fin à l'occupation sans préavis":
            _draw_box_x(c, 29.5, 512.0, 6.5, 6.5)
            _draw_clean_date(c, 253, 510.0, end_date, mask_width=90, size=7.2)

        elif end_reason == "Le membre du personnel a quitté volontairement son emploi":
            _draw_box_x(c, 29.5, 494.0, 6.5, 6.5)
            _draw_clean_date(c, 211, 492.0, end_date, mask_width=90, size=7.2)

        # ----------------------------------------------------
        # INDEMNITE DE RUPTURE
        # ----------------------------------------------------
        if data.get("rupture_indemnity"):
            _draw_box_x(c, 29.5, 737.2, 6.5, 6.5)
            _draw_clean_date(c, 248.5, 735.2, data.get("rupture_start"), mask_width=89, size=7.0)
            _draw_clean_date(c, 355.0, 735.2, data.get("rupture_end"), mask_width=89, size=7.0)

        # ----------------------------------------------------
        # MOTIF DU CHOMAGE
        # ----------------------------------------------------
        motive = (data.get("motif_chomage", "") or "").strip()
        if not motive:
            motive = {
                "Fin de plein droit et sans préavis": "Fin de l'occupation de plein droit",
                "Le pouvoir organisateur a mis fin à l'occupation avec préavis": "Fin de l'occupation à l'initiative du pouvoir organisateur avec préavis",
                "Le pouvoir organisateur a mis fin à l'occupation sans préavis": "Fin de l'occupation à l'initiative du pouvoir organisateur sans préavis",
                "Le membre du personnel a quitté volontairement son emploi": "Départ volontaire du membre du personnel",
            }.get(end_reason, "")

        if motive:
            # Deux lignes pointillées sont prévues sur le formulaire.
            words = motive.split()
            lines = []
            current = ""
            for word in words:
                proposal = word if not current else f"{current} {word}"
                if stringWidth(proposal, "Helvetica", 7.2) <= 452:
                    current = proposal
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
            for i, line in enumerate(lines[:2]):
                _draw_clean_value(c, 98 if i == 0 else 29, 468.0 - i * 18.0, line, size=7.2, max_width=455 if i == 0 else 525)

        # ----------------------------------------------------
        # DATE / RESPONSABLE
        # ----------------------------------------------------
        _draw_clean_date(c, 46, 369.6, data.get("declaration_date"), mask_width=90, size=7.2)
        # Le nom du responsable doit apparaître dans l'espace de signature AU-DESSUS
        # du libellé imprimé "nom et signature du responsable...".
        # Il reste suffisamment d'espace pour apposer la signature manuscrite.
        _draw_clean_value(c, 228, 386.0, data.get("responsible_name", ""), size=7.0, max_width=285)

    # Page 3 : réservée au membre du personnel, donc laissée intacte.
    return _merge_overlays(template_pdf, {0: page1, 1: page2})


def generate_c4_classique_pdf(data: dict, template_pdf: bytes) -> bytes:
    def page1(c):
        _draw_niss(c, 92, 666, data.get("niss", ""))
        _draw_text(c, 250, 666, data.get("employee_name", ""), 8.0, 78)
        _draw_text(c, 92, 638, data.get("employer_name", ""), 7.8, 55)
        _draw_text(c, 314, 638, data.get("employer_category", ""), 7.6, 18)
        _draw_text(c, 437, 638, data.get("enterprise_number", ""), 7.8, 22)
        _draw_text(c, 314, 613, data.get("joint_committee", ""), 7.8, 16)
        _draw_text(c, 449, 613, data.get("onss_number", ""), 7.8, 20)
        _draw_multiline(c, 28, 587, data.get("employer_address", ""), 7.8, 8.5, 112)

        _draw_date(c, 138, 555, data.get("occupation_start"), 7.8)
        _draw_date(c, 385, 555, data.get("service_start"), 7.8)
        _draw_date(c, 146, 533, data.get("occupation_end"), 7.8)
        _draw_text(c, 348, 533, data.get("worker_code", ""), 7.8, 8)
        _draw_text(c, 55, 520, data.get("status", ""), 7.8, 30)
        _draw_text(c, 149, 491, data.get("employment_measure", ""), 7.8, 15)

        onss_case = data.get("onss_case", "Prélevées")
        _draw_check(c, 163, 475, onss_case == "Prélevées")
        _draw_check(c, 276, 475, onss_case == "Non prélevées et non versées")
        _draw_check(c, 27, 462, onss_case == "Non retenues mais seront versées")
        _draw_check(c, 229, 462, onss_case == "Statutaire art. 9")

        _draw_decimal(c, 49, 436, data.get("q"), 2, 8.0)
        _draw_decimal(c, 49, 415, data.get("s"), 2, 8.0)
        _draw_decimal(c, 144, 396, data.get("theoretical_salary"), 2, 8.0)

        freq = data.get("salary_frequency", "par mois")
        freq_coords = {
            "par heure": (48, 383), "par mois": (48, 370), "par jour": (48, 357),
            "par semaine": (48, 344), "par trimestre": (48, 331), "par année": (225, 383),
        }
        if freq in freq_coords:
            _draw_check(c, *freq_coords[freq], True)

        if data.get("exact_gross") is not None:
            _draw_decimal(c, 118, 309, data.get("exact_gross"), 2, 8.0)
            qtr, year = _quarter_parts(data.get("quarter_label", ""))
            _draw_text(c, 296, 309, qtr, 7.8)
            _draw_text(c, 319, 309, year, 7.8)

        vacation_type = data.get("vacation_type", "Temps partiel")
        if vacation_type == "Temps plein":
            _draw_check(c, 63, 263, True)
            _draw_decimal(c, 167, 263, data.get("vacation_amount"), 2, 7.8)
        else:
            _draw_check(c, 63, 251, True)
            _draw_decimal(c, 172, 251, data.get("vacation_amount"), 2, 7.8)

        public_regime = data.get("public_regime", "Non applicable")
        _draw_check(c, 389, 232, public_regime == "Secteur public")
        _draw_check(c, 451, 232, public_regime == "Secteur privé")

        holidays = data.get("paid_holidays_after_end", [])
        _draw_check(c, 42, 205, len(holidays) == 0)
        _draw_check(c, 72, 205, len(holidays) > 0)
        for idx, d in enumerate(holidays[:4]):
            _draw_date(c, 103 + idx * 92, 205, d, 6.8)

        comp_days = float(data.get("comp_rest_days", 0) or 0)
        _draw_check(c, 243, 172, comp_days <= 0)
        _draw_check(c, 271, 172, comp_days > 0)
        if comp_days > 0:
            _draw_decimal(c, 358, 172, comp_days, 2, 7.5)

    def page2(c):
        _draw_niss(c, 143, 809, data.get("niss", ""))

        qtr_rows = data.get("quarter_rows", [])
        for idx, row in enumerate(qtr_rows[:2]):
            y = 705 - idx * 41
            _draw_date(c, 52, y, row.get("start"), 7.2)
            _draw_date(c, 192, y, row.get("end"), 7.2)
            _draw_check(c, 448, y + 2, not row.get("interruption", False))
            _draw_check(c, 500, y + 2, row.get("interruption", False))
            _draw_check(c, 448, y - 14, not row.get("q_diff", False))
            _draw_check(c, 500, y - 14, row.get("q_diff", False))

        reason = data.get("end_reason", "Durée déterminée arrivée à terme")
        reason_coords = {
            "Préavis par l'employeur": (38, 604),
            "Rupture par l'employeur": (38, 555),
            "Démission / abandon volontaire": (38, 539),
            "Commun accord": (38, 522),
            "Force majeure médicale": (38, 506),
            "Force majeure autre": (38, 489),
            "Durée déterminée arrivée à terme": (38, 473),
            "Travail déterminé arrivé à terme": (38, 457),
        }
        if reason in reason_coords:
            _draw_check(c, *reason_coords[reason], True)

        end_date = data.get("occupation_end")
        if reason == "Préavis par l'employeur":
            method = data.get("notice_method", "Lettre recommandée")
            _draw_check(c, 59, 588, method == "Lettre recommandée")
            _draw_check(c, 59, 572, method == "Exploit d'huissier")
            _draw_date(c, 220, 588 if method == "Lettre recommandée" else 572, data.get("notice_sent"), 7.4)
        elif reason in ("Rupture par l'employeur", "Démission / abandon volontaire", "Commun accord", "Force majeure autre"):
            y = {
                "Rupture par l'employeur": 555,
                "Démission / abandon volontaire": 539,
                "Commun accord": 522,
                "Force majeure autre": 489,
            }[reason]
            _draw_date(c, 170, y, end_date, 7.4)
        elif reason == "Force majeure médicale":
            pass

        _draw_multiline(c, 173, 441, data.get("precise_reason", ""), 7.2, 9.0, 90)

        indemnity_type = data.get("indemnity_type", "Aucune")
        if indemnity_type == "Salaire pendant le délai de préavis":
            _draw_check(c, 32, 358, True)
            _draw_check(c, 68, 309, True)
            _draw_date(c, 181, 309, data.get("indemnity_start"), 7.2)
            _draw_date(c, 347, 309, data.get("indemnity_end"), 7.2)

    def page3(c):
        _draw_niss(c, 143, 809, data.get("niss", ""))
        indemnity_type = data.get("indemnity_type", "Aucune")
        if indemnity_type == "Indemnité de congé / rupture":
            _draw_check(c, 40, 778, True)
            _draw_check(c, 65, 753, True)
            _draw_date(c, 171, 753, data.get("indemnity_start"), 7.2)
            _draw_date(c, 302, 753, data.get("indemnity_end"), 7.2)
        elif indemnity_type == "Autre indemnité":
            _draw_check(c, 40, 363, True)
            _draw_text(c, 160, 347, data.get("other_indemnity_name", ""), 7.2, 70)
            _draw_check(c, 65, 291, True)
            _draw_date(c, 190, 291, data.get("indemnity_start"), 7.2)
            _draw_date(c, 335, 291, data.get("indemnity_end"), 7.2)
            _draw_decimal(c, 175, 272, data.get("other_indemnity_amount"), 2, 7.2)
        _draw_multiline(c, 28, 207, data.get("remarks", ""), 7.2, 9.0, 110)

    def page4(c):
        _draw_niss(c, 143, 809, data.get("niss", ""))
        pact = data.get("pact_generations", "Non concerné / ne pas compléter")
        if pact == "Non concerné / ne pas compléter":
            _draw_check(c, 27, 765, True)
        elif pact == "Licenciement - cellule emploi créée":
            _draw_check(c, 59, 724, True)
        elif pact == "Licenciement - pas de cellule emploi":
            _draw_check(c, 59, 713, True)
        elif pact == "Pas un licenciement":
            _draw_check(c, 59, 702, True)

        complementary = data.get("complementary_indemnity", "Non")
        _draw_check(c, 59, 666, complementary == "Oui")
        _draw_check(c, 59, 655, complementary == "Non")

        _draw_date(c, 54, 527, data.get("declaration_date"), 7.8)
        # Le nom est placé au-dessus de l’intitulé afin de garder la ligne imprimée lisible.\n        _draw_text(c, 199, 542, data.get("responsible_name", ""), 7.8, 72)

    return _merge_overlays(template_pdf, {0: page1, 1: page2, 2: page3, 3: page4})


# ============================================================
# INTERFACE C4 CLASSIQUE
# ============================================================

def render_c4_classique_manuel():
    st.subheader("2. Fiche(s) de paie")
    uploaded_files = st.file_uploader(
        "Importer une ou plusieurs fiches de paie PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="c4_classic_payroll_files",
    )

    entries: list[PayrollEntry] = []
    if uploaded_files:
        entries, extraction_errors = extract_payroll_entries(uploaded_files)
        for error in extraction_errors:
            st.warning(error)

    base_entry = entries[0] if entries else PayrollEntry("", 0, "")

    st.subheader("3. Travailleur et employeur")
    c1, c2 = st.columns(2)
    with c1:
        employee_name = st.text_input("Nom et prénom", value=base_entry.employee_name, key="c4c_employee_name")
        niss = st.text_input("NISS", key="c4c_niss")
    with c2:
        employer_name = st.text_input("Employeur / Pouvoir organisateur", key="c4c_employer_name")
        enterprise_number = st.text_input("Numéro d'entreprise (BCE)", key="c4c_bce")

    employer_address = st.text_area("Adresse de l'employeur", key="c4c_employer_address")
    c1, c2, c3 = st.columns(3)
    with c1:
        employer_category = st.text_input("Catégorie employeur", key="c4c_employer_category")
    with c2:
        joint_committee = st.text_input("Commission paritaire", key="c4c_joint_committee")
    with c3:
        onss_number = st.text_input("Numéro ONSS", key="c4c_onss_number")

    st.subheader("4. Données concernant l'occupation")
    c1, c2, c3 = st.columns(3)
    with c1:
        occupation_start_txt = _masked_date_input(
            "Date de début de l'occupation",
            key="c4c_occ_start",
        )
        service_start_txt = _masked_date_input(
            "Date d'entrée en service",
            key="c4c_service_start",
        )
    with c2:
        occupation_end_txt = _masked_date_input(
            "Date de fin de l'occupation",
            key="c4c_occ_end",
        )
        worker_code = st.text_input("Code travailleur", key="c4c_worker_code")
    with c3:
        status = st.text_input("Statut", key="c4c_status")
        employment_measure = st.text_input("Mesure de promotion de l'emploi", value="APE" if "APE" in st.session_state.get("c4_personnel_type", "") else "", key="c4c_employment_measure")

    occupation_start, e1 = _parse_user_date(occupation_start_txt)
    service_start, e2 = _parse_user_date(service_start_txt)
    occupation_end, e3 = _parse_user_date(occupation_end_txt)

    c1, c2, c3 = st.columns(3)
    with c1:
        q = st.number_input("Q", min_value=0.0, value=float(base_entry.q or 0), step=0.01, key="c4c_q")
    with c2:
        s = st.number_input("S", min_value=0.0, value=float(base_entry.s or 0), step=0.01, key="c4c_s")
    with c3:
        theoretical_salary = st.number_input(
            "Salaire brut moyen théorique",
            min_value=0.0,
            value=float(base_entry.gross or 0),
            step=0.01,
            key="c4c_theoretical_salary",
            help="La fiche de paie peut proposer un montant, mais vérifiez qu'il s'agit bien du salaire brut moyen théorique du C4 classique.",
        )

    salary_frequency = st.selectbox(
        "Périodicité du salaire brut moyen théorique",
        ["par mois", "par heure", "par jour", "par semaine", "par trimestre", "par année"],
        key="c4c_salary_frequency",
    )

    onss_case = st.selectbox(
        "Cotisations ONSS - secteur chômage",
        ["Prélevées", "Non prélevées et non versées", "Non retenues mais seront versées", "Statutaire art. 9"],
        key="c4c_onss_case",
    )

    exact_gross = st.number_input("Salaire brut exact du trimestre (0 si non requis)", min_value=0.0, value=0.0, step=0.01, key="c4c_exact_gross")
    quarter_label = ""
    if occupation_end:
        _, _, _, quarter_label = quarter_info(occupation_end)
        st.caption(f"Trimestre correspondant à la fin d'occupation : {quarter_label}")

    vacation_type = st.radio("Vacances légales", ["Temps partiel", "Temps plein"], horizontal=True, key="c4c_vacation_type")
    vacation_amount = st.number_input("Nombre d'heures (temps partiel) ou de jours (temps plein) de vacances rémunérées", min_value=0.0, value=0.0, step=0.5, key="c4c_vacation_amount")
    public_regime = st.selectbox("Régime de vacances - pouvoirs publics", ["Non applicable", "Secteur public", "Secteur privé"], key="c4c_public_regime")

    holidays_text = st.text_input(
        "Jours fériés payés après la fin du contrat (séparés par des virgules, JJ/MM/AAAA)",
        key="c4c_holidays",
    )
    paid_holidays_after_end: list[date] = []
    holiday_errors = []
    for chunk in [x.strip() for x in holidays_text.split(",") if x.strip()]:
        d, err = _parse_user_date(chunk)
        if d:
            paid_holidays_after_end.append(d)
        if err:
            holiday_errors.append(chunk)

    comp_rest_days = st.number_input("Jours encore rémunérés après la fin pour repos compensatoire / heures supplémentaires", min_value=0.0, value=0.0, step=0.5, key="c4c_comp_rest")

    st.subheader("5. Trimestres ONSS non encore déclarés ou acceptés")
    quarter_rows = []
    qrow_count = int(st.number_input("Nombre de trimestres à mentionner", min_value=0, max_value=2, value=0, step=1, key="c4c_qrow_count"))
    for i in range(qrow_count):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            a = st.text_input("Du", placeholder="JJ/MM/AAAA", key=f"c4c_qr_{i}_start")
        with c2:
            b = st.text_input("Au", placeholder="JJ/MM/AAAA", key=f"c4c_qr_{i}_end")
        with c3:
            interruption = st.checkbox("Interruption", key=f"c4c_qr_{i}_int")
        with c4:
            q_diff = st.checkbox("Heures ≠ Q", key=f"c4c_qr_{i}_qdiff")
        da, _ = _parse_user_date(a) if a else (None, None)
        db, _ = _parse_user_date(b) if b else (None, None)
        quarter_rows.append({"start": da, "end": db, "interruption": interruption, "q_diff": q_diff})

    st.subheader("6. Fin de l'occupation")
    end_reason = st.selectbox(
        "Comment le contrat a-t-il pris fin ?",
        [
            "Durée déterminée arrivée à terme",
            "Travail déterminé arrivé à terme",
            "Préavis par l'employeur",
            "Rupture par l'employeur",
            "Démission / abandon volontaire",
            "Commun accord",
            "Force majeure médicale",
            "Force majeure autre",
        ],
        key="c4c_end_reason",
    )
    precise_reason = st.text_area("Motif précis du chômage (si requis)", key="c4c_precise_reason")

    notice_method = "Lettre recommandée"
    notice_sent = None
    if end_reason == "Préavis par l'employeur":
        notice_method = st.radio("Notification du préavis", ["Lettre recommandée", "Exploit d'huissier"], horizontal=True, key="c4c_notice_method")
        notice_sent_txt = st.text_input("Date d'envoi / notification", placeholder="JJ/MM/AAAA", key="c4c_notice_sent")
        notice_sent, _ = _parse_user_date(notice_sent_txt) if notice_sent_txt else (None, None)

    st.subheader("7. Indemnité liée à la fin")
    indemnity_type = st.selectbox(
        "Une indemnité a-t-elle été payée ?",
        ["Aucune", "Salaire pendant le délai de préavis", "Indemnité de congé / rupture", "Autre indemnité"],
        key="c4c_indemnity_type",
    )
    indemnity_start = indemnity_end = None
    other_indemnity_name = ""
    other_indemnity_amount = 0.0
    if indemnity_type != "Aucune":
        c1, c2 = st.columns(2)
        with c1:
            x = st.text_input("Période couverte - du", placeholder="JJ/MM/AAAA", key="c4c_ind_start")
        with c2:
            y = st.text_input("Période couverte - au", placeholder="JJ/MM/AAAA", key="c4c_ind_end")
        indemnity_start, _ = _parse_user_date(x) if x else (None, None)
        indemnity_end, _ = _parse_user_date(y) if y else (None, None)
        if indemnity_type == "Autre indemnité":
            other_indemnity_name = st.text_input("Nature de l'autre indemnité", key="c4c_other_ind_name")
            other_indemnity_amount = st.number_input("Montant", min_value=0.0, value=0.0, step=0.01, key="c4c_other_ind_amount")

    remarks = st.text_area("Remarques", key="c4c_remarks")

    st.subheader("8. Partie E et signature employeur")
    pact_generations = st.selectbox(
        "Pacte des générations",
        ["Non concerné / ne pas compléter", "Licenciement - cellule emploi créée", "Licenciement - pas de cellule emploi", "Pas un licenciement"],
        key="c4c_pact",
    )
    complementary_indemnity = st.radio("Indemnité complémentaire sans cotisations salariales ONSS ?", ["Non", "Oui"], horizontal=True, key="c4c_compl_ind")
    responsible_name = st.text_input("Nom du responsable / délégué", key="c4c_responsible")
    declaration_date = st.date_input("Date de la déclaration", value=date.today(), format="DD/MM/YYYY", key="c4c_decl_date")

    errors = []
    if e1: errors.append("Date de début de l'occupation manquante ou invalide.")
    if e2: errors.append("Date d'entrée en service manquante ou invalide.")
    if e3: errors.append("Date de fin de l'occupation manquante ou invalide.")
    if not employee_name.strip(): errors.append("Nom du travailleur manquant.")
    if len(re.sub(r"\D", "", niss)) != 11: errors.append("Le NISS doit contenir 11 chiffres.")
    if not employer_name.strip(): errors.append("Employeur / PO manquant.")
    if not enterprise_number.strip() and not onss_number.strip(): errors.append("Complétez au moins le numéro d'entreprise ou le numéro ONSS.")
    if q <= 0 or s <= 0: errors.append("Q et S doivent être supérieurs à 0.")
    if theoretical_salary <= 0: errors.append("Salaire brut moyen théorique manquant.")
    if holiday_errors: errors.append("Une ou plusieurs dates de jours fériés sont invalides.")
    if not responsible_name.strip(): errors.append("Nom du responsable / délégué manquant.")

    for error in errors:
        st.warning(error)

    template_pdf, template_error = _template_bytes(TEMPLATE_C4_CLASSIQUE)
    if template_error:
        st.error(template_error)
        return

    if not _template_contains_version(template_pdf, EXPECTED_C4_CLASSIQUE_VERSION):
        st.error(
            "Le PDF placé dans assets/c4_classique_officiel.pdf ne correspond pas à la version "
            f"attendue ({EXPECTED_C4_CLASSIQUE_VERSION}). Les coordonnées d'impression pourraient être incorrectes."
        )
        return

    if errors:
        st.info("Corrigez les éléments ci-dessus avant de générer le C4 prêt à imprimer.")
        return

    data = {
        "employee_name": employee_name,
        "niss": niss,
        "employer_name": employer_name,
        "employer_address": employer_address,
        "employer_category": employer_category,
        "enterprise_number": enterprise_number,
        "joint_committee": joint_committee,
        "onss_number": onss_number,
        "occupation_start": occupation_start,
        "service_start": service_start,
        "occupation_end": occupation_end,
        "worker_code": worker_code,
        "status": status,
        "employment_measure": employment_measure,
        "onss_case": onss_case,
        "q": q,
        "s": s,
        "theoretical_salary": theoretical_salary,
        "salary_frequency": salary_frequency,
        "exact_gross": exact_gross if exact_gross > 0 else None,
        "quarter_label": quarter_label,
        "vacation_type": vacation_type,
        "vacation_amount": vacation_amount,
        "public_regime": public_regime,
        "paid_holidays_after_end": paid_holidays_after_end,
        "comp_rest_days": comp_rest_days,
        "quarter_rows": quarter_rows,
        "end_reason": end_reason,
        "precise_reason": precise_reason,
        "notice_method": notice_method,
        "notice_sent": notice_sent,
        "indemnity_type": indemnity_type,
        "indemnity_start": indemnity_start,
        "indemnity_end": indemnity_end,
        "other_indemnity_name": other_indemnity_name,
        "other_indemnity_amount": other_indemnity_amount,
        "remarks": remarks,
        "pact_generations": pact_generations,
        "complementary_indemnity": complementary_indemnity,
        "responsible_name": responsible_name,
        "declaration_date": declaration_date,
    }

    try:
        pdf_bytes = generate_c4_classique_pdf(data, template_pdf)
    except Exception as exc:
        st.error(f"La génération du PDF a échoué : {exc}")
        return

    st.success("Le C4 classique est prêt à imprimer. La rubrique du travailleur reste volontairement vierge.")
    st.download_button(
        "Télécharger le C4 classique prêt à imprimer",
        data=pdf_bytes,
        file_name="C4_certificat_chomage_complete.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# INTERFACE C4 CLASSIQUE - ACS / APE / PART-APE / PTP
# ============================================================

def render_c4_classique_acs_ape():
    """Prépare automatiquement le C4 classique à partir des mêmes fiches FWB.

    Les éléments fiables de la fiche de paie sont repris automatiquement : identité,
    Q/S, barème annuel, index, brut et éventuelle allocation foyer/résidence.
    Les données qui ne figurent pas de manière fiable sur la fiche (NISS, dates
    contractuelles, données du PO, code travailleur, vacances et motif de fin) restent
    à confirmer par la direction.
    """

    st.info(
        "Les situations ACS / APE / PART-APE / PTP utilisent le C4 classique. "
        "Vous pouvez importer les mêmes fiches de paie PDF que pour le C4-Enseignement."
    )

    # --------------------------------------------------------
    # 2. FICHES DE PAIE
    # --------------------------------------------------------
    st.subheader("2. Fiches de paie")

    uploaded_files = st.file_uploader(
        "Importer une ou plusieurs fiches de paie PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="c4_acs_payroll_files",
    )

    st.caption(
        "Le module lit les PDF pour effectuer les calculs mais ne les enregistre pas dans GitHub."
    )

    if not uploaded_files:
        st.info("Importez au moins une fiche de paie pour préremplir automatiquement le C4.")
        return

    entries, extraction_errors = extract_payroll_entries(uploaded_files)
    for error in extraction_errors:
        st.warning(error)

    if not entries:
        st.error("Aucune donnée exploitable n'a pu être extraite des fiches de paie.")
        return

    with st.expander("Voir les données détectées sur les fiches de paie"):
        rows = []
        for entry in entries:
            rows.append(
                {
                    "Source": f"{entry.file_name} – p. {entry.page_number}",
                    "Nom": entry.employee_name,
                    "Q/S": (
                        f"{entry.q:.2f}/{entry.s:.2f}".replace(".", ",")
                        if entry.q is not None and entry.s is not None
                        else "—"
                    ),
                    "Statut fiche": entry.status or "—",
                    "TAB": _format_money(entry.annual_base_salary),
                    "Index": (
                        f"{entry.pdf_index:.4f}".replace(".", ",")
                        if entry.pdf_index is not None
                        else "—"
                    ),
                    "Brut payé": _format_money(entry.gross),
                    "Période de paie": (
                        f"{_format_date(entry.period_start)} → {_format_date(entry.period_end)}"
                        if entry.period_start and entry.period_end
                        else "—"
                    ),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

    labels = [_entry_label(entry) for entry in entries]
    source_label = st.selectbox(
        "Quelle ligne de la fiche correspond à l'occupation qui prend fin ?",
        labels,
        key="c4_acs_source_entry",
    )
    source_entry = entries[labels.index(source_label)]

    # --------------------------------------------------------
    # SYNCHRONISATION DES DONNÉES EXTRAITES
    # --------------------------------------------------------
    # Streamlit conserve la valeur des widgets portant une clé identique entre
    # les reruns. Sans cette synchronisation, un champ ACS/APE déjà créé vide
    # pouvait rester vide après l'import d'une fiche de paie, même si le PDF
    # avait été correctement lu. On recharge donc les valeurs détectées chaque
    # fois que la fiche / page source change, sans écraser les corrections
    # manuelles lors des reruns suivants.
    source_signature = "|".join(
        [
            source_entry.file_name,
            str(source_entry.page_number),
            source_entry.employee_name or "",
            source_entry.employee_address or "",
            str(source_entry.q if source_entry.q is not None else ""),
            str(source_entry.s if source_entry.s is not None else ""),
            str(source_entry.annual_base_salary if source_entry.annual_base_salary is not None else ""),
            str(source_entry.pdf_index if source_entry.pdf_index is not None else ""),
            str(source_entry.gross if source_entry.gross is not None else ""),
        ]
    )

    if st.session_state.get("_c4_acs_prefill_signature") != source_signature:
        st.session_state["_c4_acs_prefill_signature"] = source_signature
        st.session_state["c4_acs_employee_name"] = source_entry.employee_name or ""
        st.session_state["c4_acs_employee_address"] = source_entry.employee_address or ""

        detected_q = float(source_entry.q or 0.0)
        detected_s = float(source_entry.s or 0.0)
        if abs(detected_q - 18.0) < 0.01 and abs(detected_s - 36.0) < 0.01:
            st.session_state["c4_acs_regime_horaire"] = "Mi-temps — 18/36"
        elif abs(detected_q - 32.0) < 0.01 and abs(detected_s - 36.0) < 0.01:
            st.session_state["c4_acs_regime_horaire"] = "4/5e temps — 32/36"
        elif abs(detected_q - 36.0) < 0.01 and abs(detected_s - 36.0) < 0.01:
            st.session_state["c4_acs_regime_horaire"] = "Temps plein — 36/36"

        # Recalcule la rémunération proposée pour la nouvelle fiche.
        st.session_state.pop("c4_acs_use_auto_salary", None)
        st.session_state.pop("c4_acs_theoretical_salary_manual", None)

    st.success("La fiche de paie a été lue et les données disponibles ont été récupérées.")
    info1, info2, info3 = st.columns(3)
    with info1:
        st.markdown(f"**Nom :** {source_entry.employee_name or '—'}")
        if source_entry.employee_address:
            st.markdown(
                "**Adresse détectée :** "
                + re.sub(r"\s+", " ", source_entry.employee_address).strip()
            )
        if source_entry.q is not None and source_entry.s is not None:
            st.markdown(
                "**Charge détectée :** "
                + f"{source_entry.q:.2f}/{source_entry.s:.2f}".replace(".", ",")
            )
        else:
            st.markdown("**Charge détectée :** —")
    with info2:
        st.markdown(f"**TAB :** {_format_money(source_entry.annual_base_salary)}")
        st.markdown(
            "**Index :** "
            + (
                f"{source_entry.pdf_index:.4f}".replace(".", ",")
                if source_entry.pdf_index is not None
                else "—"
            )
        )
    with info3:
        st.markdown(f"**Brut payé :** {_format_money(source_entry.gross)}")
        if source_entry.establishment_name:
            st.markdown(
                f"**Établissement détecté sur la fiche :** {source_entry.establishment_name}"
            )
        if source_entry.period_start and source_entry.period_end:
            st.markdown(
                f"**Période de paie :** {_format_date(source_entry.period_start)} → "
                f"{_format_date(source_entry.period_end)}"
            )
        else:
            st.markdown("**Période de paie :** —")

    missing_auto = []
    if not source_entry.employee_name:
        missing_auto.append("nom")
    if not source_entry.employee_address:
        missing_auto.append("adresse")
    if source_entry.q is None or source_entry.s is None:
        missing_auto.append("charge")
    if source_entry.annual_base_salary is None:
        missing_auto.append("TAB")
    if source_entry.pdf_index is None:
        missing_auto.append("index")
    if source_entry.gross is None:
        missing_auto.append("brut")
    if missing_auto:
        st.warning(
            "Certaines données n'ont pas été reconnues automatiquement sur cette fiche : "
            + ", ".join(missing_auto)
            + ". Les autres données détectées restent utilisables."
        )

    # --------------------------------------------------------
    # 3. TYPE DE PROGRAMME
    # --------------------------------------------------------
    st.subheader("3. Situation ACS / APE")

    detected_program = ""
    all_text = "\n".join(entry.raw_text.upper() for entry in entries)
    if "PART-APE" in all_text or "PART APE" in all_text:
        detected_program = "PART-APE"
    elif re.search(r"\bPTP\b", all_text):
        detected_program = "PTP"
    elif re.search(r"\bACS\b", all_text):
        detected_program = "ACS"
    elif re.search(r"\bAPE\b", all_text):
        detected_program = "APE"

    programme_options = ["ACS", "APE", "PART-APE", "PTP"]
    programme_index = programme_options.index(detected_program) if detected_program in programme_options else 0

    # Si le programme est explicitement présent sur la fiche, on le reprend
    # automatiquement lors du changement de source. Sinon, le choix reste manuel.
    programme_signature = f"{source_signature}|{detected_program}"
    if st.session_state.get("_c4_acs_programme_signature") != programme_signature:
        st.session_state["_c4_acs_programme_signature"] = programme_signature
        if detected_program in programme_options:
            st.session_state["c4_acs_programme"] = detected_program
        elif "c4_acs_programme" not in st.session_state:
            st.session_state["c4_acs_programme"] = programme_options[programme_index]

    programme = st.selectbox(
        "Type de programme",
        programme_options,
        key="c4_acs_programme",
    )

    fonction_option = st.selectbox(
        "Fonction",
        options=FONCTIONS_ACS_APE_OPTIONS,
        key="c4_acs_fonction",
        help=(
            "Les fonctions propres aux situations ACS/APE/PTP sont placées en tête de liste. "
            "Les autres fonctions ProEco apparaissent ensuite."
        ),
    )
    fonction_acs = _acs_ape_function_label(fonction_option)

    if fonction_acs == "Puériculteur(trice) PTP":
        st.info(
            "Puériculteur(trice) PTP : cette fonction requiert un titre requis ou suffisant "
            "et impose une charge horaire de 32/36e."
        )
        if programme != "PTP":
            st.warning(
                "La fonction « Puériculteur(trice) PTP » doit être utilisée avec le programme PTP."
            )

    if programme == "PTP":
        employment_measure = "2"
        st.caption("Mesure de promotion de l'emploi : code 2 (PTP), complété automatiquement.")
    else:
        employment_measure = ""
        st.caption(
            "Pour ACS / APE / PART-APE, le champ « mesure de promotion de l'emploi » du C4 "
            "reste vide. Le code 2 est réservé au PTP/SINE."
        )

    # --------------------------------------------------------
    # 4. TRAVAILLEUR / ETABLISSEMENT / EMPLOYEUR
    # --------------------------------------------------------
    st.subheader("4. Travailleur et employeur")

    col1, col2 = st.columns(2)
    with col1:
        employee_name = st.text_input(
            "Nom et prénom",
            key="c4_acs_employee_name",
        )
        niss = st.text_input(
            "NISS",
            key="c4_acs_niss",
            help="Le matricule figurant sur la fiche de paie n'est pas utilisé comme NISS.",
        )
        employee_address = st.text_area(
            "Adresse du membre du personnel (contrôle)",
            key="c4_acs_employee_address",
            height=85,
            disabled=True,
        )

    with col2:
        fase_database, fase_database_error = _load_fase_database()
        fase_input = st.text_input(
            "N° FASE de l'établissement",
            placeholder="Ex. 765",
            key="c4_acs_fase",
        )
        fase = _normalize_fase(fase_input)
        fase_record = fase_database.get(fase) if fase else None

        establishment_name = ""
        establishment_address = ""
        establishment_unit_bce = ""

        if fase_database_error:
            st.error(fase_database_error)
        elif not fase:
            st.caption("Introduisez le FASE pour identifier l'établissement officiel.")
        elif not fase_record:
            st.error(f"Le numéro FASE {fase} n'a pas été trouvé dans le répertoire FWB.")
        else:
            establishment_name = str(fase_record.get("nom", "")).strip()
            establishment_address = _fase_establishment_address(fase_record)
            establishment_unit_bce = str(fase_record.get("bce_etablissement", "")).strip()
            st.markdown(f"**Établissement :** {establishment_name}")
            st.markdown(f"**Adresse :** {establishment_address}")
            if establishment_unit_bce:
                st.caption(
                    f"N° BCE de l'unité d'établissement : {establishment_unit_bce} — "
                    "informatif, ce n'est pas automatiquement le n° d'entreprise de l'employeur/PO."
                )

    st.warning(
        "Le C4 classique doit identifier l'employeur. Le FASE permet d'identifier l'école, "
        "mais pas de manière fiable le pouvoir organisateur ni son numéro d'entreprise. "
        "Ces données doivent donc être confirmées ci-dessous."
    )

    c1, c2 = st.columns(2)
    with c1:
        employer_name = st.text_input(
            "Nom / raison sociale du pouvoir organisateur",
            key="c4_acs_employer_name",
        )
        employer_address = st.text_area(
            "Adresse du pouvoir organisateur",
            key="c4_acs_employer_address",
            height=85,
        )
        enterprise_number = st.text_input(
            "Numéro d'entreprise (BCE) du pouvoir organisateur",
            key="c4_acs_bce",
        )
    with c2:
        employer_category = st.text_input(
            "Catégorie employeur",
            key="c4_acs_employer_category",
        )
        joint_committee = st.text_input(
            "Commission paritaire",
            key="c4_acs_joint_committee",
        )
        onss_number = st.text_input(
            "Numéro ONSS de l'employeur",
            key="c4_acs_onss_number",
        )

    # --------------------------------------------------------
    # 5. OCCUPATION
    # --------------------------------------------------------
    st.subheader("5. Données concernant l'occupation")

    c1, c2, c3 = st.columns(3)
    with c1:
        occupation_start_txt = _masked_date_input(
            "Date de début de l'occupation",
            key="c4_acs_occ_start",
        )
        service_start_txt = _masked_date_input(
            "Date d'entrée en service",
            key="c4_acs_service_start",
        )
    with c2:
        occupation_end_txt = _masked_date_input(
            "Date de fin de l'occupation",
            key="c4_acs_occ_end",
        )
        worker_code = st.text_input(
            "Code travailleur (3 chiffres)",
            max_chars=3,
            key="c4_acs_worker_code",
        )
    with c3:
        home_worker = st.checkbox(
            "Travailleur à domicile",
            value=False,
            key="c4_acs_home_worker",
            help="Le statut D ne doit être indiqué sur le C4 que pour un travailleur à domicile.",
        )
        status = "D" if home_worker else ""
        st.text_input(
            "Statut à reporter",
            value=status,
            disabled=True,
            key="c4_acs_status_display",
        )
        st.text_input(
            "Mesure de promotion de l'emploi",
            value=employment_measure,
            disabled=True,
            key="c4_acs_employment_measure_display",
        )

    occupation_start, e1 = _parse_user_date(occupation_start_txt)
    service_start, e2 = _parse_user_date(service_start_txt)
    occupation_end, e3 = _parse_user_date(occupation_end_txt)

    # --------------------------------------------------------
    # REGIME HORAIRE
    # --------------------------------------------------------
    # Pour les situations ACS / APE / PART-APE / PTP, l'utilisateur ne doit
    # pas encoder Q et S séparément. Il choisit le régime, puis Q/S sont
    # déterminés automatiquement pour le C4 classique.
    detected_q = float(source_entry.q or 0.0)
    detected_s = float(source_entry.s or 0.0)

    default_regime_index = 2  # Temps plein par défaut
    if abs(detected_q - 18.0) < 0.01 and abs(detected_s - 36.0) < 0.01:
        default_regime_index = 0
    elif abs(detected_q - 32.0) < 0.01 and abs(detected_s - 36.0) < 0.01:
        default_regime_index = 1
    elif abs(detected_q - 36.0) < 0.01 and abs(detected_s - 36.0) < 0.01:
        default_regime_index = 2

    # La fonction Puériculteur(trice) PTP impose 32/36e.
    if fonction_acs == "Puériculteur(trice) PTP":
        default_regime_index = 1

    regime_options = list(REGIMES_HORAIRES_ACS_APE.keys())
    if "c4_acs_regime_horaire" not in st.session_state:
        st.session_state["c4_acs_regime_horaire"] = regime_options[default_regime_index]

    regime_horaire = st.selectbox(
        "Charge horaire",
        options=regime_options,
        key="c4_acs_regime_horaire",
        help=(
            "Choisissez le régime de travail. Le site convertit automatiquement ce choix "
            "en Q/S pour remplir le C4 classique."
        ),
    )

    q, s = REGIMES_HORAIRES_ACS_APE[regime_horaire]

    st.caption(
        f"Valeur reportée automatiquement sur le C4 : Q = {q:.2f} / S = {s:.2f}".replace(".", ",")
    )

    onss_case = st.selectbox(
        "Cotisations ONSS - secteur chômage",
        [
            "Prélevées",
            "Non prélevées et non versées",
            "Non retenues mais seront versées",
            "Statutaire art. 9",
        ],
        index=0,
        key="c4_acs_onss_case",
    )

    # --------------------------------------------------------
    # 6. REMUNERATION - CALCUL AUTOMATIQUE
    # --------------------------------------------------------
    st.subheader("6. Rémunération")

    monthly_fr = reconstruct_monthly_fr(source_entry)
    calculated_theoretical = None
    if (
        source_entry.annual_base_salary is not None
        and source_entry.pdf_index is not None
        and q > 0
        and s > 0
    ):
        calculated_theoretical = calculate_monthly_indexed_salary(
            annual_base_salary=source_entry.annual_base_salary,
            q=q,
            s=s,
            index_value=source_entry.pdf_index,
            monthly_fr=monthly_fr,
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("TAB détecté", _format_money(source_entry.annual_base_salary))
    with c2:
        st.metric(
            "Index détecté",
            f"{source_entry.pdf_index:.4f}".replace(".", ",") if source_entry.pdf_index else "—",
        )
    with c3:
        st.metric("Allocation F/R mensuelle", _format_money(monthly_fr))

    if calculated_theoretical is not None:
        st.success(
            "Salaire brut moyen théorique calculé automatiquement : "
            f"{_format_money(calculated_theoretical)} / mois"
        )
        st.caption("Calcul : TAB × Q/S × index ÷ 12 + allocation foyer/résidence éventuelle.")
    else:
        st.warning(
            "Le TAB, l'index ou la fraction Q/S n'a pas pu être déterminé complètement. "
            "Encodez le salaire brut moyen théorique manuellement."
        )

    use_auto_salary = st.checkbox(
        "Utiliser le salaire calculé automatiquement",
        value=calculated_theoretical is not None,
        key="c4_acs_use_auto_salary",
        disabled=calculated_theoretical is None,
    )

    if use_auto_salary and calculated_theoretical is not None:
        theoretical_salary = float(calculated_theoretical)
        st.number_input(
            "Salaire brut moyen théorique à reporter",
            min_value=0.0,
            value=theoretical_salary,
            step=0.01,
            format="%.2f",
            disabled=True,
            key="c4_acs_theoretical_salary_auto_display",
        )
    else:
        theoretical_salary = st.number_input(
            "Salaire brut moyen théorique à reporter",
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            key="c4_acs_theoretical_salary_manual",
        )

    salary_frequency = "par mois"
    st.text_input(
        "Périodicité",
        value="par mois",
        disabled=True,
        key="c4_acs_salary_frequency_display",
    )

    exact_gross = None
    quarter_label = ""
    quarter_rows = []

    if occupation_end:
        _, quarter_start, quarter_end, quarter_label = quarter_info(occupation_end)
        st.markdown(f"**Trimestre de la fin d'occupation : {quarter_label}**")

        dmfa_accepted = st.radio(
            "La déclaration DmfA de ce trimestre est-elle déjà déclarée et acceptée par l'ONSS ?",
            ["Oui", "Non"],
            index=1,
            horizontal=True,
            key="c4_acs_dmfa_accepted",
        )

        if dmfa_accepted == "Non":
            candidates = [
                e for e in entries
                if _entry_in_quarter(e, quarter_start, quarter_end)
                and (
                    source_entry.q is None
                    or e.q is None
                    or abs((e.q or 0) - (source_entry.q or 0)) < 0.001
                )
                and (
                    source_entry.s is None
                    or e.s is None
                    or abs((e.s or 0) - (source_entry.s or 0)) < 0.001
                )
            ]
            if not candidates:
                candidates = [e for e in entries if _entry_in_quarter(e, quarter_start, quarter_end)]

            candidate_labels = [_entry_label(e) for e in candidates]
            selected_labels = st.multiselect(
                "Fiches de paie à additionner pour le salaire brut exact du trimestre",
                candidate_labels,
                default=candidate_labels,
                key="c4_acs_exact_entries",
            )

            selected_entries = [
                candidates[candidate_labels.index(label)]
                for label in selected_labels
            ]
            suggested_exact = round(
                sum(
                    (entry.gross or 0.0) + (entry.fr_amount if entry.fr_found else 0.0)
                    for entry in selected_entries
                ),
                2,
            )

            exact_gross = st.number_input(
                "Salaire brut exact du trimestre",
                min_value=0.0,
                value=float(suggested_exact),
                step=0.01,
                format="%.2f",
                key="c4_acs_exact_gross",
                help=(
                    "Proposition calculée à partir des bruts réellement payés sur les fiches sélectionnées. "
                    "Vérifiez le montant avec la DmfA si nécessaire."
                ),
            )

            qrow_start = max(quarter_start, occupation_start) if occupation_start else quarter_start
            qrow_end = min(quarter_end, occupation_end)
            has_interruption = st.checkbox(
                "Il y a eu une interruption à déclarer pendant ce trimestre",
                value=False,
                key="c4_acs_qrow_interruption",
            )
            q_changed = st.checkbox(
                "La durée de travail diffère de Q pendant une partie du trimestre",
                value=False,
                key="c4_acs_qrow_qdiff",
            )
            quarter_rows = [
                {
                    "start": qrow_start,
                    "end": qrow_end,
                    "interruption": has_interruption,
                    "q_diff": q_changed,
                }
            ]
        else:
            st.caption(
                "Le salaire brut exact et la partie B ne sont pas complétés pour un trimestre déjà accepté, "
                "sauf situation particulière."
            )
    else:
        st.caption("Complétez la date de fin pour déterminer le trimestre ONSS.")

    # --------------------------------------------------------
    # 7. VACANCES / JOURS FERIES / REPOS
    # --------------------------------------------------------
    st.subheader("7. Vacances et jours encore rémunérés")

    default_vacation_type = "Temps plein" if q > 0 and s > 0 and abs(q - s) < 0.001 else "Temps partiel"
    vacation_type = st.radio(
        "Vacances légales",
        ["Temps partiel", "Temps plein"],
        index=1 if default_vacation_type == "Temps plein" else 0,
        horizontal=True,
        key="c4_acs_vacation_type",
    )
    vacation_amount = st.number_input(
        "Nombre d'heures (temps partiel) ou de jours (temps plein) de vacances rémunérées depuis le 1er janvier",
        min_value=0.0,
        value=0.0,
        step=0.5,
        key="c4_acs_vacation_amount",
    )

    network = str((fase_record or {}).get("reseau", "")).lower()
    if "libre" in network:
        public_default = "Secteur privé"
    elif "communal" in network or "provinc" in network or "fédération" in network or "federation" in network:
        public_default = "Secteur public"
    else:
        public_default = "Non applicable"

    regime_options = ["Non applicable", "Secteur public", "Secteur privé"]
    public_regime = st.selectbox(
        "Régime de vacances - pouvoirs publics",
        regime_options,
        index=regime_options.index(public_default),
        key="c4_acs_public_regime",
    )

    holidays_text = st.text_input(
        "Jours fériés payés après la fin du contrat (séparés par des virgules, JJ/MM/AAAA)",
        key="c4_acs_holidays",
    )
    paid_holidays_after_end: list[date] = []
    holiday_errors = []
    for chunk in [x.strip() for x in holidays_text.split(",") if x.strip()]:
        d, err = _parse_user_date(chunk)
        if d:
            paid_holidays_after_end.append(d)
        if err:
            holiday_errors.append(chunk)

    comp_rest_days = st.number_input(
        "Jours encore rémunérés après la fin pour repos compensatoire / heures supplémentaires",
        min_value=0.0,
        value=0.0,
        step=0.5,
        key="c4_acs_comp_rest",
    )

    # --------------------------------------------------------
    # 8. FIN DU CONTRAT
    # --------------------------------------------------------
    st.subheader("8. Fin de l'occupation")

    end_reason = st.selectbox(
        "Comment le contrat a-t-il pris fin ?",
        [
            "Durée déterminée arrivée à terme",
            "Travail déterminé arrivé à terme",
            "Préavis par l'employeur",
            "Rupture par l'employeur",
            "Démission / abandon volontaire",
            "Commun accord",
            "Force majeure médicale",
            "Force majeure autre",
        ],
        key="c4_acs_end_reason",
    )

    precise_reason_default = ""
    if end_reason == "Préavis par l'employeur":
        precise_reason_default = "Fin de l'occupation à l'initiative de l'employeur avec préavis"
    elif end_reason == "Rupture par l'employeur":
        precise_reason_default = "Fin de l'occupation à l'initiative de l'employeur"
    elif end_reason == "Commun accord":
        precise_reason_default = "Fin de l'occupation de commun accord"
    elif end_reason.startswith("Force majeure"):
        precise_reason_default = "Fin de l'occupation pour force majeure"

    precise_reason = st.text_area(
        "Motif précis du chômage",
        value=precise_reason_default,
        key="c4_acs_precise_reason",
        help="Le formulaire exige ce motif notamment pour certaines fins à l'initiative de l'employeur, de commun accord ou pour force majeure.",
    )

    notice_method = "Lettre recommandée"
    notice_sent = None
    if end_reason == "Préavis par l'employeur":
        notice_method = st.radio(
            "Notification du préavis",
            ["Lettre recommandée", "Exploit d'huissier"],
            horizontal=True,
            key="c4_acs_notice_method",
        )
        notice_sent_txt = _masked_date_input(
            "Date d'envoi / notification",
            key="c4_acs_notice_sent",
        )
        notice_sent, _ = _parse_user_date(notice_sent_txt)

    st.subheader("9. Indemnité liée à la fin")
    indemnity_type = st.selectbox(
        "Une indemnité a-t-elle été payée ?",
        ["Aucune", "Salaire pendant le délai de préavis", "Indemnité de congé / rupture", "Autre indemnité"],
        key="c4_acs_indemnity_type",
    )

    indemnity_start = indemnity_end = None
    other_indemnity_name = ""
    other_indemnity_amount = 0.0
    if indemnity_type != "Aucune":
        c1, c2 = st.columns(2)
        with c1:
            ind_start_txt = _masked_date_input(
                "Période couverte - du",
                key="c4_acs_ind_start",
            )
        with c2:
            ind_end_txt = _masked_date_input(
                "Période couverte - au",
                key="c4_acs_ind_end",
            )
        indemnity_start, _ = _parse_user_date(ind_start_txt)
        indemnity_end, _ = _parse_user_date(ind_end_txt)

        if indemnity_type == "Autre indemnité":
            other_indemnity_name = st.text_input(
                "Nature de l'autre indemnité",
                key="c4_acs_other_ind_name",
            )
            other_indemnity_amount = st.number_input(
                "Montant de l'autre indemnité",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key="c4_acs_other_ind_amount",
            )

    remarks = st.text_area("Remarques", key="c4_acs_remarks")

    # --------------------------------------------------------
    # 10. SIGNATURE / GENERATION
    # --------------------------------------------------------
    st.subheader("10. C4 classique prêt à imprimer")

    pact_generations = st.selectbox(
        "Pacte des générations",
        [
            "Non concerné / ne pas compléter",
            "Licenciement - cellule emploi créée",
            "Licenciement - pas de cellule emploi",
            "Pas un licenciement",
        ],
        key="c4_acs_pact",
    )
    complementary_indemnity = st.radio(
        "Indemnité complémentaire sans cotisations salariales ONSS ?",
        ["Non", "Oui"],
        horizontal=True,
        key="c4_acs_compl_ind",
    )
    responsible_name = st.text_input(
        "Nom du responsable / délégué qui signera le C4",
        key="c4_acs_responsible",
    )
    declaration_date = st.date_input(
        "Date de la déclaration",
        value=date.today(),
        format="DD/MM/YYYY",
        key="c4_acs_decl_date",
    )

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------
    errors = []
    if e1:
        errors.append("Date de début de l'occupation manquante ou invalide.")
    if e2:
        errors.append("Date d'entrée en service manquante ou invalide.")
    if e3:
        errors.append("Date de fin de l'occupation manquante ou invalide.")
    if not fonction_acs:
        errors.append("Fonction manquante.")
    if fonction_acs == "Puériculteur(trice) PTP":
        if programme != "PTP":
            errors.append("La fonction Puériculteur(trice) PTP doit être associée au programme PTP.")
        if regime_horaire != "4/5e temps — 32/36":
            errors.append("La fonction Puériculteur(trice) PTP impose le régime 4/5e temps (32/36).")

    if not employee_name.strip():
        errors.append("Nom du travailleur manquant.")
    if len(re.sub(r"\D", "", niss)) != 11:
        errors.append("Le NISS doit contenir 11 chiffres.")
    if not fase:
        errors.append("Numéro FASE de l'établissement manquant.")
    elif not fase_record:
        errors.append(f"Numéro FASE {fase} introuvable dans le répertoire FWB.")
    if not employer_name.strip():
        errors.append("Nom / raison sociale du pouvoir organisateur manquant.")
    if not employer_address.strip():
        errors.append("Adresse du pouvoir organisateur manquante.")
    if not enterprise_number.strip() and not onss_number.strip():
        errors.append("Complétez au moins le numéro d'entreprise BCE ou le numéro ONSS de l'employeur.")
    if not re.fullmatch(r"\d{3}", worker_code.strip()):
        errors.append("Le code travailleur doit contenir exactement 3 chiffres.")
    if q <= 0 or s <= 0:
        errors.append("Q et S doivent être supérieurs à 0.")
    if theoretical_salary <= 0:
        errors.append("Salaire brut moyen théorique manquant.")
    if holiday_errors:
        errors.append("Une ou plusieurs dates de jours fériés sont invalides.")
    if not responsible_name.strip():
        errors.append("Nom du responsable / délégué manquant.")
    if occupation_end and st.session_state.get("c4_acs_dmfa_accepted") == "Non" and (exact_gross is None or exact_gross <= 0):
        errors.append("Salaire brut exact du trimestre manquant pour une DmfA non encore acceptée.")

    for error in errors:
        st.warning(error)

    template_pdf, template_error = _template_bytes(TEMPLATE_C4_CLASSIQUE)
    if template_error:
        st.error(template_error)
        return

    if not _template_contains_version(template_pdf, EXPECTED_C4_CLASSIQUE_VERSION):
        st.error(
            "Le PDF placé dans assets/c4_classique_officiel.pdf ne correspond pas à la version "
            f"attendue ({EXPECTED_C4_CLASSIQUE_VERSION}). Les coordonnées d'impression pourraient être incorrectes."
        )
        return

    if errors:
        st.info("Corrigez les éléments ci-dessus avant de générer le C4 prêt à imprimer.")
        return

    data = {
        "fonction": fonction_acs,
        "employee_name": employee_name,
        "niss": niss,
        "employer_name": employer_name,
        "employer_address": employer_address,
        "employer_category": employer_category,
        "enterprise_number": enterprise_number,
        "joint_committee": joint_committee,
        "onss_number": onss_number,
        "occupation_start": occupation_start,
        "service_start": service_start,
        "occupation_end": occupation_end,
        "worker_code": worker_code,
        "status": status,
        "employment_measure": employment_measure,
        "onss_case": onss_case,
        "q": q,
        "s": s,
        "theoretical_salary": theoretical_salary,
        "salary_frequency": salary_frequency,
        "exact_gross": exact_gross if exact_gross and exact_gross > 0 else None,
        "quarter_label": quarter_label,
        "vacation_type": vacation_type,
        "vacation_amount": vacation_amount,
        "public_regime": public_regime,
        "paid_holidays_after_end": paid_holidays_after_end,
        "comp_rest_days": comp_rest_days,
        "quarter_rows": quarter_rows,
        "end_reason": end_reason,
        "precise_reason": precise_reason,
        "notice_method": notice_method,
        "notice_sent": notice_sent,
        "indemnity_type": indemnity_type,
        "indemnity_start": indemnity_start,
        "indemnity_end": indemnity_end,
        "other_indemnity_name": other_indemnity_name,
        "other_indemnity_amount": other_indemnity_amount,
        "remarks": remarks,
        "pact_generations": pact_generations,
        "complementary_indemnity": complementary_indemnity,
        "responsible_name": responsible_name,
        "declaration_date": declaration_date,
    }

    try:
        pdf_bytes = generate_c4_classique_pdf(data, template_pdf)
    except Exception as exc:
        st.error(f"La génération du PDF a échoué : {exc}")
        return

    st.success(
        f"Le C4 classique {programme} est prêt à imprimer. "
        "La rubrique destinée au travailleur reste inchangée."
    )
    st.download_button(
        f"Télécharger le C4 {programme} prêt à imprimer",
        data=pdf_bytes,
        file_name=f"C4_{programme.replace('-', '_')}_complete.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# INTERFACE STREAMLIT
# ============================================================

def render_c4_assistant():
    st.title("📄 C4 Assistant")

    st.write(
        "Importez une ou plusieurs fiches de paie. L'outil extrait les données utiles, "
        "vous laisse les vérifier, puis prépare soit le C4-Enseignement, soit le C4 classique "
        "selon la situation du membre du personnel."
    )

    st.info(
        "Les dates d'occupation ne sont jamais déduites de la période de paie. "
        "Elles doivent être introduites séparément."
    )

    # --------------------------------------------------------
    # 1. AIGUILLAGE C4-ENSEIGNEMENT / C4 CLASSIQUE
    # --------------------------------------------------------

    st.subheader("1. Type de C4")

    personnel_type = st.selectbox(
        "Quelle est la situation du membre du personnel ?",
        [
            "Sélectionnez une situation",
            "Personnel enseignant / direction / auxiliaire d'éducation / paramédical payé par la FWB",
            "ACS / APE / PART-APE / PTP",
            "Personnel engagé sur fonds propres ou lié par un contrat de travail",
            "Personnel ouvrier ou administratif contractuel",
        ],
        key="c4_personnel_type",
    )

    if personnel_type == "Sélectionnez une situation":
        return

    if personnel_type == "ACS / APE / PART-APE / PTP":
        st.info(
            "Cette situation relève du C4 classique. Les mêmes fiches de paie FWB peuvent être utilisées "
            "pour préremplir automatiquement les données de rémunération et de fraction d'occupation."
        )
        render_c4_classique_acs_ape()
        return

    if personnel_type != (
        "Personnel enseignant / direction / auxiliaire d'éducation / paramédical payé par la FWB"
    ):
        st.info("Cette situation relève du C4 classique.")
        render_c4_classique_manuel()
        return

    # --------------------------------------------------------
    # 2. IMPORT DES FICHES DE PAIE
    # --------------------------------------------------------

    st.subheader("2. Fiches de paie")

    uploaded_files = st.file_uploader(
        "Importer une ou plusieurs fiches de paie PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="c4_payroll_files",
    )

    st.caption(
        "Le module lit les PDF pour effectuer les calculs mais ne les enregistre pas dans le dépôt GitHub."
    )

    entries: list[PayrollEntry] = []
    extraction_errors: list[str] = []

    if uploaded_files:
        entries, extraction_errors = extract_payroll_entries(uploaded_files)

    for error in extraction_errors:
        st.warning(error)

    if entries:
        with st.expander("Voir les données détectées sur les fiches de paie"):
            for i, entry in enumerate(entries, start=1):
                st.markdown(f"**Fiche détectée {i} — {_entry_label(entry)}**")
                st.write(
                    {
                        "Nom": entry.employee_name,
                        "Adresse": entry.employee_address,
                        "Matricule fiche": entry.employee_matricule,
                        "Établissement détecté sur la fiche (non utilisé)": entry.establishment_name,
                        "Adresse détectée sur la fiche (non utilisée)": entry.establishment_address,
                        "Charge": (
                            f"{entry.q:g}/{entry.s:g}"
                            if entry.q is not None and entry.s is not None
                            else ""
                        ),
                        "Mois de liquidation": entry.liquidation_month,
                        "Période de paie": (
                            f"{_format_date(entry.period_start)} au {_format_date(entry.period_end)}"
                            if entry.period_start and entry.period_end
                            else ""
                        ),
                        "Statut": entry.status,
                        "Échelle": entry.salary_scale,
                        "Ancienneté": entry.seniority,
                        "TAB": _format_money(entry.annual_base_salary),
                        "Index fiche": (
                            f"{entry.pdf_index:.4f}".replace(".", ",")
                            if entry.pdf_index is not None
                            else "non détecté"
                        ),
                        "Brut": _format_money(entry.gross),
                        "F/R repérée": _format_money(entry.fr_amount) if entry.fr_found else "non repérée",
                        "Congé / interruption repéré": entry.absence_or_leave,
                        "Traitement différé repéré": "oui" if entry.deferred_pay_detected else "non",
                    }
                )
                st.divider()
    else:
        st.info(
            "Importez au moins une fiche de paie PDF. L'index est récupéré directement sur la fiche et n'est plus saisi manuellement."
        )
        return

    # --------------------------------------------------------
    # 3. IDENTITE ET ETABLISSEMENT
    # --------------------------------------------------------

    st.subheader("3. Identité et établissement")

    base_entry = entries[0]

    col1, col2 = st.columns(2)

    with col1:
        employee_name = st.text_input(
            "Nom et prénom",
            value=base_entry.employee_name,
            key="c4_employee_name",
        )

        niss = st.text_input(
            "NISS",
            value="",
            key="c4_niss",
            help="Le matricule figurant sur la fiche de paie n'est pas utilisé comme NISS.",
        )

        employee_address = st.text_area(
            "Adresse du MDP",
            value=base_entry.employee_address,
            key="c4_employee_address",
            height=90,
        )

    with col2:
        fase_database, fase_database_error = _load_fase_database()

        fase_input = st.text_input(
            "N° FASE de l'établissement",
            value="",
            placeholder="Ex. 765",
            key="c4_fase_establishment",
            help=(
                "Le nom officiel et l'adresse de l'établissement sont récupérés "
                "dans le fichier signalétique des établissements de la Fédération Wallonie-Bruxelles."
            ),
        )

        fase = _normalize_fase(fase_input)
        fase_record = fase_database.get(fase) if fase else None

        establishment_name = ""
        establishment_address = ""

        if fase_database_error:
            st.error(fase_database_error)
        elif not fase:
            st.caption(
                "Introduisez le numéro FASE : le nom officiel de l'établissement "
                "et son adresse seront complétés automatiquement."
            )
        elif not fase_record:
            st.error(
                f"Le numéro FASE {fase} n'a pas été trouvé dans le fichier signalétique FWB."
            )
        else:
            establishment_name = str(fase_record.get("nom", "")).strip()
            establishment_address = _fase_establishment_address(fase_record)

            st.markdown(f"**Nom officiel :** {establishment_name}")
            st.markdown(f"**Adresse officielle :** {establishment_address}")
            st.caption(
                "Source : fichier signalétique des établissements d'enseignement "
                "de la Fédération Wallonie-Bruxelles."
            )

        st.text_input(
            "Numéro BCE à reporter",
            value=BCE_FWB_ENSEIGNEMENT,
            disabled=True,
        )

        st.caption("Numéro ONSS : ne pas compléter sur le C4-Enseignement.")

    # Index détecté directement sur les fiches de paie.
    detected_indexes = sorted(
        {round(e.pdf_index, 4) for e in entries if e.pdf_index is not None}
    )

    if entries and detected_indexes:
        st.info(
            "Index détecté automatiquement sur les fiches de paie : "
            + ", ".join(f"{x:.4f}".replace(".", ",") for x in detected_indexes)
        )
    elif entries:
        st.warning(
            "Aucun index n'a pu être extrait des fiches de paie. "
            "Le salaire mensuel brut indexé ne pourra pas être calculé tant qu'une fiche contenant l'index n'est pas sélectionnée."
        )

    # --------------------------------------------------------
    # 4. OCCUPATIONS TERMINEES
    # --------------------------------------------------------

    st.subheader("4. Occupation(s) terminée(s)")

    st.caption(
        "Le formulaire C4-Enseignement prévoit jusqu'à trois cadres d'occupation. "
        "Ne renseignez pas une mission qui est toujours en cours."
    )

    occupation_count = int(
        st.number_input(
            "Nombre d'occupations terminées à reprendre",
            min_value=1,
            max_value=3,
            value=1,
            step=1,
            key="c4_occupation_count",
        )
    )

    entry_options = [_entry_label(e) for e in entries]
    entry_map = {_entry_label(e): e for e in entries}

    occupation_results = []
    global_errors: list[str] = []

    for occ_index in range(1, occupation_count + 1):
        prefix = f"c4_occ_{occ_index}"

        st.markdown(f"### Occupation {occ_index}")

        source_label = st.selectbox(
            "Fiche de paie utilisée comme base",
            entry_options,
            index=min(occ_index - 1, len(entry_options) - 1),
            key=f"{prefix}_source",
            on_change=_clear_occ_fields,
            args=(prefix,),
        )

        source_entry = entry_map[source_label]
        index_value = source_entry.pdf_index

        if index_value is not None:
            st.info(
                "Index repris automatiquement sur cette fiche : "
                f"**{index_value:.4f}**".replace(".", ",")
            )
        else:
            st.warning(
                "Aucun index n'a été détecté sur la fiche sélectionnée. "
                "Choisissez une autre fiche contenant l'index."
            )

        default_status_index = _status_default_index(source_entry.status)

        col_a, col_b = st.columns(2)

        with col_a:
            fonction_code = st.selectbox(
                "Fonction",
                options=[""] + [code for code, _ in FONCTIONS_ENSEIGNEMENT],
                format_func=_format_fonction_option,
                index=0,
                key=f"{prefix}_fonction",
                help=(
                    "Le menu affiche le code ProEco et l'intitulé complet. "
                    "Seul l'intitulé complet sera imprimé sur le C4."
                ),
            )
            fonction = FONCTIONS_PAR_CODE.get(fonction_code, "")

            status_index = st.selectbox(
                "Statut à reporter",
                options=list(range(4)),
                format_func=_status_value,
                index=default_status_index,
                key=f"{prefix}_statut",
            )
            statut = _status_value(status_index)

            start_text = _masked_date_input(
                "Date d'entrée dans cette occupation",
                key=f"{prefix}_start",
            )

            end_text = _masked_date_input(
                "Date de fin effective de cette occupation",
                key=f"{prefix}_end",
            )

        with col_b:
            q = st.number_input(
                "Q — prestations hebdomadaires",
                min_value=0.0,
                value=float(source_entry.q or 0.0),
                step=0.01,
                format="%.2f",
                key=f"{prefix}_q",
            )

            s = st.number_input(
                "S — charge complète",
                min_value=0.0,
                value=float(source_entry.s or 0.0),
                step=0.01,
                format="%.2f",
                key=f"{prefix}_s",
            )

            tab = st.number_input(
                "Traitement annuel brut (TAB) à 100 %",
                min_value=0.0,
                value=float(source_entry.annual_base_salary or 0.0),
                step=0.01,
                format="%.2f",
                key=f"{prefix}_tab",
            )

            suggested_fr = reconstruct_monthly_fr(source_entry)
            monthly_fr = st.number_input(
                "Allocation F/R mensuelle à inclure",
                min_value=0.0,
                value=float(suggested_fr),
                step=0.01,
                format="%.2f",
                key=f"{prefix}_fr_month",
                help=(
                    "Si la fiche ne couvre qu'une partie d'un mois et qu'une allocation F/R a été repérée, "
                    "le module reconstitue le montant d'un mois complet par règle de trois."
                ),
            )

            if not source_entry.fr_found:
                st.caption(
                    "Aucune allocation F/R n'a été repérée automatiquement sur cette fiche. "
                    "Vérifiez le montant avant de laisser 0,00 €."
                )

        start_date, start_error = _parse_user_date(start_text)
        end_date, end_error = _parse_user_date(end_text)

        if start_error:
            global_errors.append(f"Occupation {occ_index} — date d'entrée : {start_error}")
        if end_error:
            global_errors.append(f"Occupation {occ_index} — date de fin : {end_error}")
        if start_date and end_date and end_date < start_date:
            global_errors.append(
                f"Occupation {occ_index} — la date de fin est antérieure à la date d'entrée."
            )

        if not fonction:
            global_errors.append(
                f"Occupation {occ_index} — sélectionnez une fonction."
            )

        salary_monthly = None
        if index_value is None:
            global_errors.append(
                f"Occupation {occ_index} — index absent de la fiche de paie sélectionnée."
            )
        else:
            salary_monthly = calculate_monthly_indexed_salary(
                annual_base_salary=tab,
                q=q,
                s=s,
                index_value=index_value,
                monthly_fr=monthly_fr,
            )

        if salary_monthly is None:
            global_errors.append(
                f"Occupation {occ_index} — impossible de calculer le salaire mensuel brut indexé."
            )
        else:
            st.success(
                f"Salaire mensuel brut indexé à reporter : **{_format_money(salary_monthly)}**"
            )
            st.caption(
                f"Calcul : ({_format_money(tab)} × {q:g}/{s:g} × "
                f"{index_value:.4f}) / 12 + {_format_money(monthly_fr)} F/R"
            )

        # ----------------------------------------------------
        # MODE DE PAIEMENT
        # ----------------------------------------------------

        period_additional = False
        if "Temporaire" in statut:
            period_additional = st.checkbox(
                "Il s'agit de périodes additionnelles",
                value=False,
                key=f"{prefix}_period_additional",
                help="Les périodes additionnelles sont en mode 12.",
            )

        auto_mode = "20" if ("Temporaire" in statut and not period_additional) else "12"

        mode_choice = st.selectbox(
            "Mode de paiement",
            [f"Automatique — {auto_mode}", "12", "20"],
            key=f"{prefix}_mode_override",
        )
        mode_payment = auto_mode if mode_choice.startswith("Automatique") else mode_choice

        # ----------------------------------------------------
        # COTISATIONS ONSS
        # ----------------------------------------------------

        onss_case = st.selectbox(
            "Cotisations ONSS — secteur chômage",
            [
                "Paiement FWB normal",
                "Incapacité de travail à charge de la mutuelle pendant le trimestre concerné",
                "Interruption de carrière totale pendant le trimestre concerné",
            ],
            key=f"{prefix}_onss_case",
        )

        if onss_case == "Paiement FWB normal":
            onss_text = (
                f"ont été prélevées du {_format_date(start_date)} au {_format_date(end_date)}"
                if start_date and end_date
                else "ont été prélevées — période à compléter"
            )
        else:
            onss_text = "n'ont pas été prélevées (enseignant statutaire)"

        # ----------------------------------------------------
        # SALAIRE BRUT EXACT DU TRIMESTRE
        # ----------------------------------------------------

        exact_total: Optional[float] = None
        quarter_label = ""
        dmfa_state = ""

        if end_date:
            _, q_start, q_end, quarter_label = quarter_info(end_date)

            dmfa_state = st.radio(
                f"Le trimestre ONSS {quarter_label} est-il déjà déclaré et accepté en DmfA ?",
                [
                    "Non / le salaire brut exact doit être complété",
                    "Oui / ne pas compléter le salaire brut exact",
                    "Je ne sais pas",
                ],
                key=f"{prefix}_dmfa_state",
            )

            if dmfa_state == "Non / le salaire brut exact doit être complété":
                candidates = [
                    e for e in entries if _entry_in_quarter(e, q_start, q_end)
                ]

                candidate_labels = [_entry_label(e) for e in candidates]
                candidate_map = {_entry_label(e): e for e in candidates}

                default_candidates = []
                for candidate in candidates:
                    q_match = (
                        candidate.q is not None
                        and candidate.s is not None
                        and abs(candidate.q - q) < 0.001
                        and abs(candidate.s - s) < 0.001
                    )
                    status_match = _same_status(candidate.status, statut)
                    if q_match and status_match:
                        default_candidates.append(_entry_label(candidate))

                selected_exact_labels = st.multiselect(
                    f"Fiches à additionner pour le salaire brut exact — trimestre {quarter_label}",
                    options=candidate_labels,
                    default=default_candidates,
                    key=f"{prefix}_exact_entries",
                    help=(
                        "Sélectionnez uniquement les lignes de paie qui correspondent à cette occupation. "
                        "Le calcul additionne Brut + F/R de chaque ligne sélectionnée."
                    ),
                )

                exact_from_slips = 0.0
                selected_exact_entries = []
                for label in selected_exact_labels:
                    e = candidate_map[label]
                    selected_exact_entries.append(e)
                    exact_from_slips += (e.gross or 0.0) + (e.fr_amount if e.fr_found else 0.0)

                if end_date.month == 7 and any(e.deferred_pay_detected for e in selected_exact_entries):
                    st.warning(
                        "Une rémunération ou un traitement différé a été repéré dans une fiche de juillet sélectionnée. "
                        "Il ne doit pas être inclus dans le salaire brut exact de juillet. Vérifiez la sélection ou introduisez le montant correct manuellement."
                    )
                    global_errors.append(
                        f"Occupation {occ_index} — traitement différé repéré dans le calcul du salaire brut exact de juillet."
                    )

                manual_extra = st.number_input(
                    "Montant complémentaire du trimestre non présent dans les PDF",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"{prefix}_exact_manual",
                    help=(
                        "Utilisez ce champ si une rémunération du trimestre n'est pas disponible dans les PDF. "
                        "Ne l'utilisez pas pour estimer un autre mois par règle de trois."
                    ),
                )

                july_estimation = 0.0

                if end_date.month == 7:
                    has_july_entry = any(
                        e.period_start
                        and e.period_start.year == end_date.year
                        and e.period_start.month == 7
                        for e in candidates
                    )

                    if not has_july_entry:
                        use_july_estimate = st.checkbox(
                            "Estimer le salaire brut exact de juillet à partir d'une fiche de juin",
                            value=False,
                            key=f"{prefix}_july_estimate",
                        )

                        if use_july_estimate:
                            june_entries = [
                                e
                                for e in entries
                                if e.period_start
                                and e.period_start.year == end_date.year
                                and e.period_start.month == 6
                            ]

                            june_labels = [_entry_label(e) for e in june_entries]
                            june_map = {_entry_label(e): e for e in june_entries}

                            if june_labels:
                                default_june_index = 0
                                for idx, candidate in enumerate(june_entries):
                                    if (
                                        candidate.q is not None
                                        and candidate.s is not None
                                        and abs(candidate.q - q) < 0.001
                                        and abs(candidate.s - s) < 0.001
                                        and _same_status(candidate.status, statut)
                                    ):
                                        default_june_index = idx
                                        break

                                june_label = st.selectbox(
                                    "Fiche de juin servant de base",
                                    june_labels,
                                    index=default_june_index,
                                    key=f"{prefix}_june_source",
                                )
                                june_entry = june_map[june_label]

                                june_exact = (june_entry.gross or 0.0) + (
                                    june_entry.fr_amount if june_entry.fr_found else 0.0
                                )

                                july_start = max(
                                    start_date if start_date else date(end_date.year, 7, 1),
                                    date(end_date.year, 7, 1),
                                )
                                july_days = (end_date - july_start).days + 1

                                if july_days > 0:
                                    july_estimation = round(
                                        (june_exact / 30.0) * july_days,
                                        2,
                                    )

                                    st.info(
                                        f"Estimation juillet : {_format_money(june_exact)} / 30 × "
                                        f"{july_days} jour(s) = {_format_money(july_estimation)}"
                                    )
                            else:
                                st.warning(
                                    "Aucune fiche de juin n'a été trouvée. "
                                    "Importez la fiche de juin ou introduisez le montant exact manuellement."
                                )

                exact_total = round(exact_from_slips + manual_extra + july_estimation, 2)

                st.success(
                    f"Salaire brut exact à reporter pour le trimestre {quarter_label} : "
                    f"**{_format_money(exact_total)}**"
                )

                if exact_total == 0:
                    global_errors.append(
                        f"Occupation {occ_index} — salaire brut exact du trimestre {quarter_label} égal à 0,00 €. Vérifiez les fiches sélectionnées."
                    )

            elif dmfa_state == "Je ne sais pas":
                global_errors.append(
                    f"Occupation {occ_index} — vérifiez si le trimestre {quarter_label} est déjà déclaré/accepté en DmfA avant de compléter le champ salaire brut exact."
                )

        occupation_results.append(
            {
                "fonction": fonction,
                "statut": statut,
                "start_date": start_date,
                "end_date": end_date,
                "q": q,
                "s": s,
                "tab": tab,
                "monthly_fr": monthly_fr,
                "index_value": index_value,
                "salary_monthly": salary_monthly,
                "mode_payment": mode_payment,
                "onss_text": onss_text,
                "quarter_label": quarter_label,
                "dmfa_state": dmfa_state,
                "exact_total": exact_total,
            }
        )

        st.divider()

    # --------------------------------------------------------
    # 5. INTERRUPTIONS
    # --------------------------------------------------------

    st.subheader("5. Interruptions à mentionner")

    valid_end_dates = [
        o["end_date"] for o in occupation_results if o["end_date"] is not None
    ]

    final_end_date = max(valid_end_dates) if valid_end_dates else None
    interruption_rows = []

    if final_end_date:
        window_start, window_end = interruption_window(final_end_date)

        st.caption(
            "Période à contrôler pour les interruptions : "
            f"{_format_date(window_start)} au {_format_date(window_end)}."
        )

        interruption_count = int(
            st.number_input(
                "Nombre d'interruptions à mentionner",
                min_value=0,
                max_value=3,
                value=0,
                step=1,
                key="c4_interruption_count",
            )
        )

        for i in range(1, interruption_count + 1):
            st.markdown(f"**Interruption {i}**")

            kind = st.selectbox(
                "Nature",
                [
                    "Protection de la maternité",
                    "Maladie / accident non couvert par un salaire garanti",
                    "Congé sans solde / absence non rémunérée après le 10e jour",
                    "Interruption de carrière à temps plein",
                    "Interruption de carrière à temps partiel",
                    "Autre événement à mentionner",
                ],
                key=f"c4_interrupt_{i}_kind",
            )

            c1, c2 = st.columns(2)
            with c1:
                start_text = st.text_input(
                    "Du",
                    placeholder="JJ/MM/AAAA",
                    key=f"c4_interrupt_{i}_start",
                )
            with c2:
                end_text = st.text_input(
                    "Au",
                    placeholder="JJ/MM/AAAA",
                    key=f"c4_interrupt_{i}_end",
                )

            start_i, error_start_i = _parse_user_date(start_text)
            end_i, error_end_i = _parse_user_date(end_text)

            if error_start_i:
                global_errors.append(f"Interruption {i} — date de début : {error_start_i}")
            if error_end_i:
                global_errors.append(f"Interruption {i} — date de fin : {error_end_i}")

            nature = kind
            if kind == "Autre événement à mentionner":
                nature = st.text_input(
                    "Précisez la nature",
                    key=f"c4_interrupt_{i}_nature",
                )

            if start_i and end_i:
                if end_i < start_i:
                    global_errors.append(
                        f"Interruption {i} — la date de fin est antérieure à la date de début."
                    )
                if start_i < window_start or end_i > window_end:
                    st.warning(
                        f"L'interruption {i} dépasse la période à contrôler. "
                        "Vérifiez si elle doit réellement être reprise sur ce C4."
                    )

            interruption_rows.append(
                {
                    "kind": kind,
                    "nature": nature,
                    "start": start_i,
                    "end": end_i,
                }
            )

    else:
        st.warning(
            "Indiquez d'abord la date de fin de l'occupation pour calculer la période d'interruptions à contrôler."
        )

    # --------------------------------------------------------
    # 6. FIN DE LA DERNIERE OCCUPATION
    # --------------------------------------------------------

    st.subheader("6. Fin de la dernière occupation")

    end_reason = st.selectbox(
        "Comment la dernière occupation a-t-elle pris fin ?",
        [
            "Fin de plein droit et sans préavis",
            "Le pouvoir organisateur a mis fin à l'occupation avec préavis",
            "Le pouvoir organisateur a mis fin à l'occupation sans préavis",
            "Le membre du personnel a quitté volontairement son emploi",
            "Autre / à compléter manuellement",
        ],
        key="c4_end_reason",
    )

    # Le formulaire comporte une zone libre « Motif du chômage ».
    # Elle est préremplie à partir du mode de fin choisi, mais reste modifiable.
    auto_motif = _default_unemployment_reason(end_reason)
    previous_end_reason = st.session_state.get("c4_previous_end_reason")
    current_motif = st.session_state.get("c4_motif_chomage", "")

    if previous_end_reason != end_reason:
        previous_auto = _default_unemployment_reason(previous_end_reason or "")
        if not current_motif.strip() or current_motif.strip() == previous_auto:
            st.session_state["c4_motif_chomage"] = auto_motif
        st.session_state["c4_previous_end_reason"] = end_reason

    motif_chomage = st.text_area(
        "Motif du chômage",
        key="c4_motif_chomage",
        height=80,
        help=(
            "Le motif est proposé automatiquement selon le mode de fin de l'occupation. "
            "Vous pouvez le modifier avant de générer le C4."
        ),
    )

    # Sécurité : même si le champ a été vidé accidentellement, une valeur cohérente
    # est reprise pour les quatre motifs standard. Pour « Autre », la saisie reste libre.
    motif_chomage_pdf = motif_chomage.strip() or auto_motif

    # --------------------------------------------------------
    # 7. CONTROLES
    # --------------------------------------------------------

    st.subheader("7. Contrôles")

    if not employee_name.strip():
        global_errors.append("Nom et prénom manquants.")
    if not niss.strip():
        global_errors.append("NISS manquant.")
    if not fase:
        global_errors.append("Numéro FASE de l'établissement manquant.")
    elif not fase_record:
        global_errors.append(f"Numéro FASE {fase} introuvable dans le fichier signalétique FWB.")
    if not establishment_name.strip():
        global_errors.append("Nom officiel de l'établissement introuvable à partir du FASE.")
    if not establishment_address.strip():
        global_errors.append("Adresse officielle de l'établissement introuvable à partir du FASE.")

    for i, occ in enumerate(occupation_results, start=1):
        if not occ["fonction"].strip():
            global_errors.append(f"Occupation {i} — fonction manquante.")
        if occ["q"] <= 0 or occ["s"] <= 0:
            global_errors.append(f"Occupation {i} — Q/S invalide.")
        if occ["tab"] <= 0:
            global_errors.append(f"Occupation {i} — TAB nul ou manquant.")

    # Déduplication en conservant l'ordre
    global_errors = list(dict.fromkeys(global_errors))

    if global_errors:
        for error in global_errors:
            st.warning(error)
    else:
        st.success("Les contrôles de base sont satisfaits.")

    # --------------------------------------------------------
    # 8. C4-ENSEIGNEMENT PRET A IMPRIMER
    # --------------------------------------------------------

    st.subheader("8. C4-Enseignement prêt à imprimer")

    responsible_name = st.text_input(
        "Nom du responsable / délégué qui signera le C4",
        key="c4_responsible_name",
    )
    declaration_date = st.date_input(
        "Date de la déclaration",
        value=date.today(),
        format="DD/MM/YYYY",
        key="c4_declaration_date",
    )

    rupture_indemnity = st.checkbox(
        "Une indemnité de rupture a été payée",
        value=False,
        key="c4_rupture_indemnity",
    )
    rupture_start = rupture_end = None
    if rupture_indemnity:
        rc1, rc2 = st.columns(2)
        with rc1:
            rs = st.text_input("Indemnité de rupture - du", placeholder="JJ/MM/AAAA", key="c4_rupture_start")
        with rc2:
            re_ = st.text_input("Indemnité de rupture - au", placeholder="JJ/MM/AAAA", key="c4_rupture_end")
        rupture_start, err = _parse_user_date(rs) if rs else (None, None)
        if err: global_errors.append("Date de début de l'indemnité de rupture invalide.")
        rupture_end, err = _parse_user_date(re_) if re_ else (None, None)
        if err: global_errors.append("Date de fin de l'indemnité de rupture invalide.")

    notice_method = "Lettre recommandée"
    notice_start = notice_end = notice_extended_until = None
    notice_suspended = False
    notice_suspension_reason = ""
    transition = False
    transition_start = transition_end = None

    if end_reason == "Le pouvoir organisateur a mis fin à l'occupation avec préavis":
        notice_method = st.radio(
            "Notification du préavis",
            ["Lettre recommandée", "Exploit d'huissier"],
            horizontal=True,
            key="c4_notice_method",
        )
        nc1, nc2 = st.columns(2)
        with nc1:
            ns = st.text_input("Préavis - du", placeholder="JJ/MM/AAAA", key="c4_notice_start")
        with nc2:
            ne = st.text_input("Préavis - au", placeholder="JJ/MM/AAAA", key="c4_notice_end")
        notice_start, err = _parse_user_date(ns) if ns else (None, None)
        if err: global_errors.append("Date de début du préavis invalide.")
        notice_end, err = _parse_user_date(ne) if ne else (None, None)
        if err: global_errors.append("Date de fin du préavis invalide.")

        notice_suspended = st.checkbox("Le délai de préavis a été suspendu", key="c4_notice_suspended")
        if notice_suspended:
            notice_suspension_reason = st.selectbox("Cause de suspension", ["Maladie", "Vacances", "Autre"], key="c4_notice_susp_reason")
            if notice_suspension_reason == "Autre":
                notice_suspension_reason = st.text_input("Autre cause", key="c4_notice_susp_other")
            nx = st.text_input("Préavis prolongé jusqu'au", placeholder="JJ/MM/AAAA", key="c4_notice_extended")
            notice_extended_until, err = _parse_user_date(nx) if nx else (None, None)
            if err: global_errors.append("Date de prolongation du préavis invalide.")

        transition = st.checkbox("Trajet de transition pendant le préavis", key="c4_transition")
        if transition:
            tc1, tc2 = st.columns(2)
            with tc1:
                ts = st.text_input("Trajet de transition - du", placeholder="JJ/MM/AAAA", key="c4_transition_start")
            with tc2:
                te = st.text_input("Trajet de transition - au", placeholder="JJ/MM/AAAA", key="c4_transition_end")
            transition_start, err = _parse_user_date(ts) if ts else (None, None)
            if err: global_errors.append("Date de début du trajet de transition invalide.")
            transition_end, err = _parse_user_date(te) if te else (None, None)
            if err: global_errors.append("Date de fin du trajet de transition invalide.")

    if not responsible_name.strip():
        global_errors.append("Nom du responsable / délégué manquant pour le PDF.")

    template_pdf, template_error = _template_bytes(TEMPLATE_C4_ENSEIGNEMENT)
    if template_error:
        st.error(template_error)
        return

    if not _template_contains_version(template_pdf, EXPECTED_C4_ENSEIGNEMENT_VERSION):
        st.error(
            "Le PDF placé dans assets/c4_enseignement_officiel.pdf ne correspond pas à la version "
            f"attendue ({EXPECTED_C4_ENSEIGNEMENT_VERSION}). Les coordonnées d'impression pourraient être incorrectes."
        )
        return

    global_errors = list(dict.fromkeys(global_errors))
    if global_errors:
        st.warning("Le PDF prêt à imprimer est bloqué tant que les avertissements ci-dessus ne sont pas corrigés.")
        return

    pdf_data = {
        "niss": niss,
        "employee_name": employee_name,
        "employee_address": employee_address,
        "fase": fase,
        "establishment_name": establishment_name,
        "establishment_address": establishment_address,
        "occupations": occupation_results,
        "interruptions": interruption_rows,
        "remarks": "",
        "final_end_date": final_end_date,
        "end_reason": end_reason,
        "motif_chomage": motif_chomage_pdf,
        "responsible_name": responsible_name,
        "declaration_date": declaration_date,
        "rupture_indemnity": rupture_indemnity,
        "rupture_start": rupture_start,
        "rupture_end": rupture_end,
        "notice_method": notice_method,
        "notice_start": notice_start,
        "notice_end": notice_end,
        "notice_suspended": notice_suspended,
        "notice_suspension_reason": notice_suspension_reason,
        "notice_extended_until": notice_extended_until,
        "transition": transition,
        "transition_start": transition_start,
        "transition_end": transition_end,
    }

    try:
        c4_pdf = generate_c4_enseignement_pdf(pdf_data, template_pdf)
    except Exception as exc:
        st.error(f"La génération du C4-Enseignement a échoué : {exc}")
        return

    st.success(
        "Le C4-Enseignement est prêt à imprimer. La rubrique II destinée à l'enseignant reste volontairement vierge. "
        "La signature de l'employeur doit être apposée après impression."
    )
    st.download_button(
        "Télécharger le C4-Enseignement prêt à imprimer",
        data=c4_pdf,
        file_name="C4_enseignement_complete.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
