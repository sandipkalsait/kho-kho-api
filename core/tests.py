from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Tournament, Team, Player, Match, Inning, ScoreEvent
from datetime import date, time

class KhoKhoAPITests(APITestCase):

    def setUp(self):
        # Create helper data
        self.team_a = Team.objects.create(name="Pune", coach="Coach A")
        self.team_b = Team.objects.create(name="Mumbai", coach="Coach B")
        self.player_a1 = Player.objects.create(name="Player A1", chest_number=1, team=self.team_a)
        self.player_b1 = Player.objects.create(name="Player B1", chest_number=1, team=self.team_b)
        self.tournament = Tournament.objects.create(
            name="State Championship",
            venue="Pune",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 5),
            organizer="Association"
        )
        self.match = Match.objects.create(
            tournament=self.tournament,
            match_number=1,
            date=date(2025, 1, 2),
            time=time(10, 0),
            team_a=self.team_a,
            team_b=self.team_b,
            toss_won_by=self.team_a,
            choice='DEFENCE'
        )

    # --- Tournament Tests ---
    def test_create_tournament(self):
        url = reverse('tournament-list')
        data = {
            "name": "National Cup",
            "venue": "Delhi",
            "start_date": "2025-03-01",
            "end_date": "2025-03-10",
            "organizer": "National Fed"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tournament.objects.count(), 2)
        self.assertEqual(Tournament.objects.get(name="National Cup").venue, "Delhi")

    def test_get_tournaments(self):
        url = reverse('tournament-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    # --- Team Tests ---
    def test_create_team(self):
        url = reverse('team-list')
        data = {"name": "Nashik", "coach": "Coach C"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Team.objects.count(), 3)

    # --- Player Tests ---
    def test_create_player(self):
        url = reverse('player-list')
        data = {
            "name": "New Player",
            "chest_number": 10,
            "team": self.team_a.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Player.objects.count(), 3)
        self.assertEqual(Player.objects.get(name="New Player").team, self.team_a)

    # --- Match Tests ---
    def test_create_match(self):
        url = reverse('match-list')
        data = {
            "tournament": self.tournament.id,
            "match_number": 2,
            "court_number": "C1",
            "date": "2025-01-03",
            "time": "14:00:00",
            "team_a": self.team_a.id,
            "team_b": self.team_b.id,
            "toss_won_by": self.team_b.id,
            "choice": "CHASE"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Match.objects.count(), 2)

    def test_get_match_detail(self):
        """Test if match detail includes nested info like team names"""
        url = reverse('match-detail', args=[self.match.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['match_number'], 1)
        # Check nested serializers if implemented
        self.assertIn('team_a_details', response.data)
        self.assertEqual(response.data['team_a_details']['name'], "Pune")

    def test_update_match(self):
        url = reverse('match-detail', args=[self.match.id])
        data = {"winner": self.team_a.id, "result_margin": "2 points"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.match.refresh_from_db()
        self.assertEqual(self.match.winner, self.team_a)

    # --- Inning & ScoreEvent Tests ---
    def test_create_inning_and_score(self):
        # Create Inning
        inning_url = reverse('inning-list')
        inning_data = {
            "match": self.match.id,
            "inning_number": 1,
            "chasing_team": self.team_b.id, # B chases first
            "defending_team": self.team_a.id
        }
        resp_inn = self.client.post(inning_url, inning_data, format='json')
        self.assertEqual(resp_inn.status_code, status.HTTP_201_CREATED)
        inning_id = resp_inn.data['id']

        # Create Score Event
        score_url = reverse('scoreevent-list')
        score_data = {
            "inning": inning_id,
            "raider_player": self.player_b1.id,
            "defender_player": self.player_a1.id,
            "event_type": "POLE_DIVE",
            "points": 2,
            "timestamp": "10:05:00"
        }
        resp_score = self.client.post(score_url, score_data, format='json')
        self.assertEqual(resp_score.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ScoreEvent.objects.count(), 1)

    # --- Validation Tests ---
    def test_match_same_teams_fail(self):
        url = reverse('match-list')
        data = {
            "tournament": self.tournament.id,
            "match_number": 3,
            "date": "2025-01-03",
            "time": "14:00:00",
            "team_a": self.team_a.id,
            "team_b": self.team_a.id,  # Same team
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_score_event_same_team_players_fail(self):
        # Create Inning
        inning = Inning.objects.create(
            match=self.match,
            inning_number=1,
            chasing_team=self.team_b,
            defending_team=self.team_a
        )
        
        # Create another player for team_b
        player_b2 = Player.objects.create(name="Player B2", chest_number=2, team=self.team_b)
        
        url = reverse('scoreevent-list')
        data = {
            "inning": inning.id,
            "raider_player": self.player_b1.id,
            "defender_player": player_b2.id, # Also from team B
            "event_type": "TOUCH",
            "points": 1
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    # --- PDF Download Test ---
    def test_download_scoresheet(self):
        url = reverse('match-download-scoresheet', args=[self.match.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(len(response.content) > 0)
