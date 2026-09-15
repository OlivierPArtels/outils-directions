from __future__ import annotations

import calendar
import io
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import streamlit as st
from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


# ============================================================
# CONSTANTES
# ============================================================

BCE_FWB_ENSEIGNEMENT = "0220916609"
BCE_FWB_ACS_APE = "0220916609"
ONSS_EMPLOYEUR_ACS_APE = "000370539"

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

TEMPLATE_C4_ENSEIGNEMENT = ASSETS_DIR / "c4_enseignement_officiel.pdf"
TEMPLATE_C4_CLASSIQUE = ASSETS_DIR / "c4_classique_officiel.pdf"
FASE_DATABASE_FILE = ASSETS_DIR / "etablissements_fase.json"

EXPECTED_C4_ENSEIGNEMENT_VERSION = "06.07.2023/830.10.015"
EXPECTED_C4_CLASSIQUE_VERSION = "06.07.2023/830.10.016"

MONTH_NAMES_FR = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}


# ============================================================
# FONCTIONS ENSEIGNEMENT
# ============================================================

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
# FONCTIONS ACS / APE / PART-APE / PTP
# ============================================================

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

REGIMES_HORAIRES_ACS_APE: dict[str, tuple[float, float]] = {
    "Mi-temps — 18/36": (18.0, 36.0),
    "4/5e temps — 32/36": (32.0, 36.0),
    "Temps plein — 36/36": (36.0, 36.0),
}


def _acs_ape_function_label(option: str) -> str:
    if " — " in option:
        return option.split(" — ", 1)[1].strip()
    return option.strip()


def _format_fonction_option(code: str) -> str:
    if not code:
        return "— Sélectionner une fonction —"
    return f"{code} — {FONCTIONS_PAR_CODE[code]}"


# ============================================================
# CHAMP DATE JJ/MM/AAAA
# ============================================================


def _format_masked_date(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")[:8]
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}/{digits[2:]}"
    return f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"


def _sync_masked_date(widget_key: str, state_key: str) -> None:
    formatted = _format_masked_date(st.session_state.get(widget_key, ""))
    st.session_state[widget_key] = formatted
    st.session_state[state_key] = formatted


def _masked_date_input(label: str, key: str, value: str = "") -> str:
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
# REPERTOIRE FASE
# ============================================================


def _normalize_fase(value: str | int | float | None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    match = re.search(r"\d+(?:[.,]0+)?", text)
    if not match:
        return ""
    number = match.group(0).replace(",", ".")
    try:
        return str(int(float(number)))
    except ValueError:
        return ""


def _load_fase_database() -> tuple[dict[str, dict], str]:
    if not FASE_DATABASE_FILE.exists():
        return {}, (
            "Le répertoire FASE est absent : assets/etablissements_fase.json. "
            "Ajoutez ce fichier dans le dépôt GitHub."
        )
    try:
        with FASE_DATABASE_FILE.open("r", encoding="utf-8") as fh:
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
        if re.fullmatch(r"[0-9]{8,14}", line.strip()):
            break
        address_lines.append(line)

    return name, "\n".join(address_lines).strip()


def parse_payroll_page(text: str, file_name: str, page_number: int) -> PayrollEntry:
    cleaned_text = text.replace("\u00a0", " ")
    lines = [_clean_spaces(line) for line in cleaned_text.splitlines() if _clean_spaces(line)]

    entry = PayrollEntry(file_name=file_name, page_number=page_number, raw_text=cleaned_text)

    entry.employee_name, entry.employee_address, entry.employee_matricule = _extract_employee_identity(lines)
    entry.establishment_name, entry.establishment_address = _extract_establishment(lines)

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

    liquidation_match = _find_first([r"Mois\s+de\s+liquidation\s*:\s*([^\n\r]+)"], cleaned_text)
    if liquidation_match:
        entry.liquidation_month = _clean_spaces(liquidation_match.group(1))

    period_match = _find_first(
        [r"P[ée]riode\s+concern[ée]e?\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{2,4})\s+au\s+([0-9]{2}/[0-9]{2}/[0-9]{2,4})"],
        cleaned_text,
    )
    if period_match:
        entry.period_start = _parse_date(period_match.group(1))
        entry.period_end = _parse_date(period_match.group(2))

    status_match = _find_first([r"Statut\s*:\s*([^\n\r]+)"], cleaned_text)
    if status_match:
        entry.status = _clean_spaces(status_match.group(1))

    scale_match = _find_first([r"Echelle\s+bar[ée]mique\s*:\s*([^\n\r]+)"], cleaned_text)
    if scale_match:
        entry.salary_scale = _clean_spaces(scale_match.group(1))

    seniority_match = _find_first([r"Anciennet[ée]\s+p[ée]cuniaire\s*:\s*([^\n\r]+)"], cleaned_text)
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

    index_match = _find_first([r"Index\s*:\s*([0-9]+[,.][0-9]{4,6})"], cleaned_text)
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
                errors.append(f"{uploaded_file.name}, page {page_index} : extraction impossible ({exc}).")
                continue

            if not text.strip():
                errors.append(
                    f"{uploaded_file.name}, page {page_index} : aucun texte exploitable. "
                    "Le PDF est peut-être scanné sous forme d'image."
                )
                continue

            entries.append(parse_payroll_page(text, uploaded_file.name, page_index))

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
    if entry.period_start.year != entry.period_end.year or entry.period_start.month != entry.period_end.month:
        return round(entry.fr_amount, 2)

    total_days = calendar.monthrange(entry.period_start.year, entry.period_start.month)[1]
    covered_days = (entry.period_end - entry.period_start).days + 1
    if covered_days <= 0 or covered_days >= total_days:
        return round(entry.fr_amount, 2)
    return round((entry.fr_amount / covered_days) * total_days, 2)


def quarter_info(d: date) -> tuple[int, date, date, str]:
    quarter = ((d.month - 1) // 3) + 1
    start_month = 1 + (quarter - 1) * 3
    end_month = start_month + 2
    start = date(d.year, start_month, 1)
    end = date(d.year, end_month, calendar.monthrange(d.year, end_month)[1])
    label = f"{quarter:02d}/{d.year}"
    return quarter, start, end, label


def calculate_exact_gross_rule_of_three(
    monthly_salary: float,
    occupation_start: date,
    occupation_end: date,
) -> tuple[Optional[float], list[dict]]:
    """Calcule le salaire brut exact du trimestre de fin par règle de trois."""
    if monthly_salary is None or monthly_salary <= 0:
        return None, []
    if occupation_start is None or occupation_end is None:
        return None, []
    if occupation_end < occupation_start:
        return None, []

    _, quarter_start, quarter_end, _ = quarter_info(occupation_end)
    calculation_start = max(occupation_start, quarter_start)
    calculation_end = min(occupation_end, quarter_end)
    if calculation_end < calculation_start:
        return None, []

    total = 0.0
    details: list[dict] = []
    year = calculation_start.year
    month = calculation_start.month

    while (year, month) <= (calculation_end.year, calculation_end.month):
        days_in_month = calendar.monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month)
        covered_start = max(calculation_start, month_start)
        covered_end = min(calculation_end, month_end)

        if covered_start <= covered_end:
            covered_days = (covered_end - covered_start).days + 1
            daily_salary = monthly_salary / days_in_month
            month_amount = daily_salary * covered_days
            total += month_amount
            details.append(
                {
                    "year": year,
                    "month": month,
                    "days_in_month": days_in_month,
                    "covered_days": covered_days,
                    "covered_start": covered_start,
                    "covered_end": covered_end,
                    "daily_salary": round(daily_salary, 6),
                    "amount": round(month_amount, 2),
                }
            )

        month += 1
        if month == 13:
            month = 1
            year += 1

    return round(total, 2), details


def _show_exact_gross_calculation(
    monthly_salary: float,
    occupation_start: date,
    occupation_end: date,
    quarter_label: str,
) -> Optional[float]:
    total, details = calculate_exact_gross_rule_of_three(
        monthly_salary=monthly_salary,
        occupation_start=occupation_start,
        occupation_end=occupation_end,
    )
    if total is None:
        return None

    st.success(
        f"Salaire brut exact à reporter pour le trimestre {quarter_label} : "
        f"**{_format_money(total)}**"
    )
    st.caption(
        "Calcul automatique par règle de trois : salaire mensuel brut ÷ nombre de jours "
        "calendrier du mois × nombre de jours couverts."
    )

    for detail in details:
        name = MONTH_NAMES_FR[detail["month"]].capitalize()
        st.write(
            f"**{name} {detail['year']}** : "
            f"{_format_money(monthly_salary)} ÷ {detail['days_in_month']} × "
            f"{detail['covered_days']} jour(s) = **{_format_money(detail['amount'])}**"
        )

    return total


def interruption_window(end_date: date) -> tuple[date, date]:
    if end_date.month in (1, 4, 7, 10):
        year = end_date.year
        month = end_date.month - 3
        while month <= 0:
            month += 12
            year -= 1
        return date(year, month, 1), end_date
    _, start, _, _ = quarter_info(end_date)
    return start, end_date


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
    return (
        f"{entry.file_name} — p. {entry.page_number} — {period} — "
        f"{entry.status or 'statut ?'} — {fraction} — brut {_format_money(entry.gross)}"
    )


def _parse_user_date(value: str) -> tuple[Optional[date], Optional[str]]:
    value = (value or "").strip()
    if not value:
        return None, "Date manquante."
    parsed = _parse_date(value)
    if not parsed:
        return None, "Date invalide. Utilisez JJ/MM/AAAA."
    return parsed, None


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


def _detect_acs_program(entry: PayrollEntry) -> str:
    text = (entry.raw_text or "").upper().replace("–", "-")
    if "PART-APE" in text or "PART APE" in text:
        return "PART-APE"
    if re.search(r"\bPTP\b", text):
        return "PTP"
    if re.search(r"\bACS\b", text):
        return "ACS"
    if re.search(r"\bAPE\b", text):
        return "APE"
    return ""


# ============================================================
# GENERATION PDF - OUTILS COMMUNS
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
            "Ajoutez le PDF officiel dans le dossier assets du dépôt GitHub."
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

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _draw_text(c, x: float, y: float, text: object, size: float = 8.0, max_chars: int | None = None):
    if text is None:
        return
    value = str(text).replace("\u00a0", " ").strip()
    if not value:
        return
    if max_chars:
        value = value[:max_chars]
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", size)
    c.drawString(x, y, value)


def _draw_multiline(
    c,
    x: float,
    y: float,
    text: object,
    size: float = 8.0,
    leading: float = 9.5,
    max_chars: int = 100,
    max_lines: int = 4,
):
    value = str(text or "").replace("\u00a0", " ").strip()
    if not value:
        return
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        proposal = word if not current else f"{current} {word}"
        if len(proposal) <= max_chars:
            current = proposal
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", size)
    for i, line in enumerate(lines[:max_lines]):
        c.drawString(x, y - i * leading, line)


def _draw_check(c, x: float, y: float, checked: bool, size: float = 8.0):
    if not checked:
        return
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, "X")


