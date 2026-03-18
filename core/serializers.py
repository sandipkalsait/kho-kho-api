from rest_framework import serializers
from .models import Tournament, Team, Player, MatchDetails, MatchStaff, MatchResult, ExtraPoints, RunningBatch, Substitution, Chase, Defence, ScoreCard

class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = '__all__'

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = '__all__'

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'coach', 'manager', 'supporting_staff']

class BatchesSerializer(serializers.Serializer):
    team_a = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField(), min_length=3, max_length=3),
        required=False, default=list
    )
    team_b = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField(), min_length=3, max_length=3),
        required=False, default=list
    )

class MatchDetailsSerializer(serializers.ModelSerializer):
    batches = BatchesSerializer(required=False)

    class Meta:
        model = MatchDetails
        fields = ['id', 'tournamentId', 'team_A_id', 'teamB_id', 'match_no', 'date', 'time', 'court_no', 'type', 'session', 'section', 'category', 'group', 'toss_winner', 'choice', 'batches']

    def validate(self, data):
        instance = MatchDetails(**data)
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        return data

class MatchDetailsResponseSerializer(serializers.Serializer):
    match_details = MatchDetailsSerializer(source='*')

class MatchStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchStaff
        fields = [
            'id', 'match_id', 'scorer_1', 'scorer_2', 'umpire_1', 'umpire_2',
            'post_umpire_1', 'post_umpire_2', 'dugout', 'timekeeper', 'referee'
        ]

class MatchStaffResponseSerializer(serializers.Serializer):
    match_staff = MatchStaffSerializer(source='*')

class TeamResultSerializer(serializers.Serializer):
    I = serializers.ListField(
        child=serializers.RegexField(regex=r'^(\d+|-)$'),
        min_length=2, max_length=2, required=False
    )
    II = serializers.ListField(
        child=serializers.RegexField(regex=r'^(\d+|-)$'),
        min_length=2, max_length=2, required=False
    )
    III = serializers.ListField(
        child=serializers.RegexField(regex=r'^(\d+|-)$'),
        min_length=2, max_length=2, required=False
    )
    IV = serializers.RegexField(regex=r'^(\d+|-)$', required=False)

class MatchResultSerializer(serializers.ModelSerializer):
    won_by = serializers.CharField(read_only=True)
    team_won = serializers.CharField(read_only=True)
    team_A = TeamResultSerializer(required=False)
    team_B = TeamResultSerializer(required=False)

    class Meta:
        model = MatchResult
        fields = ['id', 'match_id', 'team_a_total', 'team_b_total', 'won_by', 'team_won', 'team_A', 'team_B']
        
    def validate(self, data):
        instance = MatchResult(**data)
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        return data

class MatchResultResponseSerializer(serializers.Serializer):
    result = MatchResultSerializer(source='*')

class ExtraPointsCategorySerializer(serializers.Serializer):
    late_entry = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    out_of_field = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    warning = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    dream_run = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

class ExtraPointsSerializer(serializers.ModelSerializer):
    Team_A = ExtraPointsCategorySerializer(required=False)
    Team_B = ExtraPointsCategorySerializer(required=False)

    class Meta:
        model = ExtraPoints
        fields = ['id', 'match_id', 'Team_A', 'Team_B']
        read_only_fields = ['id']

    def to_representation(self, instance):
        # Wraps the response in "Extra_Points" as requested in the root key instructions if needed,
        # but the View code returns {"extra_points": serializer.data}
        # To match the exact "Extra_Points" root key case:
        return {
            "id": instance.id,
            "match_id": instance.match_id,
            "Team_A": instance.Team_A,
            "Team_B": instance.Team_B
        }

    def validate(self, data):
        instance = ExtraPoints(**data)
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        return data

class RunningBatchTurnSerializer(serializers.Serializer):
    turn_I = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()), required=False, default=list)
    turn_II = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()), required=False, default=list)
    turn_III = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()), required=False, default=list)
    turn_IV = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()), required=False, default=list)

class RunningBatchSerializer(serializers.ModelSerializer):
    Team_A = RunningBatchTurnSerializer(required=False)
    Team_B = RunningBatchTurnSerializer(required=False)

    class Meta:
        model = RunningBatch
        fields = ['id', 'match_id', 'Team_A', 'Team_B']
        read_only_fields = ['id']

    def to_representation(self, instance):
        return {
            "id": instance.id,
            "match_id": instance.match_id,
            "Team_A": instance.Team_A,
            "Team_B": instance.Team_B
        }

    def validate(self, data):
        instance = RunningBatch(**data)
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        return data

