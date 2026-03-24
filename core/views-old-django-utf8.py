from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from .models import Tournament, Team, Player, Match, Inning, ScoreEvent
from .serializers import (
    TournamentSerializer, TeamSerializer, PlayerSerializer, 
    MatchSerializer, MatchCreateSerializer, InningSerializer, ScoreEventSerializer
)
from .utils.pdf_generator import generate_scoresheet_pdf

class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MatchCreateSerializer
        return MatchSerializer

    @action(detail=True, methods=['get'])
    def download_scoresheet(self, request, pk=None):
        match = self.get_object()
        try:
            pdf_buffer = generate_scoresheet_pdf(match)
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="match_{match.match_number}_scoresheet.pdf"'
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InningViewSet(viewsets.ModelViewSet):
    queryset = Inning.objects.all()
    serializer_class = InningSerializer

class ScoreEventViewSet(viewsets.ModelViewSet):
    queryset = ScoreEvent.objects.all()
    serializer_class = ScoreEventSerializer
