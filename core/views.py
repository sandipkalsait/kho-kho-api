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

import io
import time
import logging
import base64
from io import BytesIO
from PIL import Image, ImageOps
import pytesseract
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

logger = logging.getLogger("core")

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

@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def process_ocr(request):
    start_time = time.time()
    
    # 1. Validate Request
    image_base64 = request.data.get('image_base64')
    if image_base64:
        try:
            image_data = base64.b64decode(image_base64)
            img = Image.open(BytesIO(image_data))
            filename = request.data.get('filename', 'upload.jpg')
            content_type = request.data.get('type', 'image/jpeg')
        except Exception as e:
            return Response({'error': 'Invalid base64 image data'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        # Fallback to standard multipart upload
        image_file = request.FILES.get('image') or request.data.get('image')
        
        if not image_file:
            return Response({'error': 'No image file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Guard against React Native sending string dictionary
        if isinstance(image_file, str):
            return Response({'error': 'Image was incorrectly sent as a string instead of a file.'}, status=status.HTTP_400_BAD_REQUEST)
            
        content_type = getattr(image_file, 'content_type', '')
        
        # Be more permissive with content types
        if not content_type.startswith('image/'):
            return Response({'error': f"Unsupported file type ({content_type}). Please upload an image."}, status=status.HTTP_400_BAD_REQUEST)
        
        img = Image.open(image_file)
        filename = getattr(image_file, 'name', 'unknown')

    try:
        
        # 2. Preprocessing
        img = ImageOps.grayscale(img)
        
        # 3. Perform OCR
        extracted_text = pytesseract.image_to_string(img).strip()
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # 4. Structured Logging (DEBUG)
        logger.info(
            "OCR Processing Complete | file: %s | length: %d",
            filename, len(extracted_text)
        )
        
        # 5. Return Response
        return Response({
            "status": "success",
            "text": extracted_text,
            "processing_time_ms": processing_time_ms
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(
            "OCR Processing Failed",
            extra={"extra_data": {"filename": locals().get('filename', 'unknown'), "error": str(e)}}
        )
        return Response({'error': 'Error processing image for OCR.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
