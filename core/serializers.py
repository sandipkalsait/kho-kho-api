from rest_framework import serializers
from .models import Tournament, Team, Player, Match, Inning, ScoreEvent

class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = '__all__'

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = '__all__'

class TeamSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = '__all__'

class ScoreEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreEvent
        fields = '__all__'


class InningSerializer(serializers.ModelSerializer):
    score_events = ScoreEventSerializer(many=True, read_only=True)

    class Meta:
        model = Inning
        fields = '__all__'

class MatchSerializer(serializers.ModelSerializer):
    innings = InningSerializer(many=True, read_only=True)
    tournament_details = TournamentSerializer(source='tournament', read_only=True)
    team_a_details = TeamSerializer(source='team_a', read_only=True)
    team_b_details = TeamSerializer(source='team_b', read_only=True)

    class Meta:
        model = Match
        fields = '__all__'

class MatchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = '__all__'


