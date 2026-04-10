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
    sheet_payload = models.JSONField(default=dict, null=True, blank=True)

    def clean(self):
        pass

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
        pass

    def __str__(self):
        return f"{self.event_type} - {self.points} pts"

# ─── Human-in-the-Loop OCR Pipeline Models ───────────────────────────────────

import uuid

class UploadRequest(models.Model):
    """Tracks the full lifecycle of an image-upload / OCR extraction request."""
    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('EXTRACTED',  'Extracted'),
        ('REVIEWED',   'Reviewed'),
        ('COMPLETED',  'Completed'),
        ('FAILED',     'Failed'),
    ]
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id       = models.CharField(max_length=255, blank=True, null=True)
    document_type = models.CharField(max_length=100, blank=True, null=True)
    image_url     = models.TextField(blank=True, null=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROCESSING', db_index=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"UploadRequest {self.id} [{self.status}]"


class ExtractedData(models.Model):
    """Immutable snapshot of the raw OCR / ML extraction output."""
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request          = models.OneToOneField(UploadRequest, related_name='extracted_data', on_delete=models.CASCADE)
    raw_payload      = models.JSONField(default=dict)
    confidence_score = models.FloatField(null=True, blank=True)
    missing_fields   = models.JSONField(default=list)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ExtractedData for {self.request_id}"


class ReviewedData(models.Model):
    """Mutable human-adjusted data linked to an UploadRequest."""
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request       = models.OneToOneField(UploadRequest, related_name='reviewed_data', on_delete=models.CASCADE)
    reviewer_id   = models.CharField(max_length=255, blank=True, null=True)
    final_payload = models.JSONField(default=dict)
    comments      = models.TextField(blank=True, null=True)
    updated_at    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ReviewedData for {self.request_id}"


class AuditLog(models.Model):
    """Append-only record of every change made during the review process."""
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request        = models.ForeignKey(UploadRequest, related_name='audit_logs', on_delete=models.CASCADE)
    user_id        = models.CharField(max_length=255, blank=True, null=True)
    action_type    = models.CharField(max_length=50)   # e.g. FIELD_UPDATE, APPROVED, SUBMITTED
    previous_value = models.JSONField(default=dict, blank=True)
    new_value      = models.JSONField(default=dict, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AuditLog [{self.action_type}] for {self.request_id}"
