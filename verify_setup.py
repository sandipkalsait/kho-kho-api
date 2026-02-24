import os
import django
from datetime import date, time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kho_kho_project.settings')
django.setup()

from core.models import Tournament, Team, Player, Match, Inning, ScoreEvent
from core.utils.pdf_generator import generate_scoresheet_pdf

def run_verification():
    print("Starting verification...")

    # 1. Create Data
    print("Creating sample data...")
    tournament, _ = Tournament.objects.get_or_create(
        name="61st State Championship",
        defaults={
            "venue": "Shivaji Maharaj Sports Complex",
            "start_date": date(2025, 2, 20),
            "end_date": date(2025, 2, 25),
            "organizer": "MKKA"
        }
    )

    team_a, _ = Team.objects.get_or_create(name="Pune", defaults={"coach": "Shirin Godbole"})
    team_b, _ = Team.objects.get_or_create(name="Dharashiv", defaults={"coach": "Patil Abhijit"})

    # Create players for Team A
    p1 = Player.objects.create(name="Dahane Arthava", chest_number=1, team=team_a)
    p2 = Player.objects.create(name="Bangar Pratik", chest_number=2, team=team_a)

    # Create players for Team B
    p3 = Player.objects.create(name="Vasave Bharat", chest_number=1, team=team_b)

    match = Match.objects.create(
        tournament=tournament,
        match_number=37,
        date=date(2025, 2, 21),
        time=time(8, 45),
        team_a=team_a,
        team_b=team_b,
        toss_won_by=team_a,
        choice='DEFENCE'
    )

    # Inning 1
    inning1 = Inning.objects.create(
        match=match,
        inning_number=1,
        chasing_team=team_b,
        defending_team=team_a
    )

    # Score Event
    ScoreEvent.objects.create(
        inning=inning1,
        raider_player=p3,
        defender_player=p1,
        event_type="SIMPLE_TOUCH",
        points=1,
        symbol="S"
    )

    print("Sample data created successfully.")

    # 2. Test PDF Generation
    print("Testing PDF generation...")
    try:
        pdf_buffer = generate_scoresheet_pdf(match)
        with open("test_scoresheet.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        print("PDF generated successfully: test_scoresheet.pdf")
    except Exception as e:
        print(f"PDF Generation Failed: {e}")
        raise

    print("Verification Completed Successfully!")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"Error: {e}")
