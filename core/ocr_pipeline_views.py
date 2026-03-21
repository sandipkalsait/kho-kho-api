"""
Human-in-the-Loop OCR Pipeline Views
=====================================
Implements the 5-step image processing workflow:
  POST /api/upload/          -> Step 1: Upload image + trigger OCR
  GET  /api/review/<id>/     -> Step 3: Fetch extracted data for review
  PUT  /api/review/<id>/     -> Step 4: Submit human edits + audit trail
  POST /api/submit/<id>/     -> Step 5: Finalise & persist confirmed data
"""

import os
import uuid
import time
import base64
from django.conf import settings as django_settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from PIL import Image, ImageOps
import logging
from io import BytesIO

# Configurable Tesseract path from .env
TESSERACT_PATH = os.environ.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

try:
    import cv2
except ImportError:
    cv2 = None
    
try:
    import numpy as np
except ImportError:
    np = None

try:
    import pytesseract
    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except ImportError:
    pytesseract = None

from .models import UploadRequest, ExtractedData, ReviewedData, AuditLog
from .utils.ocr_preprocessing import preprocess_image
from .utils.ocr_parser import parse_kho_kho_sheet, find_missing_fields

logger = logging.getLogger("ocr_pipeline")

# ─── Required fields that must be present before submission ───────────────────
REQUIRED_FIELDS = ["teamA", "teamB", "date"]

# ─── Helpers ─────────────────────────────────────────────────────────────────

# Handled by utils.ocr_preprocessing and utils.ocr_parser