def _draw_date(c, x: float, y: float, value: Optional[date], size: float = 8.0):
    if value:
        _draw_text(c, x, y, value.strftime("%d/%m/%Y"), size=size)


def _draw_decimal(c, x: float, y: float, value: Optional[float], decimals: int = 2, size: float = 8.2):
    if value is None:
        return
    txt = f"{float(value):.{decimals}f}".replace(".", ",")
    _draw_text(c, x, y, txt, size=size)


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
    if text is None:
        return
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


def _draw_clean_date(
    c,
    x: float,
    y: float,
    value: Optional[date],
    mask_width: float = 91.0,
    size: float = 7.5,
):
    if not value:
        return
    _mask_pdf_area(c, x - 1.0, y - 1.8, mask_width, size + 3.1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", size)
    c.drawString(x, y, value.strftime("%d/%m/%Y"))


def _draw_clean_money(
    c,
    x_right: float,
    y: float,
    value: Optional[float],
    field_left: float,
    field_width: float,
    size: float = 7.5,
):
    if value is None:
        return
    txt = f"{float(value):.2f}".replace(".", ",")
    _mask_pdf_area(c, field_left, y - 1.8, field_width, size + 3.1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", size)
    c.drawRightString(x_right, y, txt)


def _draw_box_x(c, left: float, bottom: float, width: float = 6.5, height: float = 6.5):
    size = min(5.1, height * 0.82)
    x_width = stringWidth("X", "Helvetica-Bold", size)
    x = left + (width - x_width) / 2.0
    y = bottom + (height - size * 0.72) / 2.0
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, "X")


def _draw_clean_fraction(
    c,
    x: float,
    y: float,
    value: Optional[float],
    field_width: float = 65.0,
    size: float = 7.6,
):
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


# ============================================================
# C4-ENSEIGNEMENT - PDF
# ============================================================


def generate_c4_enseignement_pdf(data: dict, template_pdf: bytes) -> bytes:
    occupations = data.get("occupations", [])
    interruptions = data.get("interruptions", [])

    occ_layouts = [
        {
            "function_y": 571.2,
            "status_y": 555.7,
            "q_y": 538.2,
            "s_y": 524.3,
            "entry_y": 571.2,
            "end_y": 555.7,
            "salary_y": 536.2,
            "exact1_y": 521.9,
            "mode_boxes": [(325.2, 492.8, 4.8, 4.8), (341.5, 492.8, 4.8, 4.8), (357.8, 492.8, 4.8, 4.8)],
            "onss_boxes": [(186.2, 474.4, 5.8, 5.8), (186.2, 464.3, 5.8, 5.8), (186.2, 454.9, 5.8, 5.8), (186.2, 444.8, 5.8, 5.8)],
            "onss_date_y": 462.7,
        },
        {
            "function_y": 421.6,
            "status_y": 406.1,
            "q_y": 388.6,
            "s_y": 374.7,
            "entry_y": 421.6,
            "end_y": 406.1,
            "salary_y": 386.6,
            "exact1_y": 372.3,
            "mode_boxes": [(324.5, 338.8, 4.8, 4.8), (340.8, 338.8, 4.8, 4.8), (357.4, 338.8, 4.8, 4.8)],
            "onss_boxes": [(186.2, 325.3, 5.8, 5.8), (186.2, 315.2, 5.8, 5.8), (186.2, 305.9, 5.8, 5.8), (186.2, 295.8, 5.8, 5.8)],
            "onss_date_y": 313.5,
        },
        {
            "function_y": 272.4,
            "status_y": 256.9,
            "q_y": 239.4,
            "s_y": 225.5,
            "entry_y": 272.4,
            "end_y": 256.9,
            "salary_y": 237.4,
            "exact1_y": 223.1,
            "mode_boxes": [(324.5, 189.5, 4.8, 4.8), (340.8, 189.5, 4.8, 4.8), (357.4, 189.5, 4.8, 4.8)],
            "onss_boxes": [(186.2, 176.3, 5.8, 5.8), (186.2, 166.2, 5.8, 5.8), (186.2, 156.6, 5.8, 5.8), (186.2, 146.5, 5.8, 5.8)],
            "onss_date_y": 164.5,
        },
    ]

    def page1(c):
        niss = re.sub(r"\D", "", data.get("niss", "") or "")
        if len(niss) == 11:
            niss = f"{niss[:6]}/{niss[6:9]}-{niss[9:]}"

        _draw_clean_value(c, 91, 721.0, niss, size=7.7, max_width=96, mask_width=98)
        _draw_clean_value(c, 252, 721.0, data.get("employee_name", ""), size=7.7, max_width=285)
        _draw_clean_value(c, 88, 694.4, data.get("employee_address", ""), size=7.35, max_width=455)
        _draw_clean_value(c, 168, 668.2, data.get("establishment_name", ""), size=7.45, max_width=380)
        _draw_clean_value(c, 30, 643.6, data.get("establishment_address", ""), size=7.35, max_width=520)
        _draw_clean_value(c, 52, 618.0, BCE_FWB_ENSEIGNEMENT, size=7.7, max_width=95, mask_width=102)

        for idx, occ in enumerate(occupations[:3]):
            lay = occ_layouts[idx]
            _draw_clean_value(c, 62, lay["function_y"], occ.get("fonction", ""), size=7.35, max_width=172)
            _draw_clean_value(c, 55, lay["status_y"], occ.get("statut", ""), size=7.35, max_width=180)
            _draw_clean_fraction(c, 132.5, lay["q_y"], occ.get("q"), field_width=70, size=7.45)
            _draw_clean_fraction(c, 132.5, lay["s_y"], occ.get("s"), field_width=70, size=7.45)
            _draw_clean_date(c, 304, lay["entry_y"], occ.get("start_date"), mask_width=92, size=7.45)
            _draw_clean_date(c, 304, lay["end_y"], occ.get("end_date"), mask_width=92, size=7.45)
            _draw_clean_money(c, 431, lay["salary_y"], occ.get("salary_monthly"), 347, 86, size=7.45)

            if occ.get("dmfa_state") == "Non / le salaire brut exact doit être complété":
                _draw_clean_money(c, 416, lay["exact1_y"], occ.get("exact_total"), 327, 91, size=7.35)
                qtr, year = _quarter_parts(occ.get("quarter_label", ""))
                quarter_text = f"{qtr}/{year}" if qtr and year else ""
                _draw_clean_value(c, 493, lay["exact1_y"], quarter_text, size=7.2, max_width=61, mask_width=63)

            mode_payment = str(occ.get("mode_payment", ""))
            mode_map = {"10": 0, "12": 1, "20": 2}
            if mode_payment in mode_map:
                _draw_box_x(c, *lay["mode_boxes"][mode_map[mode_payment]])

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

        if interruptions:
            _draw_box_x(c, 128.4, 93.2, 6.5, 6.5)
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
            _draw_box_x(c, 35.0, 93.2, 6.5, 6.5)

        _draw_clean_value(c, 68, 50.4, data.get("remarks", ""), size=6.7, max_width=465)

    def page2(c):
        niss = re.sub(r"\D", "", data.get("niss", "") or "")
        if len(niss) == 11:
            niss = f"{niss[:6]}/{niss[6:9]}-{niss[9:]}"
        _draw_clean_value(c, 142, 803.6, niss, size=7.5, max_width=145, mask_width=147)

        end_date = data.get("final_end_date")
        end_reason = data.get("end_reason", "")

        if end_reason == "Fin de plein droit et sans préavis":
            _draw_clean_date(c, 211.4, 766.8, end_date, mask_width=91, size=7.2)
        elif end_reason == "Le pouvoir organisateur a mis fin à l'occupation avec préavis":
            _draw_box_x(c, 29.5, 717.0, 6.5, 6.5)
            _draw_clean_date(c, 209.1, 718.8, end_date, mask_width=89, size=7.0)

            if data.get("notice_method") == "Exploit d'huissier":
                _draw_box_x(c, 142.0, 681.0, 6.5, 6.5)
            else:
                _draw_box_x(c, 142.0, 699.0, 6.5, 6.5)

            _draw_clean_date(c, 157.1, 664.8, data.get("notice_start"), mask_width=89, size=7.0)
            _draw_clean_date(c, 261.8, 664.8, data.get("notice_end"), mask_width=89, size=7.0)

            suspended = bool(data.get("notice_suspended"))
            if suspended:
                _draw_box_x(c, 251.8, 645.0, 6.5, 6.5)
            else:
                _draw_box_x(c, 159.6, 645.0, 6.5, 6.5)

            if suspended:
                suspension_reason = data.get("notice_suspension_reason", "")
                if suspension_reason == "Maladie":
                    _draw_box_x(c, 377.3, 645.0, 6.5, 6.5)
                elif suspension_reason == "Vacances":
                    _draw_box_x(c, 377.3, 627.0, 6.5, 6.5)
                elif suspension_reason:
                    _draw_box_x(c, 377.3, 609.0, 6.5, 6.5)
                    _draw_clean_value(c, 411.2, 610.7, suspension_reason, size=6.8, max_width=129)
                _draw_clean_date(c, 188.9, 595.8, data.get("notice_extended_until"), mask_width=92, size=7.0)

            transition = bool(data.get("transition"))
            if transition:
                _draw_box_x(c, 106.5, 558.0, 5.8, 5.8)
                _draw_clean_date(c, 141.3, 559.8, data.get("transition_start"), mask_width=89, size=6.8)
                _draw_clean_date(c, 246.1, 559.8, data.get("transition_end"), mask_width=89, size=6.8)
            else:
                _draw_box_x(c, 79.0, 558.0, 6.0, 5.8)

        elif end_reason == "Le pouvoir organisateur a mis fin à l'occupation sans préavis":
            _draw_box_x(c, 29.5, 510.0, 6.5, 6.5)
            _draw_clean_date(c, 252.8, 511.8, end_date, mask_width=93, size=7.2)

        elif end_reason == "Le membre du personnel a quitté volontairement son emploi":
            _draw_box_x(c, 29.5, 492.0, 6.5, 6.5)
            _draw_clean_date(c, 211.4, 493.8, end_date, mask_width=93, size=7.2)

        if data.get("rupture_indemnity"):
            _draw_box_x(c, 29.5, 735.0, 6.5, 6.5)
            _draw_clean_date(c, 248.6, 736.8, data.get("rupture_start"), mask_width=89, size=7.0)
            _draw_clean_date(c, 355.3, 736.8, data.get("rupture_end"), mask_width=89, size=7.0)

        motive = (data.get("motif_chomage", "") or "").strip()
        if not motive:
            motive = _default_unemployment_reason(end_reason)

        if motive:
            words = motive.split()
            lines: list[str] = []
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

        _draw_clean_date(c, 46, 369.6, data.get("declaration_date"), mask_width=90, size=7.2)
        _draw_clean_value(c, 228, 386.0, data.get("responsible_name", ""), size=7.0, max_width=285)

    return _merge_overlays(template_pdf, {0: page1, 1: page2})


# ============================================================
# C4 CLASSIQUE - PDF
# Coordonnées recalibrées sur le formulaire officiel 5 pages.
# ============================================================


def generate_c4_classique_pdf(data: dict, template_pdf: bytes) -> bytes:
    """Génère le C4 classique ONEM 06.07.2023/830.10.016."""

    def clean_text(c, x, y, value, width, size=7.6, max_chars=None):
        if value is None:
            return
        text = str(value).replace("\u00a0", " ").strip()
        if not text:
            return
        if max_chars:
            text = text[:max_chars]
        _mask_pdf_area(c, x - 1.0, y - 2.0, width, size + 4.0)
        _draw_text(c, x, y, text, size=size)

    def clean_date(c, x, y, value, width=48, size=7.2):
        if not value:
            return
        clean_text(c, x, y, value.strftime("%d/%m/%Y"), width, size=size)

    def clean_number(c, x, y, value, width, decimals=2, size=7.8):
        if value is None:
            return
        text = f"{float(value):.{decimals}f}".replace(".", ",")
        clean_text(c, x, y, text, width, size=size)

    def draw_precise_reason(c, value):
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            return

        words = text.split()
        lines = []
        limits = [245.0, 525.0]
        starts = [305.0, 27.0]

        for line_index, limit in enumerate(limits):
            current = ""
            while words:
                proposal = words[0] if not current else f"{current} {words[0]}"
                if stringWidth(proposal, "Helvetica", 7.1) <= limit:
                    current = proposal
                    words.pop(0)
                else:
                    break
            if current:
                lines.append((starts[line_index], current, limit))
            if not words:
                break

        ys = [439.5, 421.5]
        for i, (x, line, width) in enumerate(lines[:2]):
            clean_text(c, x, ys[i], line, width, size=7.1)

    def page1(c):
        # TRAVAILLEUR / EMPLOYEUR
        _draw_niss(c, 92, 666, data.get("niss", ""))
        _draw_text(c, 250, 666, data.get("employee_name", ""), 8.0, 78)
        _draw_text(c, 92, 638, data.get("employer_name", ""), 7.8, 55)
        _draw_text(c, 314, 638, data.get("employer_category", ""), 7.6, 18)
        _draw_text(c, 437, 638, data.get("enterprise_number", ""), 7.8, 22)
        _draw_text(c, 314, 613, data.get("joint_committee", ""), 7.8, 16)
        _draw_text(c, 449, 613, data.get("onss_number", ""), 7.8, 20)
        _draw_multiline(c, 28, 587, data.get("employer_address", ""), 7.8, 8.5, 112)

        # PARTIE A - OCCUPATION
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
            "par heure": (48, 383),
            "par mois": (48, 370),
            "par jour": (48, 357),
            "par semaine": (48, 344),
            "par trimestre": (48, 331),
            "par année": (225, 383),
        }
        if freq in freq_coords:
            _draw_check(c, *freq_coords[freq], True)

        # SALAIRE BRUT EXACT - CORRIGÉ
        exact_gross = data.get("exact_gross")
        if exact_gross is not None:
            clean_number(c, 117, 309.0, exact_gross, 86, decimals=2, size=8.0)
            clean_text(c, 292, 309.0, data.get("quarter_label", ""), 79, size=7.7)

        # VACANCES - CORRIGÉ
        vacation_type = data.get("vacation_type", "Temps partiel")
        vacation_amount = float(data.get("vacation_amount", 0) or 0)
        if vacation_type == "Temps plein":
            _draw_box_x(c, 62.64, 250.22, 8.02, 9.99)
            clean_number(c, 160, 251.0, vacation_amount, 33, decimals=1, size=7.7)
        else:
            _draw_box_x(c, 62.63, 238.82, 8.02, 9.99)
            clean_number(c, 164, 239.6, vacation_amount, 33, decimals=1, size=7.7)

        public_regime = data.get("public_regime", "Non applicable")
        if public_regime == "Secteur public":
            _draw_box_x(c, 389.04, 219.74, 8.02, 9.99)
        elif public_regime == "Secteur privé":
            _draw_box_x(c, 450.97, 219.74, 8.02, 9.99)

        holidays = data.get("paid_holidays_after_end", []) or []
        if holidays:
            _draw_box_x(c, 71.88, 192.98, 8.02, 9.99)
            holiday_xs = [103.5, 217.5, 331.5, 445.5]
            for idx, holiday in enumerate(holidays[:4]):
                clean_date(c, holiday_xs[idx], 195.6, holiday, width=47, size=6.8)
        else:
            _draw_box_x(c, 41.76, 192.98, 8.02, 9.99)

        comp_days = float(data.get("comp_rest_days", 0) or 0)
        if comp_days > 0:
            _draw_box_x(c, 270.48, 160.46, 8.02, 9.99)
            clean_number(c, 314, 163.7, comp_days, 51, decimals=1, size=7.5)
        else:
            _draw_box_x(c, 242.52, 160.47, 8.02, 9.99)

        # IMPORTANT : Partie B = page 2, jamais page 1.

    def page2(c):
        _draw_niss(c, 143, 809, data.get("niss", ""))

        # PARTIE B - CORRIGÉE
        qtr_rows = data.get("quarter_rows", []) or []
        row_layouts = [
            {
                "date_y": 709.0,
                "int_non": (439.92, 708.26, 8.02, 9.99),
                "int_oui": (489.48, 708.26, 8.02, 9.99),
                "q_non": (439.92, 696.26, 8.02, 9.99),
                "q_oui": (489.48, 696.26, 8.02, 9.99),
            },
            {
                "date_y": 685.0,
                "int_non": (439.92, 684.26, 8.02, 9.99),
                "int_oui": (489.48, 684.26, 8.02, 9.99),
                "q_non": (439.92, 672.26, 8.02, 9.99),
                "q_oui": (489.48, 672.26, 8.02, 9.99),
            },
        ]

        for idx, row in enumerate(qtr_rows[:2]):
            lay = row_layouts[idx]
            clean_date(c, 52, lay["date_y"], row.get("start"), width=111, size=7.2)
            clean_date(c, 190, lay["date_y"], row.get("end"), width=111, size=7.2)
            _draw_box_x(c, *(lay["int_oui"] if row.get("interruption", False) else lay["int_non"]))
            _draw_box_x(c, *(lay["q_oui"] if row.get("q_diff", False) else lay["q_non"]))

        # PARTIE C - FIN DE L'OCCUPATION - CORRIGÉE
        reason = data.get("end_reason", "Durée déterminée arrivée à terme")
        reason_boxes = {
            "Préavis par l'employeur": (37.56, 603.26, 8.02, 9.99),
            "Rupture par l'employeur": (37.58, 554.31, 8.02, 9.99),
            "Démission / abandon volontaire": (37.59, 537.87, 8.02, 9.99),
            "Commun accord": (37.58, 521.55, 8.02, 9.99),
            "Force majeure médicale": (37.57, 505.24, 8.02, 9.99),
            "Force majeure autre": (37.57, 488.92, 8.02, 9.99),
            "Durée déterminée arrivée à terme": (37.57, 472.60, 8.02, 9.99),
            "Travail déterminé arrivé à terme": (37.56, 456.29, 8.02, 9.99),
        }
        if reason in reason_boxes:
            _draw_box_x(c, *reason_boxes[reason])

        end_date = data.get("occupation_end")
        if reason == "Préavis par l'employeur":
            method = data.get("notice_method", "Lettre recommandée")
            notice_sent = data.get("notice_sent")
            if method == "Exploit d'huissier":
                _draw_box_x(c, 58.81, 570.63, 8.02, 9.99)
                clean_date(c, 170, 574.6, notice_sent, width=91, size=7.1)
            else:
                _draw_box_x(c, 58.80, 586.95, 8.02, 9.99)
                clean_date(c, 185, 590.9, notice_sent, width=91, size=7.1)
        elif reason == "Rupture par l'employeur":
            clean_date(c, 160, 558.2, end_date, width=91, size=7.1)
        elif reason == "Démission / abandon volontaire":
            clean_date(c, 222, 541.8, end_date, width=91, size=7.1)
        elif reason == "Commun accord":
            clean_date(c, 240, 525.5, end_date, width=91, size=7.1)
        elif reason == "Force majeure autre":
            clean_date(c, 227, 492.9, end_date, width=91, size=7.1)

        # Pour les points 5, 7 et 8, aucune date n'est imprimée sur la ligne.
        draw_precise_reason(c, data.get("precise_reason", ""))

        indemnity_type = data.get("indemnity_type", "Aucune")
        if indemnity_type == "Salaire pendant le délai de préavis":
            _draw_box_x(c, 32.28, 357.86, 8.02, 9.99)
            clean_date(c, 168, 343.4, data.get("indemnity_start"), width=91, size=7.1)
            clean_date(c, 268, 343.4, data.get("indemnity_end"), width=91, size=7.1)

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
        _draw_text(c, 199, 542, data.get("responsible_name", ""), 7.8, 72)

    return _merge_overlays(template_pdf, {0: page1, 1: page2, 2: page3, 3: page4})


