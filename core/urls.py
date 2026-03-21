from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TournamentViewSet, TeamViewSet, PlayerViewSet,
    MatchViewSet, InningViewSet, ScoreEventViewSet, process_ocr
)
from .ocr_pipeline_views import upload_image, review_get, review_put, submit_request, audit_logs

router = DefaultRouter()
router.register(r'tournaments', TournamentViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'players', PlayerViewSet)
router.register(r'matches', MatchViewSet)
router.register(r'innings', InningViewSet)
router.register(r'score-events', ScoreEventViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # legacy OCR endpoint (kept for backwards compatibility)
    path('ocr/', process_ocr, name='process-ocr'),

    # ── Human-in-the-Loop OCR Pipeline ──────────────────────────────────────
    path('upload/',              upload_image,    name='pipeline-upload'),
    path('review/<str:request_id>/', review_get, name='pipeline-review-get'),
    path('review/<str:request_id>/update/', review_put, name='pipeline-review-put'),
    path('submit/<str:request_id>/', submit_request, name='pipeline-submit'),
    path('audit/<str:request_id>/',  audit_logs,     name='pipeline-audit'),
]
