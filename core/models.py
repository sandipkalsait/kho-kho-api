from django.db import models

class Tournament(models.Model):
    name = models.CharField(max_length=255)
    venue = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    organizer = models.CharField(max_length=255, help_text="e.g., Maharashtra Kho Kho Association")

    def __str__(self):
        return self.name

class Team(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255, blank=True, null=True)
    coach = models.CharField(max_length=255, blank=True, null=True)
    manager = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class Player(models.Model):
    name = models.CharField(max_length=255)
    chest_number = models.IntegerField()
    team = models.ForeignKey(Team, related_name='players', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.chest_number})"

class Match(models.Model):
    DEFENCE = 'DEFENCE'
    CHASE = 'CHASE'
    CHOICE_CHOICES = [
        (DEFENCE, 'Defence'),
        (CHASE, 'Chase'),
    ]

    tournament = models.ForeignKey(Tournament, related_name='matches', on_delete=models.CASCADE)
    match_number = models.IntegerField()
    court_number = models.CharField(max_length=50, blank=True, null=True)
    date = models.DateField()
    time = models.TimeField()
    team_a = models.ForeignKey(Team, related_name='matches_as_team_a', on_delete=models.CASCADE)
    team_b = models.ForeignKey(Team, related_name='matches_as_team_b', on_delete=models.CASCADE)
    toss_won_by = models.ForeignKey(Team, related_name='matches_toss_won', on_delete=models.SET_NULL, null=True, blank=True)
    choice = models.CharField(max_length=10, choices=CHOICE_CHOICES, blank=True, null=True)
    winner = models.ForeignKey(Team, related_name='matches_won', on_delete=models.SET_NULL, null=True, blank=True)
    result_margin = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    officials = models.JSONField(default=dict, blank=True, help_text="Scorer, Umpires, Referee, Timekeeper")

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.team_a == self.team_b:
            raise ValidationError("Team A and Team B must be different.")
        if self.toss_won_by and self.toss_won_by not in [self.team_a, self.team_b]:
            raise ValidationError("Toss winner must be one of the participating teams.")
        if self.winner and self.winner not in [self.team_a, self.team_b]:
            raise ValidationError("Winner must be one of the participating teams.")

    def __str__(self):
        return f"Match {self.match_number}: {self.team_a} vs {self.team_b}"

class Inning(models.Model):
    match = models.ForeignKey(Match, related_name='innings', on_delete=models.CASCADE)
    inning_number = models.IntegerField(help_text="1, 2, 3, 4")
    chasing_team = models.ForeignKey(Team, related_name='innings_chasing', on_delete=models.CASCADE)
    defending_team = models.ForeignKey(Team, related_name='innings_defending', on_delete=models.CASCADE)

    def __str__(self):
        return f"Match {self.match.match_number} - Inning {self.inning_number}"

class ScoreEvent(models.Model):
    inning = models.ForeignKey(Inning, related_name='score_events', on_delete=models.CASCADE)
    raider_player = models.ForeignKey(Player, related_name='score_events_as_raider', on_delete=models.SET_NULL, null=True, blank=True)
    defender_player = models.ForeignKey(Player, related_name='score_events_as_defender', on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50, help_text="e.g., SIMPLE_TOUCH, DIVE, LATE_ENTRY")
    points = models.IntegerField(default=0)
    timestamp = models.TimeField(null=True, blank=True, help_text="Run time")
    symbol = models.CharField(max_length=10, blank=True, null=True, help_text="S, L, O, etc.")

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.raider_player and self.defender_player:
            if self.raider_player.team == self.defender_player.team:
                raise ValidationError("Raider and Defender must be from different teams.")
            
            match_teams = [self.inning.match.team_a, self.inning.match.team_b]
            if self.raider_player.team not in match_teams:
                raise ValidationError(f"Raider player {self.raider_player.name} is not in the match teams.")
            if self.defender_player.team not in match_teams:
                raise ValidationError(f"Defender player {self.defender_player.name} is not in the match teams.")

    def __str__(self):
        return f"{self.event_type} - {self.points} pts"
