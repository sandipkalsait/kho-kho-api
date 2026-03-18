from django.db import models

class Tournament(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=255)
    venue = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Team(models.Model):
    name = models.CharField(max_length=255)
    coach = models.CharField(max_length=255, blank=True, null=True)
    manager = models.CharField(max_length=255, blank=True, null=True)
    supporting_staff = models.CharField(max_length=255, blank=True, default="", help_text="Supporting staff names/roles")

    def __str__(self):
        return self.name

class Player(models.Model):
    name = models.CharField(max_length=255)
    chest_number = models.IntegerField()
    team = models.ForeignKey(Team, related_name='players', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.chest_number})"


class MatchDetails(models.Model):
    tournamentId = models.IntegerField(null=True, blank=True)
    team_A_id = models.IntegerField(null=True, blank=True)
    teamB_id = models.IntegerField(null=True, blank=True)
    match_no = models.IntegerField()
    date = models.DateField()
    time = models.TimeField()
    court_no = models.IntegerField()
    type = models.CharField(max_length=100)
    session = models.CharField(max_length=100)
    section = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    group = models.CharField(max_length=100)
    toss_winner = models.CharField(max_length=100)
    choice = models.CharField(max_length=100)
    batches = models.JSONField(default=dict, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if not isinstance(self.batches, dict):
            raise ValidationError({'batches': "Must be a dictionary containing team_a and team_b arrays."})
        for team_key in ['team_a', 'team_b']:
            if team_key in self.batches:
                team_batches = self.batches[team_key]
                if not isinstance(team_batches, list):
                    raise ValidationError({'batches': f"{team_key} must be a list of batches."})
                for batch in team_batches:
                    if not isinstance(batch, list) or len(batch) != 3:
                        raise ValidationError({'batches': f"Each batch in {team_key} MUST contain exactly 3 integers."})
                    if not all(isinstance(item, int) for item in batch):
                        raise ValidationError({'batches': f"Each batch in {team_key} MUST contain exactly 3 integers."})

    def __str__(self):
        return f"Match {self.match_no} - {self.date}"

class MatchStaff(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    scorer_1 = models.CharField(max_length=255)
    scorer_2 = models.CharField(max_length=255)
    umpire_1 = models.CharField(max_length=255)
    umpire_2 = models.CharField(max_length=255)
    post_umpire_1 = models.CharField(max_length=255, blank=True, null=True)
    post_umpire_2 = models.CharField(max_length=255, blank=True, null=True)
    dugout = models.CharField(max_length=255, blank=True, null=True)
    timekeeper = models.CharField(max_length=255)
    referee = models.CharField(max_length=255)

    def __str__(self):
        return f"Match Staff ID: {self.id}"

class MatchResult(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    team_a_name = models.CharField(max_length=255)
    team_b_name = models.CharField(max_length=255)
    team_a_total = models.IntegerField()
    team_b_total = models.IntegerField()
    team_A = models.JSONField(default=dict, blank=True, null=True)
    team_B = models.JSONField(default=dict, blank=True, null=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        import re

        val_pattern = re.compile(r'^(\d+|-)$')
        
        for team_key in ['team_A', 'team_B']:
            team_data = getattr(self, team_key)
            if not isinstance(team_data, dict):
                raise ValidationError({team_key: "Must be a dictionary."})
            
            for key in ['I', 'II', 'III']:
                if key in team_data:
                    val = team_data[key]
                    if not isinstance(val, list) or len(val) != 2:
                        raise ValidationError({team_key: f"Key {key} must be a list of exactly 2 strings."})
                    for item in val:
                        if not isinstance(item, str) or not val_pattern.match(item):
                            raise ValidationError({team_key: f"Elements in {key} must be numeric strings or '-'."})
            
            if 'IV' in team_data:
                val = team_data['IV']
                if not isinstance(val, str) or not val_pattern.match(val):
                    raise ValidationError({team_key: "Key IV must be a single numeric string or '-'."})

    @property
    def won_by(self):
        diff = abs(self.team_a_total - self.team_b_total)
        if diff == 0:
            return "Tie"
        return f"{diff} points"

    @property
    def team_won(self):
        if self.team_a_total > self.team_b_total:
            return self.team_a_name
        elif self.team_b_total > self.team_a_total:
            return self.team_b_name
        return "None"

    def __str__(self):
        return f"Result: {self.team_won} won by {self.won_by}"

class ExtraPoints(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    Team_A = models.JSONField(default=dict, blank=True)
    Team_B = models.JSONField(default=dict, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        for team_name in ['Team_A', 'Team_B']:
            team_data = getattr(self, team_name)
            if not isinstance(team_data, dict):
                raise ValidationError({team_name: "Must be a dictionary."})
            for field_name in ['late_entry', 'out_of_field', 'warning', 'dream_run']:
                if field_name in team_data:
                    val = team_data[field_name]
                    if not isinstance(val, list):
                        raise ValidationError({team_name: f"{field_name} must be a list."})
                    if not all(isinstance(item, int) for item in val):
                        raise ValidationError({team_name: f"All items in the list {field_name} must be integers."})

    def __str__(self):
        return f"ExtraPoints ID: {self.id}"

class RunningBatch(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    Team_A = models.JSONField(default=dict, blank=True)
    Team_B = models.JSONField(default=dict, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        for team_name in ['Team_A', 'Team_B']:
            team_data = getattr(self, team_name)
            if not isinstance(team_data, dict):
                raise ValidationError({team_name: "Must be a dictionary."})
            for turn in ['turn_I', 'turn_II', 'turn_III', 'turn_IV']:
                if turn in team_data:
                    val = team_data[turn]
                    if not isinstance(val, list):
                        raise ValidationError({team_name: f"{turn} must be a list."})
                    for sublist in val:
                        if not isinstance(sublist, list):
                            raise ValidationError({team_name: f"Elements in {turn} must be lists."})
                        if not all(isinstance(item, int) for item in sublist):
                            raise ValidationError({team_name: f"All items in sublists of {turn} must be integers."})

    def __str__(self):
        return f"RunningBatch ID: {self.id}"

class Substitution(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    Substitutions = models.JSONField(default=dict, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if not isinstance(self.Substitutions, dict):
            raise ValidationError({'Substitutions': "Must be a dictionary."})
        
        for team_name in ['TeamA', 'TeamB']:
            if team_name in self.Substitutions:
                team_data = self.Substitutions[team_name]
                if not isinstance(team_data, list):
                    raise ValidationError({'Substitutions': f"{team_name} must be a list."})
                for item in team_data:
                    if not isinstance(item, dict):
                        raise ValidationError({'Substitutions': f"Each substitution in {team_name} must be an object."})
                    if 'player_in' not in item or 'player_out' not in item:
                        raise ValidationError({'Substitutions': f"Each substitution in {team_name} must have player_in and player_out."})
                    if not isinstance(item['player_in'], int) or not isinstance(item['player_out'], int):
                        raise ValidationError({'Substitutions': f"player_in and player_out in {team_name} must be integers."})

    def __str__(self):
        return f"Substitution ID: {self.id}"

class Chase(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    Team_A = models.JSONField(default=dict, blank=True)
    Team_B = models.JSONField(default=dict, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        for team_name in ['Team_A', 'Team_B']:
            team_data = getattr(self, team_name)
            if not isinstance(team_data, dict):
                raise ValidationError({team_name: "Must be a dictionary."})
            for field_name in ['I', 'II', 'III', 'IV']:
                if field_name in team_data:
                    val = team_data[field_name]
                    if not isinstance(val, list):
                        raise ValidationError({team_name: f"{field_name} must be a single-dimensional list."})
                    if not all(isinstance(item, int) for item in val):
                        raise ValidationError({team_name: f"All items in {field_name} must be integers representing player IDs or chest numbers."})

    def __str__(self):
        return f"Chase ID: {self.id}"

class Defence(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    Team_A = models.JSONField(default=dict, blank=True)
    Team_B = models.JSONField(default=dict, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        import re

        time_pattern = re.compile(r'^(\d{2}:\d{2}|-)$')
        constraints = {'I': 3, 'II': 2, 'III': 2}

        for team_name in ['Team_A', 'Team_B']:
            team_data = getattr(self, team_name)
            if not isinstance(team_data, dict):
                raise ValidationError({team_name: "Must be a dictionary."})
            
            for field_name, expected_length in constraints.items():
                if field_name in team_data:
                    val = team_data[field_name]
                    if not isinstance(val, list):
                        raise ValidationError({team_name: f"{field_name} must be a list containing lists."})
                    if len(val) != expected_length:
                        raise ValidationError({team_name: f"{field_name} must contain exactly {expected_length} nested lists."})
                    
                    for inner_list in val:
                        if not isinstance(inner_list, list):
                            raise ValidationError({team_name: f"Items in {field_name} must be lists."})
                        if len(inner_list) != 15:
                            raise ValidationError({team_name: f"Inner lists in {field_name} must contain exactly 15 items."})
                        for item in inner_list:
                            if not isinstance(item, str):
                                raise ValidationError({team_name: f"Items in {field_name} must be strings."})
                            if not time_pattern.match(item):
                                raise ValidationError({team_name: f"Values in {field_name} must be in MM:SS format or a single hyphen '-'."})
            
            if 'IV' in team_data:
                val = team_data['IV']
                if not isinstance(val, list):
                    raise ValidationError({team_name: "IV must be a single, flat array."})
                if len(val) != 15:
                    raise ValidationError({team_name: "IV must contain exactly 15 items."})
                for item in val:
                    if not isinstance(item, str):
                        raise ValidationError({team_name: "Items in IV must be strings."})
                    if not time_pattern.match(item):
                        raise ValidationError({team_name: "Values in IV must be in MM:SS format or a single hyphen '-'."})

    def __str__(self):
        return f"Defence ID: {self.id}"

class ScoreCard(models.Model):
    match_id = models.IntegerField(null=True, blank=True)
    Team_A = models.JSONField(default=dict, blank=True)
    Team_B = models.JSONField(default=dict, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        import re

        time_pattern = re.compile(r'^\d{1,2}:\d{2}$')
        
        for team_name in ['Team_A', 'Team_B']:
            team_data = getattr(self, team_name)
            if not isinstance(team_data, dict):
                raise ValidationError({team_name: "Must be a dictionary."})
                
            for period, value in team_data.items():
                if not isinstance(value, dict):
                    raise ValidationError({team_name: f"Period {period} must be a dictionary."})
                
                for list_key in ['defender', 'attacker']:
                    if list_key not in value:
                        raise ValidationError({team_name: f"Period {period} missing {list_key}."})
                    if not isinstance(value[list_key], list):
                        raise ValidationError({team_name: f"{list_key} in {period} must be a list."})
                    if not all(isinstance(i, int) for i in value[list_key]):
                        raise ValidationError({team_name: f"All items in {list_key} for {period} must be integers."})
                
                for time_key in ['run_time', 'per_time']:
                    if time_key not in value:
                        raise ValidationError({team_name: f"Period {period} missing {time_key}."})
                    if not isinstance(value[time_key], list):
                        raise ValidationError({team_name: f"{time_key} in {period} must be a list."})
                    for t in value[time_key]:
                        if not isinstance(t, str) or not time_pattern.match(t):
                            raise ValidationError({team_name: f"Time {t} in {time_key} for {period} must be in M:SS or MM:SS format."})
                
                if 'symbol' not in value:
                    raise ValidationError({team_name: f"Period {period} missing symbol."})
                if not isinstance(value['symbol'], str) or len(value['symbol']) != 1:
                    raise ValidationError({team_name: f"Symbol in {period} must be a single string character."})

    def __str__(self):
        return f"ScoreCard ID: {self.id}"