# ============================================================
# AIDES INTERFACE
# ============================================================


def _show_detected_entries(entries: list[PayrollEntry]) -> None:
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


def _render_fase_block(prefix: str) -> tuple[str, Optional[dict], str, str]:
    fase_database, fase_database_error = _load_fase_database()
    fase_input = st.text_input(
        "N° FASE de l'établissement",
        placeholder="Ex. 765",
        key=f"{prefix}_fase",
    )
    fase = _normalize_fase(fase_input)
    fase_record = fase_database.get(fase) if fase else None
    establishment_name = ""
    establishment_address = ""

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

    return fase, fase_record, establishment_name, establishment_address


def _parse_holiday_list(text: str) -> tuple[list[date], list[str]]:
    dates: list[date] = []
    errors: list[str] = []
    for chunk in [x.strip() for x in (text or "").split(",") if x.strip()]:
        d, err = _parse_user_date(chunk)
        if d:
            dates.append(d)
        if err:
            errors.append(chunk)
    return dates, errors


def _render_indemnity_block(prefix: str):
    indemnity_type = st.selectbox(
        "Une indemnité a-t-elle été payée ?",
        ["Aucune", "Salaire pendant le délai de préavis", "Indemnité de congé / rupture", "Autre indemnité"],
        key=f"{prefix}_indemnity_type",
    )

    indemnity_start = indemnity_end = None
    other_indemnity_name = ""
    other_indemnity_amount = 0.0

    if indemnity_type != "Aucune":
        c1, c2 = st.columns(2)
        with c1:
            ind_start_txt = _masked_date_input("Période couverte - du", key=f"{prefix}_ind_start")
        with c2:
            ind_end_txt = _masked_date_input("Période couverte - au", key=f"{prefix}_ind_end")
        indemnity_start, _ = _parse_user_date(ind_start_txt)
        indemnity_end, _ = _parse_user_date(ind_end_txt)

        if indemnity_type == "Autre indemnité":
            other_indemnity_name = st.text_input("Nature de l'autre indemnité", key=f"{prefix}_other_ind_name")
            other_indemnity_amount = st.number_input(
                "Montant de l'autre indemnité",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key=f"{prefix}_other_ind_amount",
            )

    return indemnity_type, indemnity_start, indemnity_end, other_indemnity_name, other_indemnity_amount


