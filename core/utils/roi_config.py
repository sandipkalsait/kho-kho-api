"""
ROI (Region of Interest) configuration for Maharashtra Kho Kho Association Score Sheet.
Coordinates are normalized (0.0 to 1.0) as [y_min, x_min, y_max, x_max].

IMPORTANT: These coordinates must be manually calibrated based on your actual scoresheet.
Use the debug visualization (roi_debug.py) to verify field positions.
"""

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
    # Header Section - Top of the form (typically 5-15% of page height)
    "tournament": [0.02, 0.25, 0.06, 0.95],    # Tournament name - usually centered top area
    "venue":      [0.06, 0.25, 0.10, 0.95],     # Venue - below tournament
    
    # Match Details Row - typically 10-16% height
    "date":       [0.10, 0.25, 0.14, 0.42],     # Date field
    "time":       [0.10, 0.42, 0.14, 0.58],     # Time field  
    "court_no":   [0.10, 0.58, 0.14, 0.75],     # Court number
    "match_no":   [0.10, 0.75, 0.14, 0.92],     # Match number
    
    # Second Details Row - typically 14-20% height
    "section":    [0.14, 0.25, 0.18, 0.42],     # Section (Group/Category)
    "group":      [0.14, 0.42, 0.18, 0.58],     # Group/Pool
    "toss_won":   [0.14, 0.58, 0.18, 0.75],     # Toss won by
    "choice":     [0.14, 0.75, 0.18, 0.92],     # Choice (bat/field)

    # --- Team Names ---
    "team_names": {
        "team_a": [0.155, 0.04, 0.185, 0.48],
        "team_b": [0.155, 0.52, 0.185, 0.96],
    },

    # --- Player Lists (15 rows) ---
    "players": {
        "team_a": [0.20, 0.04, 0.81, 0.48],
        "team_b": [0.20, 0.52, 0.81, 0.96],
    # Team Headers - typically 18-22% height
    "team_a_name": [0.18, 0.10, 0.22, 0.48],    # Team A Name - left column
    "team_b_name": [0.18, 0.52, 0.22, 0.90],    # Team B Name - right column

    # Player Tables (main section - typically 22-75% height)
    # Team A players on left, Team B on right with separate columns
    "team_a_players": [0.22, 0.05, 0.70, 0.48],    # Total area for Team A player table
    "team_b_players": [0.22, 0.52, 0.70, 0.95],    # Total area for Team B player table

    # Staff/Officials Section - typically 70-80% height
    "team_a_staff": {
        "coach":     [0.70, 0.05, 0.74, 0.48],   # Team A Coach
        "manager":   [0.74, 0.05, 0.78, 0.48],   # Team A Manager
        "staff":     [0.78, 0.05, 0.82, 0.48],   # Team A Staff
    },

    # --- Scores (Large digits usually) ---
    "scores": {
        "team_a": [0.84, 0.04, 0.91, 0.25],
        "team_b": [0.84, 0.52, 0.91, 0.72],
    },
    "team_b_staff": {
        "coach":     [0.70, 0.52, 0.74, 0.95],   # Team B Coach
        "manager":   [0.74, 0.52, 0.78, 0.95],   # Team B Manager
        "staff":     [0.78, 0.52, 0.82, 0.95],   # Team B Staff
    },

    # Scores Section - typically 82-88% height
    "points_team_a": [0.82, 0.25, 0.86, 0.42],  # Team A Total Points
    "points_team_b": [0.82, 0.58, 0.86, 0.75],  # Team B Total Points
    
    # Remarks/Notes - typically 88-95% height
    "remarks":       [0.88, 0.10, 0.96, 0.90],   # Remarks/Comments section
    "final_result":  [0.82, 0.10, 0.88, 0.22],   # Final Result/Winner

    # --- Officials ---
    # Officials Section - typically 68-80% height
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
        "scorer":      [0.68, 0.52, 0.72, 0.95],   # Score keeper/Scorer
        "umpire":      [0.72, 0.52, 0.76, 0.95],   # Umpire
        "referee":     [0.76, 0.52, 0.80, 0.95],   # Referee
        "timekeeper":  [0.80, 0.52, 0.84, 0.95],   # Timekeeper
    }
}
