import logging
from typing import Dict, Any, List, Optional
from .ocr_validation import MISSING_VALUE, is_missing

logger = logging.getLogger("ocr.parser")

def find_missing_fields(payload: Dict[str, Any], required_fields: Optional[List[str]] = None) -> List[str]:
    """
    Checks for __MISSING__ or empty values in the structured payload.
    Supports dotted path notation (e.g. 'match_info.date').
    """
    if required_fields is None:
        # Default production requirements
        required_fields = [
            "match_info.tournament", 
            "match_info.date", 
            "teams.team_a.name", 
            "teams.team_b.name"
        ]
        
    missing: List[str] = []
    for field_path in required_fields:
        parts = field_path.split('.')
        val = payload
        
        # Traverse the dictionary
        for part in parts:
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                val = MISSING_VALUE
                break
        
        # Check if value is truly missing
        if is_missing(val) or (isinstance(val, str) and not val.strip()):
            missing.append(field_path)
            
    return missing


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(base.get(key), value)
        return merged
    if override is None:
        return base
    return override


def diff_payload(base: Any, candidate: Any) -> Any:
    if isinstance(base, dict) and isinstance(candidate, dict):
        diff: Dict[str, Any] = {}
        for key, candidate_value in candidate.items():
            base_value = base.get(key)
            nested_diff = diff_payload(base_value, candidate_value)
            if nested_diff is not None:
                diff[key] = nested_diff
        return diff or None

    if isinstance(base, list) and isinstance(candidate, list):
        return candidate if candidate != base else None

    return candidate if candidate != base else None


def is_full_payload(payload: Dict[str, Any]) -> bool:
    return (
        isinstance(payload, dict)
        and "match_info" in payload
        and "teams" in payload
        and "score" in payload
    )

def normalize_payload_for_legacy(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Maps the new structured schema back to legacy keys if needed for older UI components."""
    return {
        "tournament": payload.get("match_info", {}).get("tournament"),
        "date":       payload.get("match_info", {}).get("date"),
        "venue":      payload.get("match_info", {}).get("venue"),
        "teamA":      payload.get("teams", {}).get("team_a", {}).get("name"),
        "teamB":      payload.get("teams", {}).get("team_b", {}).get("name"),
        "scores": {
            "teamA": payload.get("score", {}).get("team_a_points"),
            "teamB": payload.get("score", {}).get("team_b_points"),
        }
    }
