"""
ROI (Region of Interest) configuration for Maharashtra Kho Kho Association Score Sheet.
Coordinates are normalized (0.0 to 1.0) as [y_min, x_min, y_max, x_max].

IMPORTANT: These coordinates must be manually calibrated based on your actual scoresheet.
Use the debug visualization (roi_debug.py) to verify field positions.
"""

ROI_LAYOUT = {
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

    # Officials Section - typically 68-80% height
    "officials": {
        "scorer":      [0.68, 0.52, 0.72, 0.95],   # Score keeper/Scorer
        "umpire":      [0.72, 0.52, 0.76, 0.95],   # Umpire
        "referee":     [0.76, 0.52, 0.80, 0.95],   # Referee
        "timekeeper":  [0.80, 0.52, 0.84, 0.95],   # Timekeeper
    }
}