class SubstitutionPlayerSerializer(serializers.Serializer):
    player_in = serializers.IntegerField(required=True)
    player_out = serializers.IntegerField(required=True)

class SubstitutionsDictSerializer(serializers.Serializer):
    TeamA = serializers.ListField(child=SubstitutionPlayerSerializer(), required=False, default=list)
    TeamB = serializers.ListField(child=SubstitutionPlayerSerializer(), required=False, default=list)

class SubstitutionSerializer(serializers.ModelSerializer):
    Substitutions = SubstitutionsDictSerializer(required=False)

    class Meta:
        model = Substitution
        fields = ['id', 'match_id', 'Substitutions']

    def validate(self, data):
        instance = Substitution(**data)
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        return data

class ChasePhaseSerializer(serializers.Serializer):
    I = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    II = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    III = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    IV = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

class ChaseSerializer(serializers.ModelSerializer):
    Team_A = ChasePhaseSerializer(required=False)
    Team_B = ChasePhaseSerializer(required=False)

    class Meta:
        model = Chase
        fields = ['id', 'match_id', 'Team_A', 'Team_B']
        read_only_fields = ['id']

    def to_representation(self, instance):
        return {
            "id": instance.id,
            "match_id": instance.match_id,
            "Team_A": instance.Team_A,
            "Team_B": instance.Team_B
        }

    def validate(self, data):
        instance = Chase(**data)
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        return data

class DefencePhaseSerializer(serializers.Serializer):
    I = serializers.ListField(
        child=serializers.ListField(
            child=serializers.RegexField(regex=r'^(\d{2}:\d{2}|-)$'),
            min_length=15, max_length=15
        ),
        min_length=3, max_length=3, required=False, default=list
    )
    II = serializers.ListField(
        child=serializers.ListField(
            child=serializers.RegexField(regex=r'^(\d{2}:\d{2}|-)$'),
            min_length=15, max_length=15
        ),
        min_length=2, max_length=2, required=False, default=list
    )
    III = serializers.ListField(
        child=serializers.ListField(
            child=serializers.RegexField(regex=r'^(\d{2}:\d{2}|-)$'),
            min_length=15, max_length=15
        ),
        min_length=2, max_length=2, required=False, default=list
    )
    IV = serializers.ListField(
        child=serializers.RegexField(regex=r'^(\d{2}:\d{2}|-)$'),
        min_length=15, max_length=15, required=False, default=list
    )

class DefenceSerializer(serializers.ModelSerializer):
    Team_A = DefencePhaseSerializer(required=False)
    Team_B = DefencePhaseSerializer(required=False)

    class Meta:
        model = Defence
        fields = ['id', 'match_id', 'Team_A', 'Team_B']
        read_only_fields = ['id']

    def to_representation(self, instance):
        return {
            "id": instance.id,
            "match_id": instance.match_id,
            "Team_A": instance.Team_A,
            "Team_B": instance.Team_B
        }

    def validate(self, data):
        instance = Defence(**data)
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        return data

class ScoreCardEventSerializer(serializers.Serializer):
    defender = serializers.ListField(child=serializers.IntegerField(), required=True)
    attacker = serializers.ListField(child=serializers.IntegerField(), required=True)
    run_time = serializers.ListField(child=serializers.RegexField(regex=r'^\d{1,2}:\d{2}$'), required=True)
    per_time = serializers.ListField(child=serializers.RegexField(regex=r'^\d{1,2}:\d{2}$'), required=True)
    symbol = serializers.CharField(max_length=1, min_length=1, required=True)

class ScoreCardPeriodDictField(serializers.DictField):
    child = ScoreCardEventSerializer()

class ScoreCardSerializer(serializers.ModelSerializer):
    Team_A = ScoreCardPeriodDictField(required=False)
    Team_B = ScoreCardPeriodDictField(required=False)

    class Meta:
        model = ScoreCard
        fields = ['id', 'match_id', 'Team_A', 'Team_B']
        read_only_fields = ['id']

    def to_representation(self, instance):
        # We omit id from the output wrapper directly in the View if needed, or dict format here.
        # But to match EXACT output requested format dict: 
        # "Team_A": {...}, "Team_B": {...}
        return {
            "id": instance.id,
            "match_id": instance.match_id,
            "Team_A": instance.Team_A,
            "Team_B": instance.Team_B
        }

    def validate(self, data):
        instance = ScoreCard(**data)
        try:
            instance.clean()
        except Exception as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        return data