# ============================================================
# INTERFACE C4 CLASSIQUE - MANUEL
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
        if entries:
            _show_detected_entries(entries)

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
        occupation_start_txt = _masked_date_input("Date de début de l'occupation", key="c4c_occ_start")
        service_start_txt = _masked_date_input("Date d'entrée en service", key="c4c_service_start")
    with c2:
        occupation_end_txt = _masked_date_input("Date de fin de l'occupation", key="c4c_occ_end")
        worker_code = st.text_input("Code travailleur", key="c4c_worker_code")
    with c3:
        status = st.text_input("Statut", key="c4c_status")
        employment_measure = st.text_input("Mesure de promotion de l'emploi", key="c4c_employment_measure")

    occupation_start, e1 = _parse_user_date(occupation_start_txt)
    service_start, e2 = _parse_user_date(service_start_txt)
    occupation_end, e3 = _parse_user_date(occupation_end_txt)

    onss_case = st.selectbox(
        "Cotisations ONSS - secteur chômage",
        ["Prélevées", "Non prélevées et non versées", "Non retenues mais seront versées", "Statutaire art. 9"],
        key="c4c_onss_case",
    )

    c1, c2 = st.columns(2)
    with c1:
        q = st.number_input("Q", min_value=0.0, value=float(base_entry.q or 0.0), step=0.01, key="c4c_q")
    with c2:
        s = st.number_input("S", min_value=0.0, value=float(base_entry.s or 0.0), step=0.01, key="c4c_s")

    theoretical_salary = st.number_input(
        "Salaire brut moyen théorique",
        min_value=0.0,
        value=float(base_entry.gross or 0.0),
        step=0.01,
        key="c4c_theoretical_salary",
    )
    salary_frequency = st.selectbox(
        "Périodicité du salaire",
        ["par mois", "par heure", "par jour", "par semaine", "par trimestre", "par année"],
        key="c4c_salary_frequency",
    )

    exact_gross: Optional[float] = None
    quarter_label = ""
    quarter_rows: list[dict] = []

    if occupation_end:
        _, quarter_start, quarter_end, quarter_label = quarter_info(occupation_end)
        dmfa_accepted = st.radio(
            "La DmfA de ce trimestre est-elle déjà déclarée et acceptée ?",
            ["Oui", "Non"],
            index=1,
            horizontal=True,
            key="c4c_dmfa_accepted",
        )
        if dmfa_accepted == "Non":
            exact_gross = st.number_input(
                "Salaire brut exact du trimestre",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key="c4c_exact_gross",
            )
            qrow_start = max(quarter_start, occupation_start) if occupation_start else quarter_start
            qrow_end = min(quarter_end, occupation_end)
            quarter_rows = [{
                "start": qrow_start,
                "end": qrow_end,
                "interruption": st.checkbox("Interruption pendant le trimestre", key="c4c_qrow_interruption"),
                "q_diff": st.checkbox("Durée de travail différente de Q", key="c4c_qrow_qdiff"),
            }]

    vacation_type = st.radio("Vacances légales", ["Temps partiel", "Temps plein"], horizontal=True, key="c4c_vacation_type")
    vacation_amount = st.number_input(
        "Nombre d'heures (temps partiel) ou de jours (temps plein) de vacances rémunérées",
        min_value=0.0,
        value=0.0,
        step=0.5,
        key="c4c_vacation_amount",
    )
    public_regime = st.selectbox(
        "Régime de vacances - pouvoirs publics",
        ["Non applicable", "Secteur public", "Secteur privé"],
        key="c4c_public_regime",
    )
    holidays_text = st.text_input(
        "Jours fériés payés après la fin du contrat (séparés par des virgules, JJ/MM/AAAA)",
        key="c4c_holidays",
    )
    paid_holidays_after_end, holiday_errors = _parse_holiday_list(holidays_text)
    comp_rest_days = st.number_input(
        "Jours encore rémunérés après la fin pour repos compensatoire / heures supplémentaires",
        min_value=0.0,
        value=0.0,
        step=0.5,
        key="c4c_comp_rest",
    )

    st.subheader("5. Fin de l'occupation")
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
        notice_method = st.radio(
            "Notification du préavis",
            ["Lettre recommandée", "Exploit d'huissier"],
            horizontal=True,
            key="c4c_notice_method",
        )
        notice_sent_txt = _masked_date_input("Date d'envoi / notification", key="c4c_notice_sent")
        notice_sent, _ = _parse_user_date(notice_sent_txt)

    st.subheader("6. Indemnités et déclaration")
    indemnity_type, indemnity_start, indemnity_end, other_indemnity_name, other_indemnity_amount = _render_indemnity_block("c4c")
    remarks = st.text_area("Remarques", key="c4c_remarks")
    pact_generations = st.selectbox(
        "Pacte des générations",
        ["Non concerné / ne pas compléter", "Licenciement - cellule emploi créée", "Licenciement - pas de cellule emploi", "Pas un licenciement"],
        key="c4c_pact",
    )
    complementary_indemnity = st.radio(
        "Indemnité complémentaire sans cotisations salariales ONSS ?",
        ["Non", "Oui"],
        horizontal=True,
        key="c4c_compl_ind",
    )
    responsible_name = st.text_input("Nom du responsable / délégué qui signera le C4", key="c4c_responsible")
    declaration_date = st.date_input("Date de la déclaration", value=date.today(), format="DD/MM/YYYY", key="c4c_decl_date")

    errors: list[str] = []
    if e1:
        errors.append("Date de début de l'occupation manquante ou invalide.")
    if e2:
        errors.append("Date d'entrée en service manquante ou invalide.")
    if e3:
        errors.append("Date de fin de l'occupation manquante ou invalide.")
    if occupation_start and occupation_end and occupation_end < occupation_start:
        errors.append("La date de fin est antérieure à la date de début.")
    if not employee_name.strip():
        errors.append("Nom et prénom manquants.")
    if not niss.strip():
        errors.append("NISS manquant.")
    if holiday_errors:
        errors.append("Une ou plusieurs dates de jours fériés sont invalides.")
    if not responsible_name.strip():
        errors.append("Nom du responsable / délégué manquant.")

    for error in errors:
        st.warning(error)

    template_pdf, template_error = _template_bytes(TEMPLATE_C4_CLASSIQUE)
    if template_error:
        st.error(template_error)
        return
    if not _template_contains_version(template_pdf, EXPECTED_C4_CLASSIQUE_VERSION):
        st.error(
            "Le PDF assets/c4_classique_officiel.pdf ne correspond pas à la version attendue "
            f"({EXPECTED_C4_CLASSIQUE_VERSION})."
        )
        return
    if errors:
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

    pdf_bytes = generate_c4_classique_pdf(data, template_pdf)
    st.success("Le C4 classique est prêt à imprimer.")
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
    st.info(
        "Les situations ACS / APE / PART-APE / PTP utilisent le C4 classique. "
        "La fiche de paie sert à préremplir les données de rémunération."
    )

    st.subheader("2. Fiches de paie")
    uploaded_files = st.file_uploader(
        "Importer une ou plusieurs fiches de paie PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="c4_acs_payroll_files",
    )
    st.caption("Les PDF sont lus pour les calculs et ne sont pas enregistrés dans le dépôt GitHub.")

    if not uploaded_files:
        st.info("Importez au moins une fiche de paie PDF.")
        return

    entries, extraction_errors = extract_payroll_entries(uploaded_files)
    for error in extraction_errors:
        st.warning(error)
    if not entries:
        st.error("Aucune donnée exploitable n'a pu être extraite des fiches importées.")
        return

    _show_detected_entries(entries)

    entry_options = [_entry_label(e) for e in entries]
    entry_map = {_entry_label(e): e for e in entries}
    source_label = st.selectbox("Fiche de paie utilisée comme base", options=entry_options, key="c4_acs_source")
    source_entry = entry_map[source_label]

    # Synchronisation robuste du préremplissage ACS / APE.
    # Streamlit conserve les valeurs des widgets entre les reruns. Une ancienne
    # valeur vide pouvait donc rester affichée même si la fiche était bien lue.
    # La version ci-dessous force une seule resynchronisation après cette mise à
    # jour puis conserve les éventuelles corrections manuelles de l'utilisateur.
    source_signature = "|".join(
        [
            "acs_prefill_v2",
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

        # Force le recalcul de la rémunération proposée pour la nouvelle fiche.
        st.session_state.pop("c4_acs_use_auto_salary", None)
        st.session_state.pop("c4_acs_theoretical_salary_manual", None)

    st.subheader("3. Programme et fonction")
    programme_options = ["ACS", "APE", "PART-APE", "PTP"]
    detected_program = _detect_acs_program(source_entry)
    programme_signature = f"{source_signature}|{detected_program}"
    if st.session_state.get("_c4_acs_programme_signature") != programme_signature:
        st.session_state["_c4_acs_programme_signature"] = programme_signature
        if detected_program in programme_options:
            st.session_state["c4_acs_programme"] = detected_program
        elif "c4_acs_programme" not in st.session_state:
            st.session_state["c4_acs_programme"] = "APE"

    programme = st.selectbox("Type de programme", programme_options, key="c4_acs_programme")
    fonction_option = st.selectbox("Fonction", options=FONCTIONS_ACS_APE_OPTIONS, key="c4_acs_fonction")
    fonction_acs = _acs_ape_function_label(fonction_option)

    if fonction_acs == "Puériculteur(trice) PTP":
        st.info(
            "Puériculteur(trice) PTP : cette fonction requiert un titre requis ou suffisant "
            "et impose une charge horaire de 32/36e."
        )
        if programme != "PTP":
            st.warning("La fonction « Puériculteur(trice) PTP » doit être utilisée avec le programme PTP.")

    if programme == "PTP":
        employment_measure = "2"
        st.caption("Mesure de promotion de l'emploi : code 2 (PTP), complété automatiquement.")
    else:
        employment_measure = ""
        st.caption("Pour ACS / APE / PART-APE, le champ « mesure de promotion de l'emploi » reste vide.")

    st.subheader("4. Travailleur et employeur")
    col1, col2 = st.columns(2)
    with col1:
        employee_name = st.text_input("Nom et prénom", key="c4_acs_employee_name")
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
        fase, fase_record, establishment_name, establishment_address = _render_fase_block("c4_acs")

    st.info(
        "Pour ACS / APE / PART-APE / PTP, le C4 classique reprend automatiquement "
        f"le n° d'entreprise FWB {BCE_FWB_ACS_APE} et le n° ONSS employeur {ONSS_EMPLOYEUR_ACS_APE}."
    )

    employer_identity_mode = st.radio(
        "Identification de l'employeur réel",
        ["Utiliser l'établissement identifié par le FASE", "Encoder un pouvoir organisateur / autre employeur"],
        key="c4_acs_employer_identity_mode",
    )

    if employer_identity_mode == "Utiliser l'établissement identifié par le FASE":
        employer_name = establishment_name
        employer_address = establishment_address
        st.text_input("Nom / raison sociale de l'employeur", value=employer_name, disabled=True, key="c4_acs_employer_name_display")
        st.text_area("Adresse de l'employeur", value=employer_address, disabled=True, height=85, key="c4_acs_employer_address_display")
    else:
        employer_name = st.text_input("Nom / raison sociale de l'employeur réel", key="c4_acs_employer_name")
        employer_address = st.text_area("Adresse de l'employeur réel", key="c4_acs_employer_address", height=85)

    c1, c2 = st.columns(2)
    with c1:
        enterprise_number = BCE_FWB_ACS_APE
        st.text_input("N° unique d'entreprise (FWB)", value=enterprise_number, disabled=True, key="c4_acs_bce_display")
        employer_category = st.text_input("Catégorie employeur", key="c4_acs_employer_category")
    with c2:
        onss_number = ONSS_EMPLOYEUR_ACS_APE
        st.text_input("N° ONSS employeur", value=onss_number, disabled=True, key="c4_acs_onss_number_display")
        joint_committee = st.text_input("Commission paritaire", key="c4_acs_joint_committee")

    st.subheader("5. Données concernant l'occupation")
    c1, c2, c3 = st.columns(3)
    with c1:
        occupation_start_txt = _masked_date_input("Date de début de l'occupation", key="c4_acs_occ_start")
        service_start_txt = _masked_date_input("Date d'entrée en service", key="c4_acs_service_start")
    with c2:
        occupation_end_txt = _masked_date_input("Date de fin de l'occupation", key="c4_acs_occ_end")
        worker_code = st.text_input("Code travailleur (3 chiffres)", max_chars=3, key="c4_acs_worker_code")
    with c3:
        home_worker = st.checkbox(
            "Travailleur à domicile",
            value=False,
            key="c4_acs_home_worker",
            help="Le statut D ne doit être indiqué que pour un travailleur à domicile.",
        )
        status = "D" if home_worker else ""
        st.text_input("Statut à reporter", value=status, disabled=True, key="c4_acs_status_display")
        st.text_input("Mesure de promotion de l'emploi", value=employment_measure, disabled=True, key="c4_acs_employment_measure_display")

    occupation_start, e1 = _parse_user_date(occupation_start_txt)
    service_start, e2 = _parse_user_date(service_start_txt)
    occupation_end, e3 = _parse_user_date(occupation_end_txt)

    detected_q = float(source_entry.q or 0.0)
    detected_s = float(source_entry.s or 0.0)
    default_regime = "Temps plein — 36/36"
    if abs(detected_q - 18.0) < 0.01 and abs(detected_s - 36.0) < 0.01:
        default_regime = "Mi-temps — 18/36"
    elif abs(detected_q - 32.0) < 0.01 and abs(detected_s - 36.0) < 0.01:
        default_regime = "4/5e temps — 32/36"

    if fonction_acs == "Puériculteur(trice) PTP":
        st.session_state["c4_acs_regime_horaire"] = "4/5e temps — 32/36"
    elif "c4_acs_regime_horaire" not in st.session_state:
        st.session_state["c4_acs_regime_horaire"] = default_regime

    regime_horaire = st.selectbox(
        "Charge horaire",
        options=list(REGIMES_HORAIRES_ACS_APE.keys()),
        key="c4_acs_regime_horaire",
        disabled=fonction_acs == "Puériculteur(trice) PTP",
    )
    q, s = REGIMES_HORAIRES_ACS_APE[regime_horaire]
    st.caption(f"Valeur reportée automatiquement sur le C4 : Q = {q:.2f} / S = {s:.2f}".replace(".", ","))

    onss_case = st.selectbox(
        "Cotisations ONSS - secteur chômage",
        ["Prélevées", "Non prélevées et non versées", "Non retenues mais seront versées", "Statutaire art. 9"],
        key="c4_acs_onss_case",
    )

    st.subheader("6. Rémunération")
    monthly_fr = reconstruct_monthly_fr(source_entry)
    calculated_theoretical = None
    if source_entry.annual_base_salary is not None and source_entry.pdf_index is not None and q > 0 and s > 0:
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
        st.metric("Index détecté", f"{source_entry.pdf_index:.4f}".replace(".", ",") if source_entry.pdf_index else "—")
    with c3:
        st.metric("Allocation F/R mensuelle", _format_money(monthly_fr))

    if calculated_theoretical is not None:
        st.success("Salaire brut moyen théorique calculé automatiquement : " f"{_format_money(calculated_theoretical)} / mois")
        st.caption("Calcul : TAB × Q/S × index ÷ 12 + allocation foyer/résidence éventuelle.")
    else:
        st.warning("Le TAB, l'index ou la fraction Q/S n'a pas pu être déterminé complètement. Encodez le salaire manuellement.")

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
    st.text_input("Périodicité", value="par mois", disabled=True, key="c4_acs_salary_frequency_display")

    # SALAIRE BRUT EXACT - RÈGLE DE TROIS
    exact_gross: Optional[float] = None
    quarter_label = ""
    quarter_rows: list[dict] = []

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
            if not occupation_start:
                st.warning("Indiquez la date de début de l'occupation pour calculer le salaire brut exact.")
            elif theoretical_salary <= 0:
                st.warning("Le salaire brut moyen théorique doit être déterminé avant le calcul.")
            else:
                exact_gross = _show_exact_gross_calculation(
                    theoretical_salary,
                    occupation_start,
                    occupation_end,
                    quarter_label,
                )

            qrow_start = max(quarter_start, occupation_start) if occupation_start else quarter_start
            qrow_end = min(quarter_end, occupation_end)
            quarter_rows = [
                {
                    "start": qrow_start,
                    "end": qrow_end,
                    "interruption": st.checkbox(
                        "Il y a eu une interruption à déclarer pendant ce trimestre",
                        value=False,
                        key="c4_acs_qrow_interruption",
                    ),
                    "q_diff": st.checkbox(
                        "La durée de travail diffère de Q pendant une partie du trimestre",
                        value=False,
                        key="c4_acs_qrow_qdiff",
                    ),
                }
            ]
        else:
            st.caption("Le salaire brut exact et la partie B ne sont pas complétés pour un trimestre déjà accepté.")
    else:
        st.caption("Complétez la date de fin pour déterminer le trimestre ONSS.")

    st.subheader("7. Vacances et jours encore rémunérés")
    default_vacation_type = "Temps plein" if abs(q - s) < 0.001 else "Temps partiel"
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

    regime_options_public = ["Non applicable", "Secteur public", "Secteur privé"]
    public_regime = st.selectbox(
        "Régime de vacances - pouvoirs publics",
        regime_options_public,
        index=regime_options_public.index(public_default),
        key="c4_acs_public_regime",
    )

    holidays_text = st.text_input(
        "Jours fériés payés après la fin du contrat (séparés par des virgules, JJ/MM/AAAA)",
        key="c4_acs_holidays",
    )
    paid_holidays_after_end, holiday_errors = _parse_holiday_list(holidays_text)

    comp_rest_days = st.number_input(
        "Jours encore rémunérés après la fin pour repos compensatoire / heures supplémentaires",
        min_value=0.0,
        value=0.0,
        step=0.5,
        key="c4_acs_comp_rest",
    )

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
    precise_reason = st.text_area("Motif précis du chômage (si requis)", key="c4_acs_precise_reason")

    notice_method = "Lettre recommandée"
    notice_sent = None
    if end_reason == "Préavis par l'employeur":
        notice_method = st.radio(
            "Notification du préavis",
            ["Lettre recommandée", "Exploit d'huissier"],
            horizontal=True,
            key="c4_acs_notice_method",
        )
        notice_sent_txt = _masked_date_input("Date d'envoi / notification", key="c4_acs_notice_sent")
        notice_sent, _ = _parse_user_date(notice_sent_txt)

    st.subheader("9. Indemnité liée à la fin")
    indemnity_type, indemnity_start, indemnity_end, other_indemnity_name, other_indemnity_amount = _render_indemnity_block("c4_acs")
    remarks = st.text_area("Remarques", key="c4_acs_remarks")

    st.subheader("10. C4 classique prêt à imprimer")
    pact_generations = st.selectbox(
        "Pacte des générations",
        ["Non concerné / ne pas compléter", "Licenciement - cellule emploi créée", "Licenciement - pas de cellule emploi", "Pas un licenciement"],
        key="c4_acs_pact",
    )
    complementary_indemnity = st.radio(
        "Indemnité complémentaire sans cotisations salariales ONSS ?",
        ["Non", "Oui"],
        horizontal=True,
        key="c4_acs_compl_ind",
    )
    responsible_name = st.text_input("Nom du responsable / délégué qui signera le C4", key="c4_acs_responsible")
    declaration_date = st.date_input("Date de la déclaration", value=date.today(), format="DD/MM/YYYY", key="c4_acs_decl_date")

    errors: list[str] = []
    if e1:
        errors.append("Date de début de l'occupation manquante ou invalide.")
    if e2:
        errors.append("Date d'entrée en service manquante ou invalide.")
    if e3:
        errors.append("Date de fin de l'occupation manquante ou invalide.")
    if occupation_start and occupation_end and occupation_end < occupation_start:
        errors.append("La date de fin est antérieure à la date de début.")
    if not employee_name.strip():
        errors.append("Nom et prénom manquants.")
    if not niss.strip():
        errors.append("NISS manquant.")
    elif len(re.sub(r"\D", "", niss)) != 11:
        errors.append("Le NISS doit contenir 11 chiffres.")
    if not employer_name.strip():
        errors.append("Employeur manquant.")
    if not employer_address.strip():
        errors.append("Adresse de l'employeur manquante.")
    if not worker_code.strip():
        errors.append("Code travailleur manquant.")
    if holiday_errors:
        errors.append("Une ou plusieurs dates de jours fériés sont invalides.")
    if not responsible_name.strip():
        errors.append("Nom du responsable / délégué manquant pour le PDF.")
    if programme == "PTP" and fonction_acs == "Puériculteur(trice) PTP" and (q, s) != (32.0, 36.0):
        errors.append("La fonction Puériculteur(trice) PTP doit être à 32/36e.")
    if occupation_end and st.session_state.get("c4_acs_dmfa_accepted") == "Non" and (exact_gross is None or exact_gross <= 0):
        errors.append("Salaire brut exact du trimestre impossible à calculer pour une DmfA non encore acceptée.")

    for error in errors:
        st.warning(error)

    template_pdf, template_error = _template_bytes(TEMPLATE_C4_CLASSIQUE)
    if template_error:
        st.error(template_error)
        return
    if not _template_contains_version(template_pdf, EXPECTED_C4_CLASSIQUE_VERSION):
        st.error(
            "Le PDF assets/c4_classique_officiel.pdf ne correspond pas à la version attendue "
            f"({EXPECTED_C4_CLASSIQUE_VERSION})."
        )
        return
    if errors:
        st.info("Corrigez les éléments ci-dessus avant de générer le C4 prêt à imprimer.")
        return

    data = {
        "fonction": fonction_acs,
        "programme": programme,
        "employer_identity_mode": employer_identity_mode,
        "employee_name": employee_name,
        "employee_address": employee_address,
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

    st.success(f"Le C4 classique {programme} est prêt à imprimer.")
    st.download_button(
        f"Télécharger le C4 {programme} prêt à imprimer",
        data=pdf_bytes,
        file_name=f"C4_{programme.replace('-', '_')}_complete.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# INTERFACE PRINCIPALE C4 ASSISTANT
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
        render_c4_classique_acs_ape()
        return

    if personnel_type != "Personnel enseignant / direction / auxiliaire d'éducation / paramédical payé par la FWB":
        st.info("Cette situation relève du C4 classique.")
        render_c4_classique_manuel()
        return

    # --------------------------------------------------------
    # C4-ENSEIGNEMENT
    # --------------------------------------------------------
    st.subheader("2. Fiches de paie")
    uploaded_files = st.file_uploader(
        "Importer une ou plusieurs fiches de paie PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="c4_payroll_files",
    )
    st.caption("Le module lit les PDF pour effectuer les calculs mais ne les enregistre pas dans le dépôt GitHub.")

    if not uploaded_files:
        st.info("Importez au moins une fiche de paie PDF.")
        return

    entries, extraction_errors = extract_payroll_entries(uploaded_files)
    for error in extraction_errors:
        st.warning(error)
    if not entries:
        st.error("Aucune donnée exploitable n'a pu être extraite.")
        return

    _show_detected_entries(entries)
    base_entry = entries[0]

    if "c4_employee_name" not in st.session_state:
        st.session_state["c4_employee_name"] = base_entry.employee_name
    if "c4_employee_address" not in st.session_state:
        st.session_state["c4_employee_address"] = base_entry.employee_address

    st.subheader("3. Identité et établissement")
    col1, col2 = st.columns(2)
    with col1:
        employee_name = st.text_input("Nom et prénom", key="c4_employee_name")
        niss = st.text_input("NISS", key="c4_niss", help="Le matricule de la fiche de paie n'est pas le NISS.")
        employee_address = st.text_area("Adresse du MDP", key="c4_employee_address", height=90)
    with col2:
        fase, fase_record, establishment_name, establishment_address = _render_fase_block("c4")

    st.subheader("4. Occupation(s) terminée(s)")
    occupation_count = int(st.number_input("Nombre d'occupations terminées à reprendre", min_value=1, max_value=3, value=1, step=1, key="c4_occ_count"))

    occupation_results: list[dict] = []
    global_errors: list[str] = []
    entry_options = [_entry_label(e) for e in entries]
    entry_map = {_entry_label(e): e for e in entries}

    for i in range(1, occupation_count + 1):
        st.markdown(f"### Occupation {i}")
        prefix = f"c4_occ_{i}"
        source_label = st.selectbox("Fiche de référence", entry_options, key=f"{prefix}_source")
        source = entry_map[source_label]

        c1, c2 = st.columns(2)
        with c1:
            function_options = ["— Sélectionner une fonction —"] + [_format_fonction_option(code) for code, _ in FONCTIONS_ENSEIGNEMENT]
            function_option = st.selectbox("Fonction", function_options, key=f"{prefix}_fonction")
            fonction = function_option.split(" — ", 1)[1] if " — " in function_option else ""
            status_index = _status_default_index(source.status)
            statut = st.selectbox(
                "Statut",
                ["Temporaire", "Définitif / statutaire", "Convention premier emploi", "Autre"],
                index=status_index,
                key=f"{prefix}_statut",
            )
        with c2:
            start_txt = _masked_date_input("Date de début", key=f"{prefix}_start")
            end_txt = _masked_date_input("Date de fin", key=f"{prefix}_end")

        start_date, start_err = _parse_user_date(start_txt)
        end_date, end_err = _parse_user_date(end_txt)
        if start_err:
            global_errors.append(f"Occupation {i} — date de début manquante ou invalide.")
        if end_err:
            global_errors.append(f"Occupation {i} — date de fin manquante ou invalide.")
        if start_date and end_date and end_date < start_date:
            global_errors.append(f"Occupation {i} — date de fin antérieure à la date de début.")
        if not fonction:
            global_errors.append(f"Occupation {i} — fonction non sélectionnée.")

        c1, c2, c3 = st.columns(3)
        with c1:
            q = st.number_input("Q", min_value=0.0, value=float(source.q or 0.0), step=0.01, key=f"{prefix}_q")
        with c2:
            s = st.number_input("S", min_value=0.0, value=float(source.s or 0.0), step=0.01, key=f"{prefix}_s")
        with c3:
            mode_payment = st.selectbox("Mode de paiement", ["10", "12", "20"], key=f"{prefix}_mode_payment")

        tab = st.number_input("TAB annuel à 100 %", min_value=0.0, value=float(source.annual_base_salary or 0.0), step=0.01, key=f"{prefix}_tab")
        index_value = float(source.pdf_index or 0.0)
        monthly_fr = reconstruct_monthly_fr(source)
        salary_monthly = calculate_monthly_indexed_salary(tab, q, s, index_value, monthly_fr) if tab > 0 and q > 0 and s > 0 and index_value > 0 else None

        if salary_monthly is not None:
            st.success(f"Salaire mensuel brut indexé : **{_format_money(salary_monthly)}**")
        else:
            global_errors.append(f"Occupation {i} — salaire mensuel impossible à calculer (TAB, Q/S ou index manquant).")

        onss_text = st.selectbox(
            "Cotisations ONSS",
            [
                "ont été prélevées",
                "ont été prélevées du ... au ...",
                "n'ont pas été prélevées",
                "seront versées",
            ],
            key=f"{prefix}_onss",
        )

        exact_total = None
        quarter_label = ""
        dmfa_state = "Oui / déjà déclarée et acceptée"
        if end_date:
            _, _, _, quarter_label = quarter_info(end_date)
            dmfa_state = st.radio(
                f"Occupation {i} — DmfA du trimestre {quarter_label} déjà déclarée/acceptée ?",
                ["Oui / déjà déclarée et acceptée", "Non / le salaire brut exact doit être complété"],
                horizontal=True,
                key=f"{prefix}_dmfa_state",
            )
            if dmfa_state == "Non / le salaire brut exact doit être complété" and start_date and salary_monthly:
                exact_total = _show_exact_gross_calculation(salary_monthly, start_date, end_date, quarter_label)

        occupation_results.append(
            {
                "fonction": fonction,
                "statut": statut,
                "start_date": start_date,
                "end_date": end_date,
                "q": q,
                "s": s,
                "salary_monthly": salary_monthly,
                "mode_payment": mode_payment,
                "onss_text": onss_text,
                "quarter_label": quarter_label,
                "dmfa_state": dmfa_state,
                "exact_total": exact_total,
            }
        )
        st.divider()

    valid_end_dates = [o["end_date"] for o in occupation_results if o["end_date"]]
    final_end_date = max(valid_end_dates) if valid_end_dates else None

    st.subheader("5. Interruptions à mentionner")
    interruption_rows: list[dict] = []
    interruption_count = int(st.number_input("Nombre d'interruptions à mentionner", min_value=0, max_value=2, value=0, step=1, key="c4_interruption_count"))
    for i in range(1, interruption_count + 1):
        st.markdown(f"**Interruption {i}**")
        kind = st.selectbox("Type", ["Protection de la maternité", "Autre interruption"], key=f"c4_int_{i}_kind")
        c1, c2 = st.columns(2)
        with c1:
            a = _masked_date_input("Du", key=f"c4_int_{i}_start")
        with c2:
            b = _masked_date_input("Au", key=f"c4_int_{i}_end")
        da, _ = _parse_user_date(a)
        db, _ = _parse_user_date(b)
        nature = ""
        if kind == "Autre interruption":
            nature = st.text_input("Nature", key=f"c4_int_{i}_nature")
        interruption_rows.append({"kind": kind, "start": da, "end": db, "nature": nature})

    st.subheader("6. Fin de l'occupation et déclaration")
    end_reason = st.selectbox(
        "Façon dont l'occupation a pris fin",
        [
            "Fin de plein droit et sans préavis",
            "Le pouvoir organisateur a mis fin à l'occupation avec préavis",
            "Le pouvoir organisateur a mis fin à l'occupation sans préavis",
            "Le membre du personnel a quitté volontairement son emploi",
        ],
        key="c4_end_reason",
    )
    motif_chomage_pdf = st.text_area(
        "Motif du chômage",
        value=_default_unemployment_reason(end_reason),
        key="c4_motif_chomage",
    )

    rupture_indemnity = st.checkbox("Une indemnité de rupture a été payée", key="c4_rupture_indemnity")
    rupture_start = rupture_end = None
    if rupture_indemnity:
        c1, c2 = st.columns(2)
        with c1:
            rs = _masked_date_input("Indemnité de rupture - du", key="c4_rupture_start")
        with c2:
            re_ = _masked_date_input("Indemnité de rupture - au", key="c4_rupture_end")
        rupture_start, _ = _parse_user_date(rs)
        rupture_end, _ = _parse_user_date(re_)

    notice_method = "Lettre recommandée"
    notice_start = notice_end = notice_extended_until = None
    notice_suspended = False
    notice_suspension_reason = ""
    transition = False
    transition_start = transition_end = None

    if end_reason == "Le pouvoir organisateur a mis fin à l'occupation avec préavis":
        notice_method = st.radio("Notification du préavis", ["Lettre recommandée", "Exploit d'huissier"], horizontal=True, key="c4_notice_method")
        c1, c2 = st.columns(2)
        with c1:
            ns = _masked_date_input("Préavis - du", key="c4_notice_start")
        with c2:
            ne = _masked_date_input("Préavis - au", key="c4_notice_end")
        notice_start, _ = _parse_user_date(ns)
        notice_end, _ = _parse_user_date(ne)

        notice_suspended = st.checkbox("Le délai de préavis a été suspendu", key="c4_notice_suspended")
        if notice_suspended:
            notice_suspension_reason = st.selectbox("Cause de suspension", ["Maladie", "Vacances", "Autre"], key="c4_notice_susp_reason")
            if notice_suspension_reason == "Autre":
                notice_suspension_reason = st.text_input("Autre cause", key="c4_notice_susp_other")
            nx = _masked_date_input("Préavis prolongé jusqu'au", key="c4_notice_extended")
            notice_extended_until, _ = _parse_user_date(nx)

        transition = st.checkbox("Trajet de transition pendant le préavis", key="c4_transition")
        if transition:
            c1, c2 = st.columns(2)
            with c1:
                ts = _masked_date_input("Trajet de transition - du", key="c4_transition_start")
            with c2:
                te = _masked_date_input("Trajet de transition - au", key="c4_transition_end")
            transition_start, _ = _parse_user_date(ts)
            transition_end, _ = _parse_user_date(te)

    responsible_name = st.text_input("Nom du responsable / délégué qui signera le C4", key="c4_responsible")
    declaration_date = st.date_input("Date de la déclaration", value=date.today(), format="DD/MM/YYYY", key="c4_decl_date")

    if not employee_name.strip():
        global_errors.append("Nom du membre du personnel manquant.")
    if len(re.sub(r"\D", "", niss)) != 11:
        global_errors.append("Le NISS doit contenir 11 chiffres.")
    if not fase_record:
        global_errors.append("Établissement FASE non identifié.")
    if not responsible_name.strip():
        global_errors.append("Nom du responsable / délégué manquant pour le PDF.")
    if not final_end_date:
        global_errors.append("Aucune date de fin d'occupation valide.")

    template_pdf, template_error = _template_bytes(TEMPLATE_C4_ENSEIGNEMENT)
    if template_error:
        st.error(template_error)
        return
    if not _template_contains_version(template_pdf, EXPECTED_C4_ENSEIGNEMENT_VERSION):
        st.error(
            "Le PDF assets/c4_enseignement_officiel.pdf ne correspond pas à la version attendue "
            f"({EXPECTED_C4_ENSEIGNEMENT_VERSION})."
        )
        return

    global_errors = list(dict.fromkeys(global_errors))
    for error in global_errors:
        st.warning(error)
    if global_errors:
        st.info("Corrigez les éléments ci-dessus avant de générer le C4-Enseignement.")
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
        "Le C4-Enseignement est prêt à imprimer. La rubrique II destinée à l'enseignant reste vierge. "
        "La signature de l'employeur doit être apposée après impression."
    )
    st.download_button(
        "Télécharger le C4-Enseignement prêt à imprimer",
        data=c4_pdf,
        file_name="C4_enseignement_complete.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