@csrf_exempt
@api_view(["GET", "POST", "PUT", "OPTIONS"])
def upload_image(request):
    """
    POST /api/upload/
    Accepts Multipart or Base64 JSON.
    """
    if request.method != "POST":
        return Response({"error": "Only POST is allowed for upload."}, status=405)

    logger.info("Upload request received. Content-Type: %s", request.content_type)
    
    start = time.time()
    img_ndarray = None
    save_path = None

    # 1. Acquire Image data
    image_file = request.FILES.get("image")
    if image_file:
        logger.info("Processing multipart file: %s", image_file.name)
        try:
            # Convert to ndarray for CV2 processing
            file_bytes = np.frombuffer(image_file.read(), np.uint8)
            img_ndarray = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            image_file.seek(0)
            save_path = default_storage.save(f"uploads/{uuid.uuid4()}_{image_file.name}", ContentFile(image_file.read()))
        except Exception as exc:
            return Response({"error": f"Image processing failed: {exc}"}, status=400)
    else:
        # Base64 path
        image_b64 = request.data.get("image_base64") or request.data.get("image")
        if not image_b64:
            logger.warning("No image data found in request data.")
            return Response({"error": "No image found in request.", "keys": list(request.data.keys()) if hasattr(request, 'data') else []}, status=400)
        
        try:
            logger.info("Processing base64 image data")
            if "," in image_b64: image_b64 = image_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(image_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_ndarray = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            save_path = f"base64_upload_{uuid.uuid4()}"
        except Exception as exc:
            return Response({"error": f"Invalid base64: {exc}"}, status=400)

    if img_ndarray is None:
        return Response({"error": "Failed to decode image."}, status=400)

    # 2. Preprocess & OCR
    try:
        if not cv2 or not np or not pytesseract:
            missing_libs = [l for l, m in [("opencv-python", cv2), ("numpy", np), ("pytesseract", pytesseract)] if not m]
            logger.error("Missing dependencies for OCR: %s", missing_libs)
            return Response({"error": f"OCR dependencies are missing: {', '.join(missing_libs)}. Please run 'pip install -r requirements.txt' and ensure Tesseract is installed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Image Refinement (Grayscale, Noise, Deskew, Thresh)
        logger.debug("Refining image for OCR...")
        refined_img = preprocess_image(img_ndarray)
        
        # OCR Engine
        pil_refined = Image.fromarray(refined_img)
        
        # Check if tesseract is actually executable
        logger.info("Executing Tesseract OCR...")
        try:
             raw_text = pytesseract.image_to_string(pil_refined, config="--psm 3").strip()
             logger.debug("Raw extracted text (first 50 chars): %s", raw_text[:50])
        except Exception as t_err:
             logger.exception("Tesseract execution failed")
             return Response({"error": f"Tesseract Engine Error: {t_err}. Check your TESSERACT_PATH in .env or system PATH."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Build structured data via parser
        payload = parse_kho_kho_sheet(raw_text)
        missing = find_missing_fields(payload)
        logger.info("Extraction complete. Fields missing: %s", missing)
        
        # Confidence logic (stub)
        confidence = 0.8 if raw_text else 0.0

        # Create Record
        req_id = str(uuid.uuid4())
        upload_req = UploadRequest.objects.create(
            id=req_id,
            user_id=request.data.get("userId", "anonymous"),
            document_type=request.data.get("documentType", "scoresheet"),
            image_url=save_path,
            status="EXTRACTED",
        )
        ExtractedData.objects.create(
            request=upload_req,
            raw_payload=payload,
            confidence_score=confidence,
            missing_fields=missing,
        )

        return Response({
            "requestId": req_id,
            "status": "EXTRACTED",
            "processingTimeMs": int((time.time() - start) * 1000),
            "dataPreview": payload
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as exc:
        return Response({"error": str(exc)}, status=500)


# ─── Step 3: Fetch Extracted Data ────────────────────────────────────────────

@api_view(["GET"])
def review_get(request, request_id):
    """GET /api/review/<request_id>/"""
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
    except UploadRequest.DoesNotExist:
        return Response({"error": "Request not found."}, status=404)

    if upload_req.status == "PROCESSING":
        return Response({"requestId": request_id, "status": "PROCESSING", "message": "Still processing."})

    if upload_req.status == "FAILED":
        return Response({"requestId": request_id, "status": "FAILED"}, status=500)

    try:
        extracted = upload_req.extracted_data
    except ExtractedData.DoesNotExist:
        return Response({"error": "No extracted data found."}, status=404)

    # Prefer the reviewed payload if a human already touched it
    current_payload = extracted.raw_payload
    if upload_req.status in ("REVIEWED", "COMPLETED"):
        try:
            current_payload = upload_req.reviewed_data.final_payload
        except ReviewedData.DoesNotExist:
            pass

    return Response({
        "requestId":       request_id,
        "status":          upload_req.status,
        "extractedData":   current_payload,
        "confidenceScore": extracted.confidence_score,
        "missingFields":   extracted.missing_fields,
    })


# ─── Step 4: Human Review & Update ───────────────────────────────────────────

@api_view(["PUT"])
@parser_classes([JSONParser])
def review_put(request, request_id):
    """PUT /api/review/<request_id>/"""
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
    except UploadRequest.DoesNotExist:
        return Response({"error": "Request not found."}, status=404)

    updated_data = request.data.get("updatedData")
    reviewer_id  = request.data.get("reviewerId", "anonymous")
    comments     = request.data.get("comments", "")

    if not updated_data or not isinstance(updated_data, dict):
        return Response({"error": "'updatedData' must be a non-empty object."}, status=400)

    # Capture previous payload for audit trail
    previous = {}
    try:
        previous = upload_req.reviewed_data.final_payload
    except ReviewedData.DoesNotExist:
        try:
            previous = upload_req.extracted_data.raw_payload
        except ExtractedData.DoesNotExist:
            pass

    # Compute field-level diff for audit
    changed_fields = {k: {"old": previous.get(k), "new": v} for k, v in updated_data.items() if previous.get(k) != v}

    # Upsert ReviewedData
    ReviewedData.objects.update_or_create(
        request=upload_req,
        defaults={
            "reviewer_id":   reviewer_id,
            "final_payload": updated_data,
            "comments":      comments,
        },
    )

    # Audit log
    AuditLog.objects.create(
        request=upload_req,
        user_id=reviewer_id,
        action_type="FIELD_UPDATE",
        previous_value=previous,
        new_value=updated_data,
    )

    # Update missing fields on ExtractedData
    try:
        ext = upload_req.extracted_data
        ext.missing_fields = find_missing_fields(updated_data)
        ext.save()
    except ExtractedData.DoesNotExist:
        pass

    upload_req.status = "REVIEWED"
    upload_req.save()

    return Response({
        "requestId":     request_id,
        "status":        "REVIEWED",
        "changedFields": changed_fields,
        "message":       "Review saved successfully.",
    })


# ─── Step 5: Final Confirmation ──────────────────────────────────────────────

@api_view(["POST"])
@parser_classes([JSONParser])
def submit_request(request, request_id):
    """POST /api/submit/<request_id>/"""
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
    except UploadRequest.DoesNotExist:
        return Response({"error": "Request not found."}, status=404)

    if upload_req.status == "COMPLETED":
        return Response({"error": "Already submitted.", "requestId": request_id}, status=400)

    if upload_req.status not in ("EXTRACTED", "REVIEWED"):
        return Response({
            "error": f"Cannot submit a request with status '{upload_req.status}'. Must be EXTRACTED or REVIEWED."
        }, status=400)

    # Use reviewed payload if available, else fall back to extracted
    try:
        final_payload = upload_req.reviewed_data.final_payload
    except ReviewedData.DoesNotExist:
        try:
            final_payload = upload_req.extracted_data.raw_payload
        except ExtractedData.DoesNotExist:
            return Response({"error": "No data to submit."}, status=400)

    # Validate completeness
    missing = find_missing_fields(final_payload)
    if missing:
        return Response({
            "error":         "Cannot submit — required fields are missing.",
            "missingFields": missing,
        }, status=400)

    # Mark as completed
    upload_req.status = "COMPLETED"
    upload_req.save()

    # Final audit log
    AuditLog.objects.create(
        request=upload_req,
        user_id=request.data.get("reviewerId", "system"),
        action_type="SUBMITTED",
        previous_value={},
        new_value=final_payload,
    )

    return Response({
        "requestId":    request_id,
        "status":       "COMPLETED",
        "finalPayload": final_payload,
        "message":      "Data validated and persisted successfully.",
    })


# ─── Audit Log retrieval ──────────────────────────────────────────────────────

@api_view(["GET"])
def audit_logs(request, request_id):
    """GET /api/audit/<request_id>/  — returns full audit trail."""
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
    except UploadRequest.DoesNotExist:
        return Response({"error": "Request not found."}, status=404)

    logs = upload_req.audit_logs.values(
        "id", "user_id", "action_type", "previous_value", "new_value", "created_at"
    )
    return Response({"requestId": request_id, "auditLogs": list(logs)})
