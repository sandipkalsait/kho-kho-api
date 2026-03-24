ROI_LAYOUT = {
    # --- Match Info Header ---
    "match_info": {
        "tournament": [0.025, 0.22, 0.075, 0.75],
        "venue":      [0.075, 0.22, 0.100, 0.75],
        "date":       [0.105, 0.22, 0.132, 0.33],
        "time":       [0.105, 0.33, 0.132, 0.44],
        "court_no":   [0.105, 0.44, 0.132, 0.55],
        "match_no":   [0.105, 0.55, 0.132, 0.66],
        "league":     [0.135, 0.35, 0.155, 0.55],
        "toss_won":   [0.135, 0.55, 0.155, 0.75],
        "choice":     [0.135, 0.75, 0.155, 0.92],
    },

    # --- Team Names ---
    "team_names": {
        "team_a": [0.155, 0.04, 0.185, 0.48],
        "team_b": [0.155, 0.52, 0.185, 0.96],
    },

    # --- Player Lists (15 rows) ---
    "players": {
        "team_a": [0.20, 0.04, 0.81, 0.48],
        "team_b": [0.20, 0.52, 0.81, 0.96],
    },

    # --- Scores (Large digits usually) ---
    "scores": {
        "team_a": [0.84, 0.04, 0.91, 0.25],
        "team_b": [0.84, 0.52, 0.91, 0.72],
    },

    # --- Officials ---
    "officials": {
        "scorer":      [0.84, 0.52, 0.88, 0.68],
        "umpire1":     [0.84, 0.68, 0.88, 0.85],
        "referee":     [0.91, 0.84, 0.95, 0.99],
        "timekeeper":  [0.91, 0.68, 0.95, 0.84],
    },

    # --- Misc ---
    "remarks": [0.84, 0.28, 0.95, 0.51],
}

# Strict validation types
# used by template_extractor to reject noise
VALIDATION_RULES = {
    "numeric": ["court_no", "match_no", "team_a_points", "team_b_points", "no"],
    "name":    ["team_a", "team_b", "scorer", "umpire1", "referee", "timekeeper", "player_name", "tournament", "venue"],
    "date":    ["date", "time"],
}
