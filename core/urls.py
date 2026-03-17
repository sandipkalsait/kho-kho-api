from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TournamentViewSet, TeamViewSet, PlayerViewSet, 
    MatchViewSet, InningViewSet, ScoreEventViewSet, process_ocr
)

router = DefaultRouter()
router.register(r'tournaments', TournamentViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'players', PlayerViewSet)
router.register(r'matches', MatchViewSet)
router.register(r'innings', InningViewSet)
router.register(r'score-events', ScoreEventViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('ocr/', process_ocr, name='process-ocr'),
]
