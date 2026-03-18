from django.urls import path, include
from rest_framework.routers import DefaultRouter, APIRootView
from .views import (
    TournamentViewSet, TeamViewSet, PlayerViewSet, 
    MatchDetailsViewSet, MatchStaffViewSet,
    MatchResultViewSet, ExtraPointsViewSet, RunningBatchViewSet, SubstitutionViewSet, ChaseViewSet, DefenceViewSet,
    ScoreCardViewSet, process_ocr
)
from .views_distributor import DistributorAPIView
from django.urls import reverse

class CustomAPIRootView(APIRootView):
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # Add the custom distributor endpoint to the API root dictionary
        response.data['distributor'] = request.build_absolute_uri(reverse('distributor'))
        return response

class CustomRouter(DefaultRouter):
    APIRootView = CustomAPIRootView

router = CustomRouter()
router.register(r'tournaments', TournamentViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'players', PlayerViewSet)
router.register(r'match-details', MatchDetailsViewSet)
router.register(r'match-staff', MatchStaffViewSet)
router.register(r'result', MatchResultViewSet)
router.register(r'extra_points', ExtraPointsViewSet)
router.register(r'running_batch', RunningBatchViewSet)
router.register(r'substitutions', SubstitutionViewSet)
router.register(r'chase', ChaseViewSet)
router.register(r'defence', DefenceViewSet)
router.register(r'score_card', ScoreCardViewSet)

urlpatterns = [
    path('distributor/', DistributorAPIView.as_view(), name='distributor'),
    path('', include(router.urls)),
    path('ocr/', process_ocr, name='process-ocr'),
]
