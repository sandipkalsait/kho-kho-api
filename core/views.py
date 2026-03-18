from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from .models import Tournament, Team, Player, MatchDetails, MatchStaff, MatchResult, ExtraPoints, RunningBatch, Substitution, Chase, Defence, ScoreCard
from .serializers import (
    TournamentSerializer, TeamSerializer, PlayerSerializer, 
    MatchDetailsSerializer, MatchDetailsResponseSerializer, MatchStaffSerializer,
    MatchResultSerializer, MatchResultResponseSerializer, ExtraPointsSerializer,
    RunningBatchSerializer, SubstitutionSerializer, ChaseSerializer, DefenceSerializer,
    ScoreCardSerializer
)
from .utils.pdf_generator import generate_scoresheet_pdf

class SubstitutionViewSet(viewsets.ModelViewSet):
    queryset = Substitution.objects.all()
    serializer_class = SubstitutionSerializer

class ChaseViewSet(viewsets.ModelViewSet):
    queryset = Chase.objects.all()
    serializer_class = ChaseSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"chase": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response([{"chase": item} for item in serializer.data])

class DefenceViewSet(viewsets.ModelViewSet):
    queryset = Defence.objects.all()
    serializer_class = DefenceSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"defence": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response([{"defence": item} for item in serializer.data])

class ScoreCardViewSet(viewsets.ModelViewSet):
    queryset = ScoreCard.objects.all()
    serializer_class = ScoreCardSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"score_card": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response([{"score_card": item} for item in serializer.data])

class RunningBatchViewSet(viewsets.ModelViewSet):
    queryset = RunningBatch.objects.all()
    serializer_class = RunningBatchSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"running_batch": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response([{"running_batch": item} for item in serializer.data])

class ExtraPointsViewSet(viewsets.ModelViewSet):
    queryset = ExtraPoints.objects.all()
    serializer_class = ExtraPointsSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"extra_points": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response([{"extra_points": item} for item in serializer.data])

class MatchResultViewSet(viewsets.ModelViewSet):
    queryset = MatchResult.objects.all()
    serializer_class = MatchResultSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"result": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response([{"result": item} for item in serializer.data])

class MatchStaffViewSet(viewsets.ModelViewSet):
    queryset = MatchStaff.objects.all()
    serializer_class = MatchStaffSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"match_staff": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response([{"match_staff": item} for item in serializer.data])

class MatchDetailsViewSet(viewsets.ModelViewSet):
    queryset = MatchDetails.objects.all()
    serializer_class = MatchDetailsSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"match_details": serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response([{"match_details": item} for item in serializer.data])

import io
import time
import logging
import json
import base64
from io import BytesIO
from PIL import Image, ImageOps
import pytesseract
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

# --- Structured Logging Setup ---
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage()
        }
        if hasattr(record, "extra_data"):
            log_entry.update(getattr(record, "extra_data"))
        return json.dumps(log_entry)

logger = logging.getLogger("ocr_logger")
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)
logger.propagate = False

class TournamentViewSet(viewsets.ModelViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

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
        
        # 4. Structured Logging
        logger.info(
            "OCR Processing Complete",
            extra={
                "extra_data": {
                    "filename": filename,
                    "content_type": content_type,
                    "processing_time_ms": processing_time_ms,
                    "extracted_text_snippet": extracted_text[:100] + "..." if len(extracted_text) > 100 else extracted_text,
                    "text_length": len(extracted_text)
                }
            }
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
