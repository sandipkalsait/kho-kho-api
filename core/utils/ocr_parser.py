import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ocr.parser")

def parse_kho_kho_sheet(raw_text: str) -> Dict[str, Any]:
    """Uses regex and heuristics to structure the match sheet."""
    logger.info("Starting sheet parsing. Text length: %d chars", len(raw_text))
    data: Dict[str, Any] = {
        "tournament": "",
        "date": "",
        "venue": "",
        "teamA": "",
        "teamB": "",
        "matchNumber": "",
        "finalResult": "",
        "players": [],
        "autoFilledFields": [],
        "scores": {
            "teamA": 0,
            "teamB": 0
        }
    }
    
    # ── 1. Match Date ──────────────────────────────────────────────────────────
    date_match = re.search(r'DATE\s*[:]\s*(\d{2,4}[/\-]\d{1,2}[/\-]\d{2,4})', raw_text, re.IGNORECASE)
    if date_match:
        data["date"] = date_match.group(1).split(',')[0].strip()

    # ── 2. Teams ──────────────────────────────────────────────────────────────
    team_a_match = re.search(r'TEAM\s*A\s*[:]\s*([A-Za-z\s]+)', raw_text, re.IGNORECASE)
    team_b_match = re.search(r'TEAM\s*B\s*[:]\s*([A-Za-z\s]+)', raw_text, re.IGNORECASE)
    
    if team_a_match:
        data["teamA"] = team_a_match.group(1).splitlines()[0].strip()
    if team_b_match:
        data["teamB"] = team_b_match.group(1).splitlines()[0].strip()

    # ── 3. Players ────────────────────────────────────────────────────────────
    player_rows = re.findall(r'(\d{1,2})\s+([A-Z\s,]{4,})', raw_text)
    for p_num, p_name in player_rows:
        if 1 <= int(p_num) <= 30:
            data["players"].append({
                "number": p_num,
                "name": p_name.strip(),
                "confidence": 0.8
            })

    # ── 4. Venue ──────────────────────────────────────────────────────────────
    venue_match = re.search(r'VENUE\s*[:]\s*([^\n]+)', raw_text, re.IGNORECASE)
    if venue_match:
        data["venue"] = venue_match.group(1).strip()

    # ── 5. Tournament ─────────────────────────────────────────────────────────
    tourn_match = re.search(r'TOURNAMENT\s*[:]\s*([^\n]+)', raw_text, re.IGNORECASE)
    if tourn_match:
        data["tournament"] = tourn_match.group(1).strip()

    # ── 6. Scores ─────────────────────────────────────────────────────────────
    scores = re.findall(r'TOTAL\s*[:]?\s*(\d+)', raw_text, re.IGNORECASE)
    if len(scores) >= 2:
        try:
            data["scores"]["teamA"] = int(scores[0])
            data["scores"]["teamB"] = int(scores[1])
        except (ValueError, IndexError):
            pass

    # ── 7. Result ─────────────────────────────────────────────────────────────
    result_match = re.search(r'RESULT\s*[:]\s*([^\n]+)', raw_text, re.IGNORECASE)
    if result_match:
        data["finalResult"] = result_match.group(1).strip()

    return data

def find_missing_fields(parsed_data: Dict[str, Any], required_fields: List[str] = None) -> List[str]:
    """Validates the structure and returns missing keys."""
    if required_fields is None:
        required_fields = ["teamA", "teamB", "date", "venue"]
        
    missing: List[str] = []
    for field in required_fields:
        if not parsed_data.get(field):
            missing.append(field)
            
    return missing
