from typing import Any, Dict, List

from .ocr_validation import MISSING_VALUE


DUMMY_PLAYER_COUNT = 12


def _missing_players() -> List[Dict[str, Any]]:
    return [{"no": index + 1, "name": MISSING_VALUE} for index in range(DUMMY_PLAYER_COUNT)]


def _empty_players() -> List[Dict[str, Any]]:
    return [{"no": index + 1, "name": ""} for index in range(DUMMY_PLAYER_COUNT)]


def build_dummy_extraction_payload(reason: str = "OCR failed. Dummy record created for manual correction.") -> Dict[str, Any]:
    missing_fields = [
        "match_info.tournament",
        "match_info.venue",
        "match_info.date",
        "teams.team_a.name",
        "teams.team_b.name",
        "score.team_a_points",
        "score.team_b_points",
    ]

    return {
        "raw_ocr": {
            "match_info": {
                "tournament": "",
                "venue": "",
                "date": "",
                "time": "",
                "court_no": "",
                "match_no": "",
                "choice": "",
                "category": "",
                "gender": "",
            },
            "teams": {
                "team_a": {"name": "", "players": _empty_players()},
                "team_b": {"name": "", "players": _empty_players()},
            },
            "score": {
                "team_a_points": "",
                "team_b_points": "",
            },
            "officials": {
                "scorer": "",
                "umpire1": "",
                "umpire2": "",
                "post_umpire1": "",
                "post_umpire2": "",
                "referee": "",
                "dugout_official": "",
                "timekeeper": "",
            },
            "remarks": "",
            "_meta": {
                "source": "dummy",
                "ocr_failed": True,
                "ocr_error": reason,
            },
        },
        "extracted": {
            "match_info": {
                "tournament": MISSING_VALUE,
                "venue": MISSING_VALUE,
                "date": MISSING_VALUE,
                "time": "",
                "court_no": "",
                "match_no": "",
                "choice": "",
                "category": "",
                "gender": "",
            },
            "teams": {
                "team_a": {"name": MISSING_VALUE, "players": _missing_players()},
                "team_b": {"name": MISSING_VALUE, "players": _missing_players()},
            },
            "score": {
                "team_a_points": MISSING_VALUE,
                "team_b_points": MISSING_VALUE,
            },
            "officials": {
                "scorer": "",
                "umpire1": "",
                "umpire2": "",
                "post_umpire1": "",
                "post_umpire2": "",
                "referee": "",
                "dugout_official": "",
                "timekeeper": "",
            },
            "remarks": reason,
        },
        "missing_fields": missing_fields,
        "confidence": 0.0,
        "confidence_summary": 0.0,
        "ocr_provider": "dummy",
        "used_dummy_data": True,
        "ocr_error": reason,
    }
