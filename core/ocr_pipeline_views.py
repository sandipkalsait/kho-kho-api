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
import json
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
# Extraction mode: 'standard' or 'optimized'
EXTRACTION_MODE = os.environ.get("EXTRACTION_MODE", "optimized").lower()
# Fast mode: skip heavy preprocessing
FAST_MODE = os.environ.get("FAST_MODE", "false").lower() == "true"
# Enable threading
USE_THREADING = os.environ.get("USE_THREADING", "true").lower() == "true"

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
from .utils.template_extractor import KhoKhoExtractor

# Import optimized extractor
try:
    from .utils.template_extractor_optimized import KhoKhoExtractorOptimized
except ImportError:
    KhoKhoExtractorOptimized = None

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

    logger.info("="*80)
    logger.info("📤 NEW IMAGE UPLOAD REQUEST RECEIVED")
    logger.info("="*80)
    logger.info("Content-Type: %s", request.content_type)
    logger.info("User-Agent: %s", request.META.get("HTTP_USER_AGENT", "unknown"))
    logger.info("Remote Address: %s", request.META.get("REMOTE_ADDR", "unknown"))
    
    start = time.time()
    img_ndarray = None
    save_path = None

    # 1. Acquire Image data
    logger.info("-" * 80)
    logger.info("📥 STEP 1: ACQUIRING IMAGE DATA")
    logger.info("-" * 80)
    
    image_file = request.FILES.get("image")
    if image_file:
        logger.info("✅ Multipart file detected")
        logger.info("Filename: %s", image_file.name)
        logger.info("File Size: %d bytes", image_file.size)
        logger.info("Content Type: %s", image_file.content_type)
        
        try:
            # Convert to ndarray for CV2 processing
            file_bytes = np.frombuffer(image_file.read(), np.uint8)
            img_ndarray = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            image_file.seek(0)
            save_path = default_storage.save(f"uploads/{uuid.uuid4()}_{image_file.name}", ContentFile(image_file.read()))
            logger.info("✅ Multipart file decoded successfully")
            logger.info("Image Saved to: %s", save_path)
        except Exception as exc:
            logger.error("❌ Image processing failed: %s", exc)
            return Response({"error": f"Image processing failed: {exc}"}, status=400)
    else:
        # Base64 path
        logger.info("📦 Base64 encoded image detected")
        image_b64 = request.data.get("image_base64") or request.data.get("image")
        if not image_b64:
            logger.warning("❌ No image data found in request")
            logger.warning("Available request keys: %s", list(request.data.keys()) if hasattr(request, 'data') else [])
            return Response({"error": "No image found in request.", "keys": list(request.data.keys()) if hasattr(request, 'data') else []}, status=400)
        
        try:
            logger.info("🔐 Decoding base64 image data")
            logger.info("Base64 data length: %d characters", len(image_b64))
            
            if "," in image_b64: 
                image_b64 = image_b64.split(",", 1)[1]
                logger.info("Data URI detected and stripped")
            
            img_bytes = base64.b64decode(image_b64)
            logger.info("✅ Base64 decoded successfully. Byte size: %d", len(img_bytes))
            
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_ndarray = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            save_path = f"base64_upload_{uuid.uuid4()}"
            logger.info("✅ Image decoded from bytes successfully")
        except Exception as exc:
            logger.error("❌ Invalid base64 or image decode failed: %s", exc)
            return Response({"error": f"Invalid base64: {exc}"}, status=400)

    if img_ndarray is None:
        logger.error("❌ Failed to decode image - ndarray is None")
        return Response({"error": "Failed to decode image."}, status=400)
    
    logger.info("✅ Image acquisition complete. Image shape: %s", img_ndarray.shape)

    # 2. Preprocess & OCR
    try:
        if not cv2 or not np:
            return Response({"error": "System Error: OpenCV or NumPy is not installed on the server backend."}, status=500)
            
        # Save file temporarily to disk for CV2/OCR processing
        temp_id = uuid.uuid4()
        temp_path = os.path.join(django_settings.MEDIA_ROOT, f"{temp_id}.png")
        if not os.path.exists(django_settings.MEDIA_ROOT): 
            os.makedirs(django_settings.MEDIA_ROOT)
        
        cv2.imwrite(temp_path, img_ndarray)
        
        try:
             # USE THE OPTIMIZED OR STANDARD EXTRACTOR
             t_path = os.environ.get("TESSERACT_PATH")
             
             # Choose extractor based on configuration
             if EXTRACTION_MODE == "optimized" and KhoKhoExtractorOptimized:
                 logger.info("📦 Initializing OPTIMIZED Extractor (fast_mode=%s, threading=%s)", FAST_MODE, USE_THREADING)
                 extractor = KhoKhoExtractorOptimized(t_path, fast_mode=FAST_MODE, use_threading=USE_THREADING)
             else:
                 logger.info("📦 Initializing STANDARD Extractor")
                 extractor = KhoKhoExtractor(t_path)
             
             logger.info("🔄 Starting template extraction...")
             payload = extractor.extract(temp_path)
             
             # Check for extraction error
             if "error" in payload:
                 logger.error("❌ Extraction failed with error: %s", payload["error"])
                 return Response({"error": payload["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
             
             # Extract raw text for legacy compatibility / audit
             raw_text = payload.get("raw_ocr", {}).get("tournament", "") # Sample text
             missing = payload.get("missing_fields", [])
             confidence_score = payload.get("confidence_summary", 0.0)
             
             # Extract performance metrics if available
             perf_metrics = payload.get("_performance", {})
             if perf_metrics:
                 logger.info("⚡ Performance Metrics: %s", json.dumps(perf_metrics, indent=2))
             
             logger.info("✅ Template extraction complete")
             logger.info("📊 Confidence Score: %.2f%%", confidence_score * 100)
             logger.info("⚠️  Missing Fields Count: %d", len(missing))
             if missing:
                 logger.warning("Missing Fields Details: %s", missing)
        except Exception as t_err:
             logger.exception("❌ Tesseract execution failed")
             return Response({"error": f"Tesseract Engine Error: {t_err}. Check your TESSERACT_PATH in .env or system PATH."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
             if os.path.exists(temp_path): os.remove(temp_path)
        
        # Confidence logic
        confidence = confidence_score if raw_text else 0.0
        
        logger.info("="*80)
        logger.info("💾 STORING EXTRACTED DATA IN DATABASE")
        logger.info("="*80)

        # Create Record
        req_id = str(uuid.uuid4())
        logger.info("Generated Request ID: %s", req_id)
        logger.info("User ID: %s", request.data.get("userId", "anonymous"))
        logger.info("Document Type: %s", request.data.get("documentType", "scoresheet"))
        logger.info("Image URL: %s", save_path)
        
        upload_req = UploadRequest.objects.create(
            id=req_id,
            user_id=request.data.get("userId", "anonymous"),
            document_type=request.data.get("documentType", "scoresheet"),
            image_url=save_path,
            status="EXTRACTED",
        )
        logger.info("✅ UploadRequest created in DB: %s", req_id)
        
        # Log the full extracted payload
        logger.info("-" * 80)
        logger.info("📋 FULL EXTRACTED DATA PAYLOAD:")
        logger.info("-" * 80)
        logger.info(json.dumps(payload, indent=2))
        logger.info("-" * 80)
        
        extracted_data = ExtractedData.objects.create(
            request=upload_req,
            raw_payload=payload,
            confidence_score=confidence,
            missing_fields=missing,
        )
        logger.info("✅ ExtractedData record created in DB")
        logger.info("  - Confidence Score stored: %.4f", confidence)
        logger.info("  - Missing Fields stored: %s", missing)
        logger.info("="*80)

        processing_time_ms = int((time.time() - start) * 1000)
        logger.info("⏱️  Total Processing Time: %d ms", processing_time_ms)
        logger.info("🎉 OCR UPLOAD AND EXTRACTION COMPLETE")
        logger.info("="*80)

        return Response({
            "requestId": req_id,
            "status": "EXTRACTED",
            "processingTimeMs": processing_time_ms,
            "dataPreview": payload
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as exc:
        logger.exception("❌ Final OCR pipeline stage failed")
        return Response({"error": str(exc)}, status=500)


# ─── Step 3: Fetch Extracted Data ────────────────────────────────────────────

@api_view(["GET"])
def review_get(request, request_id):
    """GET /api/review/<request_id>/"""
    logger.info("="*80)
    logger.info("📖 FETCHING EXTRACTED DATA FOR REVIEW")
    logger.info("="*80)
    logger.info("Request ID: %s", request_id)
    
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
        logger.info("✅ UploadRequest found with status: %s", upload_req.status)
    except UploadRequest.DoesNotExist:
        logger.error("❌ Request not found: %s", request_id)
        return Response({"error": "Request not found."}, status=404)

    if upload_req.status == "PROCESSING":
        logger.info("⏳ Request is still being processed")
        return Response({"requestId": request_id, "status": "PROCESSING", "message": "Still processing."})

    if upload_req.status == "FAILED":
        logger.error("❌ Request failed")
        return Response({"requestId": request_id, "status": "FAILED"}, status=500)

    try:
        extracted = upload_req.extracted_data
        logger.info("✅ ExtractedData found")
    except ExtractedData.DoesNotExist:
        logger.error("❌ No extracted data found for request: %s", request_id)
        return Response({"error": "No extracted data found."}, status=404)

    # Prefer the reviewed payload if a human already touched it
    current_payload = extracted.raw_payload
    if upload_req.status in ("REVIEWED", "COMPLETED"):
        try:
            current_payload = upload_req.reviewed_data.final_payload
            logger.info("✅ Using reviewed/completed payload")
        except ReviewedData.DoesNotExist:
            logger.info("ℹ️  Using raw extracted payload (no reviews yet)")
            pass
    else:
        logger.info("ℹ️  Using raw extracted payload")

    logger.info("-" * 80)
    logger.info("📋 RETURNING EXTRACTED DATA:")
    logger.info("-" * 80)
    logger.info("Confidence Score: %.4f", extracted.confidence_score)
    logger.info("Missing Fields: %s", extracted.missing_fields)
    logger.info("Current Payload:")
    logger.info(json.dumps(current_payload, indent=2))
    logger.info("="*80)

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
    logger.info("="*80)
    logger.info("👤 PROCESSING HUMAN REVIEW & DATA UPDATES")
    logger.info("="*80)
    logger.info("Request ID: %s", request_id)
    
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
        logger.info("✅ UploadRequest found")
    except UploadRequest.DoesNotExist:
        logger.error("❌ Request not found: %s", request_id)
        return Response({"error": "Request not found."}, status=404)

    updated_data = request.data.get("updatedData")
    reviewer_id  = request.data.get("reviewerId", "anonymous")
    comments     = request.data.get("comments", "")
    
    logger.info("Reviewer ID: %s", reviewer_id)
    logger.info("Comments: %s", comments if comments else "(none)")

    if not updated_data or not isinstance(updated_data, dict):
        logger.error("❌ Invalid updatedData: must be a non-empty dictionary")
        return Response({"error": "'updatedData' must be a non-empty object."}, status=400)

    logger.info("-" * 80)
    logger.info("📝 UPDATED DATA RECEIVED:")
    logger.info("-" * 80)
    logger.info(json.dumps(updated_data, indent=2))

    # Capture previous payload for audit trail
    previous = {}
    try:
        previous = upload_req.reviewed_data.final_payload
        logger.info("ℹ️  Previous payload from reviewed_data")
    except ReviewedData.DoesNotExist:
        try:
            previous = upload_req.extracted_data.raw_payload
            logger.info("ℹ️  Previous payload from extracted_data")
        except ExtractedData.DoesNotExist:
            logger.warning("⚠️  No previous payload found")
            pass

    # Compute field-level diff for audit
    changed_fields = {k: {"old": previous.get(k), "new": v} for k, v in updated_data.items() if previous.get(k) != v}
    
    logger.info("-" * 80)
    logger.info("🔄 FIELD-LEVEL CHANGES:")
    logger.info("-" * 80)
    logger.info("Total fields changed: %d", len(changed_fields))
    for field, changes in changed_fields.items():
        logger.info("  ✏️  %s:", field)
        logger.info("     OLD: %s", changes["old"])
        logger.info("     NEW: %s", changes["new"])

    # Upsert ReviewedData
    logger.info("-" * 80)
    logger.info("💾 STORING REVIEWED DATA")
    logger.info("-" * 80)
    
    ReviewedData.objects.update_or_create(
        request=upload_req,
        defaults={
            "reviewer_id":   reviewer_id,
            "final_payload": updated_data,
            "comments":      comments,
        },
    )
    logger.info("✅ ReviewedData saved to database")

    # Audit log
    audit_entry = AuditLog.objects.create(
        request=upload_req,
        user_id=reviewer_id,
        action_type="FIELD_UPDATE",
        previous_value=previous,
        new_value=updated_data,
    )
    logger.info("✅ AuditLog entry created: %s", audit_entry.id)

    # Update missing fields on ExtractedData
    try:
        ext = upload_req.extracted_data
        ext.missing_fields = find_missing_fields(updated_data)
        ext.save()
        logger.info("✅ Updated missing fields in ExtractedData: %s", ext.missing_fields)
    except ExtractedData.DoesNotExist:
        logger.warning("⚠️  ExtractedData not found for missing fields update")
        pass

    upload_req.status = "REVIEWED"
    upload_req.save()
    logger.info("✅ UploadRequest status updated to: REVIEWED")
    
    logger.info("="*80)
    logger.info("✅ REVIEW PROCESSING COMPLETE")
    logger.info("="*80)

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
    logger.info("="*80)
    logger.info("✅ SUBMITTING EXTRACTED DATA - FINAL VALIDATION")
    logger.info("="*80)
    logger.info("Request ID: %s", request_id)
    
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
        logger.info("✅ UploadRequest found with status: %s", upload_req.status)
    except UploadRequest.DoesNotExist:
        logger.error("❌ Request not found: %s", request_id)
        return Response({"error": "Request not found."}, status=404)

    if upload_req.status == "COMPLETED":
        logger.warning("⚠️  Request already submitted")
        return Response({"error": "Already submitted.", "requestId": request_id}, status=400)

    if upload_req.status not in ("EXTRACTED", "REVIEWED"):
        logger.error("❌ Invalid status for submission: %s", upload_req.status)
        return Response({
            "error": f"Cannot submit a request with status '{upload_req.status}'. Must be EXTRACTED or REVIEWED."
        }, status=400)

    # Use reviewed payload if available, else fall back to extracted
    logger.info("-" * 80)
    logger.info("📦 LOADING FINAL PAYLOAD")
    logger.info("-" * 80)
    
    try:
        final_payload = upload_req.reviewed_data.final_payload
        logger.info("✅ Using reviewed payload")
    except ReviewedData.DoesNotExist:
        try:
            final_payload = upload_req.extracted_data.raw_payload
            logger.info("✅ Using extracted payload (no reviews)")
        except ExtractedData.DoesNotExist:
            logger.error("❌ No data to submit")
            return Response({"error": "No data to submit."}, status=400)

    logger.info("Final Payload:")
    logger.info(json.dumps(final_payload, indent=2))

    # Validate completeness
    logger.info("-" * 80)
    logger.info("🔍 VALIDATING DATA COMPLETENESS")
    logger.info("-" * 80)
    
    missing = find_missing_fields(final_payload)
    if missing:
        logger.error("❌ Validation failed - Missing fields: %s", missing)
        return Response({
            "error":         "Cannot submit — required fields are missing.",
            "missingFields": missing,
        }, status=400)
    
    logger.info("✅ All required fields present - Validation passed!")

    # Mark as completed
    logger.info("-" * 80)
    logger.info("💾 MARKING REQUEST AS COMPLETED")
    logger.info("-" * 80)
    
    upload_req.status = "COMPLETED"
    upload_req.save()
    logger.info("✅ UploadRequest status updated to: COMPLETED")

    # Final audit log
    audit_entry = AuditLog.objects.create(
        request=upload_req,
        user_id=request.data.get("reviewerId", "system"),
        action_type="SUBMITTED",
        previous_value={},
        new_value=final_payload,
    )
    logger.info("✅ Final AuditLog entry created: %s", audit_entry.id)
    
    logger.info("="*80)
    logger.info("🎉 DATA SUBMISSION COMPLETE - ALL VALIDATIONS PASSED")
    logger.info("="*80)

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
    logger.info("="*80)
    logger.info("📋 FETCHING AUDIT LOGS")
    logger.info("="*80)
    logger.info("Request ID: %s", request_id)
    
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
        logger.info("✅ UploadRequest found")
    except UploadRequest.DoesNotExist:
        logger.error("❌ Request not found: %s", request_id)
        return Response({"error": "Request not found."}, status=404)

    logs = upload_req.audit_logs.values(
        "id", "user_id", "action_type", "previous_value", "new_value", "created_at"
    )
    logs_list = list(logs)
    
    logger.info("-" * 80)
    logger.info("📝 AUDIT LOG ENTRIES: %d total", len(logs_list))
    logger.info("-" * 80)
    for idx, log_entry in enumerate(logs_list, 1):
        logger.info("Entry %d:", idx)
        logger.info("  ID: %s", log_entry["id"])
        logger.info("  User: %s", log_entry["user_id"])
        logger.info("  Action: %s", log_entry["action_type"])
        logger.info("  Timestamp: %s", log_entry["created_at"])
        logger.info("  Previous Value: %s", json.dumps(log_entry["previous_value"], indent=2) if log_entry["previous_value"] else "(none)")
        logger.info("  New Value: %s", json.dumps(log_entry["new_value"], indent=2) if log_entry["new_value"] else "(none)")
    
    logger.info("="*80)
    
    return Response({"requestId": request_id, "auditLogs": logs_list})
