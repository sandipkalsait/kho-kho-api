"""
ROI (Region of Interest) configuration for Maharashtra Kho Kho Association Score Sheet.
Coordinates are normalized (0.0 to 1.0) as [y_min, x_min, y_max, x_max].
"""

ROI_LAYOUT = {
    # Match Metadata
    "tournament": [0.03, 0.20, 0.08, 0.85],
    "venue":      [0.08, 0.20, 0.10, 0.85],
    "date":       [0.10, 0.20, 0.13, 0.35],
    "time":       [0.10, 0.35, 0.13, 0.45],
    "court_no":   [0.10, 0.45, 0.13, 0.55],
    "match_no":   [0.10, 0.55, 0.13, 0.65],
    "section":    [0.13, 0.20, 0.15, 0.40],
    "group":      [0.13, 0.40, 0.15, 0.55],
    "toss_won":   [0.13, 0.55, 0.15, 0.70],
    "choice":     [0.13, 0.70, 0.15, 0.90],

    # Team Headers
    "team_a_name": [0.15, 0.05, 0.18, 0.48],
    "team_b_name": [0.15, 0.52, 0.18, 0.95],

    # Player Tables (Rows 1-15)
    # Team A players are on the left [x: 0.05 to 0.25]
    # Team B players are on the right [x: 0.52 to 0.72]
    "team_a_players": [0.20, 0.05, 0.55, 0.25], 
    "team_b_players": [0.20, 0.52, 0.55, 0.72],

    # Staff
    "team_a_staff": {
        "coach":   [0.55, 0.05, 0.58, 0.25],
        "manager": [0.58, 0.05, 0.61, 0.25],
        "staff":   [0.61, 0.05, 0.64, 0.25],
    },
    "team_b_staff": {
        "coach":   [0.55, 0.52, 0.58, 0.72],
        "manager": [0.58, 0.52, 0.61, 0.72],
        "staff":   [0.61, 0.52, 0.64, 0.72],
    },

    # Scores and Result
    "points_team_a": [0.85, 0.05, 0.90, 0.25],
    "points_team_b": [0.85, 0.52, 0.90, 0.72],
    "remarks":       [0.85, 0.30, 0.95, 0.50],
    "final_result":  [0.96, 0.05, 0.99, 0.50],

    # Officials
    "officials": {
        "scorer":   [0.85, 0.52, 0.88, 0.68],
        "umpire":   [0.85, 0.68, 0.88, 0.84],
        "referee":  [0.92, 0.84, 0.95, 0.99],
        "timekeeper": [0.92, 0.68, 0.95, 0.84],
    }
}
