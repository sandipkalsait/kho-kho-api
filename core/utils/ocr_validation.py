import re
from typing import Optional

MISSING_VALUE = "__MISSING__"

NUMERIC_FIELDS = {
    "court_no",
    "match_no",
    "team_a_points",
    "team_b_points",
}

NAME_FIELDS = {
    "team_a",
    "team_b",
    "scorer",
    "umpire1",
    "referee",
    "timekeeper",
    "player_name",
}

DATE_FIELDS = {"date"}
TIME_FIELDS = {"time"}
TEXT_FIELDS = {"tournament", "venue", "league", "toss_won", "choice", "remarks"}

NUMERIC_RE = re.compile(r"^\d+$")
DATE_RE = re.compile(r"^(?:\d{1,2}[-/.]){2}\d{2,4}$|^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$")
TIME_RE = re.compile(r"^\d{1,2}[:.]\d{2}(?::\d{2})?$")
WHITESPACE_RE = re.compile(r"\s+")
NAME_CLEAN_RE = re.compile(r"[^A-Za-z\s]")
TEXT_CLEAN_RE = re.compile(r"[^A-Za-z0-9\s,./()&'-]")
ALPHA_RE = re.compile(r"[A-Za-z]")
ALNUM_RE = re.compile(r"[A-Za-z0-9]")


def normalize_whitespace(value: Optional[str]) -> str:
    return WHITESPACE_RE.sub(" ", str(value or "")).strip()


def is_missing(value: object) -> bool:
    return value in (None, "", MISSING_VALUE)


def normalize_field(field_name: str, raw_text: Optional[str], placeholder: str = MISSING_VALUE) -> str:
    raw_value = normalize_whitespace(raw_text)
    if not raw_value:
        return placeholder

    if field_name in NUMERIC_FIELDS:
        candidate = raw_value.replace(" ", "")
        return candidate if NUMERIC_RE.fullmatch(candidate) else placeholder

    if field_name in NAME_FIELDS:
        candidate = normalize_whitespace(NAME_CLEAN_RE.sub("", raw_value))
        return candidate if len(ALPHA_RE.findall(candidate)) >= 3 else placeholder

    if field_name in DATE_FIELDS:
        candidate = raw_value.replace(" ", "")
        return candidate if DATE_RE.fullmatch(candidate) else placeholder

    if field_name in TIME_FIELDS:
        candidate = raw_value.replace(" ", "")
        return candidate if TIME_RE.fullmatch(candidate) else placeholder

    candidate = normalize_whitespace(TEXT_CLEAN_RE.sub("", raw_value))
    if field_name in TEXT_FIELDS:
        return candidate if len(ALNUM_RE.findall(candidate)) >= 2 else placeholder

    return candidate if len(ALNUM_RE.findall(candidate)) >= 2 else placeholder


def calculate_confidence(valid_fields: int, total_fields: int) -> float:
    if total_fields <= 0:
        return 0.0
    return round((valid_fields / total_fields) * 100.0, 2)
