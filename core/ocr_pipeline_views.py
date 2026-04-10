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
import logging
import copy
from datetime import datetime
from django.conf import settings as django_settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status

# Configurable Tesseract path from .env
TESSERACT_PATH = os.environ.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

import cv2
import numpy as np

from .models import UploadRequest, ExtractedData, ReviewedData, AuditLog, Match, Tournament, Team, Player
from .utils.ocr_parser import deep_merge, diff_payload, find_missing_fields, is_full_payload
from .utils.template_extractor import KhoKhoExtractor
from .utils.dummy_record import build_dummy_extraction_payload
from .utils.ocr_validation import MISSING_VALUE

logger = logging.getLogger("ocr_pipeline")

# --- Required fields that must be present before final submission ---
REQUIRED_FIELDS = [
    "match_info.tournament", 
    "match_info.date", 
    "teams.team_a.name", 
    "teams.team_b.name"
]

DEFAULT_MATCH_TIME = "00:00:00"

# --- Helpers ---


def _build_review_status(current_payload):
    pending_required = find_missing_fields(current_payload, REQUIRED_FIELDS)
    review_status = "READY" if not pending_required else "REVIEW_REQUIRED"
    return review_status, pending_required


def _clean_string(value, default=""):
    if value is None:
        return default
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned == MISSING_VALUE:
            return default
        return cleaned
    return str(value)


def _clean_int(value, default=0):
    if value in (None, "", MISSING_VALUE):
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_sheet_datetime(match_info):
    scheduled_at = _clean_string(match_info.get("scheduled_at"))
    if scheduled_at:
        dt = parse_datetime(scheduled_at)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt

    date_value = _clean_string(match_info.get("date"))
    time_value = _clean_string(match_info.get("time"), DEFAULT_MATCH_TIME)

    parsed_date = parse_date(date_value)
    if parsed_date is None and date_value:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(date_value, fmt).date()
                break
            except ValueError:
                continue
    if parsed_date is None:
        parsed_date = timezone.localdate()

    parsed_time = parse_time(time_value)
    if parsed_time is None and time_value:
        for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"):
            try:
                parsed_time = datetime.strptime(time_value, fmt).time()
                break
            except ValueError:
                continue
    if parsed_time is None:
        parsed_time = parse_time(DEFAULT_MATCH_TIME)

    combined = datetime.combine(parsed_date, parsed_time)
    return timezone.make_aware(combined, timezone.get_current_timezone())


def _resolve_tournament(match_info, scheduled_dt):
    tournament_name = _clean_string(match_info.get("tournament"), "OCR Scoresheet Tournament")
    venue = _clean_string(match_info.get("venue"), "Unknown Venue")

    tournament, _created = Tournament.objects.get_or_create(
        name=tournament_name,
        defaults={
            "venue": venue,
            "start_date": scheduled_dt.date(),
            "end_date": scheduled_dt.date(),
            "organizer": "OCR Pipeline",
        },
    )

    updates = []
    if venue and tournament.venue != venue:
        tournament.venue = venue
        updates.append("venue")
    if scheduled_dt.date() < tournament.start_date:
        tournament.start_date = scheduled_dt.date()
        updates.append("start_date")
    if scheduled_dt.date() > tournament.end_date:
        tournament.end_date = scheduled_dt.date()
        updates.append("end_date")
    if updates:
        tournament.save(update_fields=updates)

    return tournament


def _resolve_team(team_payload, fallback_name):
    team_name = _clean_string(team_payload.get("name"), fallback_name)
    team, _created = Team.objects.get_or_create(name=team_name)

    updates = []
    coach = _clean_string(team_payload.get("coach"))
    manager = _clean_string(team_payload.get("manager"))
    if coach != (team.coach or ""):
        team.coach = coach or None
        updates.append("coach")
    if manager != (team.manager or ""):
        team.manager = manager or None
        updates.append("manager")
    if updates:
        team.save(update_fields=updates)

    return team


def _sync_players(team, players_payload):
    if not isinstance(players_payload, list):
        return

    for index, player_payload in enumerate(players_payload):
        if not isinstance(player_payload, dict):
            continue
        player_name = _clean_string(player_payload.get("name"))
        if not player_name:
            continue
        chest_number = _clean_int(player_payload.get("no"), index + 1) or (index + 1)
        Player.objects.update_or_create(
            team=team,
            chest_number=chest_number,
            defaults={"name": player_name},
        )


def _resolve_named_team(team_name, team_a, team_b):
    normalized = _clean_string(team_name).lower()
    if not normalized:
        return None
    if normalized == _clean_string(team_a.name).lower():
        return team_a
    if normalized == _clean_string(team_b.name).lower():
        return team_b
    return None


def _build_match_defaults(final_payload, upload_req):
    payload = copy.deepcopy(final_payload) if isinstance(final_payload, dict) else {}
    metadata = payload.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        payload["metadata"] = metadata
    metadata["request_id"] = str(upload_req.id)
    metadata["source_image_url"] = upload_req.image_url or ""
    metadata["submitted_at"] = timezone.now().isoformat()

    match_info = payload.get("match_info", {}) if isinstance(payload, dict) else {}
    teams_payload = payload.get("teams", {}) if isinstance(payload, dict) else {}
    team_a_payload = teams_payload.get("team_a", {}) if isinstance(teams_payload, dict) else {}
    team_b_payload = teams_payload.get("team_b", {}) if isinstance(teams_payload, dict) else {}
    score_payload = payload.get("score", {}) if isinstance(payload, dict) else {}
    result_payload = payload.get("result", {}) if isinstance(payload, dict) else {}
    officials_payload = payload.get("officials", {}) if isinstance(payload, dict) else {}

    scheduled_dt = _parse_sheet_datetime(match_info)
    tournament = _resolve_tournament(match_info, scheduled_dt)
    team_a = _resolve_team(team_a_payload, "Team A")
    team_b = _resolve_team(team_b_payload, "Team B")

    _sync_players(team_a, team_a_payload.get("players"))
    _sync_players(team_b, team_b_payload.get("players"))

    toss_team = _resolve_named_team(match_info.get("toss_winner"), team_a, team_b)
    winner_team = _resolve_named_team(result_payload.get("winner"), team_a, team_b)
    if winner_team is None:
        team_a_points = _clean_int(score_payload.get("team_a_points"))
        team_b_points = _clean_int(score_payload.get("team_b_points"))
        if team_a_points > team_b_points:
            winner_team = team_a
        elif team_b_points > team_a_points:
            winner_team = team_b

    remarks = _clean_string(payload.get("remarks"))
    result_summary = _clean_string(result_payload.get("summary"))
    if not result_summary:
        result_summary = _clean_string(match_info.get("stage"))

    return {
        "tournament": tournament,
        "match_number": _clean_int(match_info.get("match_no"), 0),
        "court_number": _clean_string(match_info.get("court_no")),
        "date": scheduled_dt.date(),
        "time": scheduled_dt.time().replace(microsecond=0),
        "team_a": team_a,
        "team_b": team_b,
        "toss_won_by": toss_team,
        "choice": _clean_string(match_info.get("choice")) or None,
        "winner": winner_team,
        "result_margin": result_summary or None,
        "remarks": remarks or None,
        "officials": officials_payload if isinstance(officials_payload, dict) else {},
        "sheet_payload": payload if isinstance(payload, dict) else {},
        "source_upload_request": upload_req,
    }


def _persist_match_record(upload_req, final_payload):
    defaults = _build_match_defaults(final_payload, upload_req)
    match, _created = Match.objects.update_or_create(
        source_upload_request=upload_req,
        defaults=defaults,
    )
    return match


def _extract_response_meta(extracted):
    raw_payload = extracted.raw_payload or {}
    meta = raw_payload.get("_meta") if isinstance(raw_payload, dict) else {}
    if not isinstance(meta, dict):
        meta = {}

    return {
        "usingDummyData": bool(meta.get("source") == "dummy" or meta.get("ocr_failed")),
        "ocrError": meta.get("ocr_error"),
        "recordSource": meta.get("source", "ocr"),
    }


def _get_review_layers(upload_req):
    extracted = upload_req.extracted_data
    extracted_payload = extracted.extracted_payload or {}

    try:
        reviewed = upload_req.reviewed_data
    except ReviewedData.DoesNotExist:
        reviewed = None

    user_edits = reviewed.user_edits if reviewed else {}
    final_payload = deep_merge(extracted_payload, user_edits) if user_edits else extracted_payload
    if reviewed and reviewed.final_payload:
        final_payload = reviewed.final_payload

    return extracted, reviewed, extracted_payload, user_edits, final_payload


def _build_review_response(upload_req):
    extracted, _reviewed, extracted_payload, user_edits, final_payload = _get_review_layers(upload_req)
    review_status, pending_required = _build_review_status(final_payload)
    response_meta = _extract_response_meta(extracted)

    if upload_req.status in ("PROCESSING", "FAILED"):
        response_status = upload_req.status
    else:
        response_status = review_status

    return {
        "requestId": str(upload_req.id),
        "status": response_status,
        "workflowStatus": upload_req.status,
        "raw_ocr": extracted.raw_payload or {},
        "extracted": extracted_payload,
        "final": final_payload,
        "user_edits": user_edits or {},
        "extractedData": extracted_payload,
        "rawOcrData": extracted.raw_payload or {},
        "finalData": final_payload,
        "currentData": final_payload,
        "userEdits": user_edits or {},
        "confidence": extracted.confidence_score,
        "confidenceScore": extracted.confidence_score,
        "missing_fields": extracted.missing_fields or [],
        "missingFields": extracted.missing_fields or [],
        "pendingRequiredFields": pending_required,
        "usingDummyData": response_meta["usingDummyData"],
        "ocrError": response_meta["ocrError"],
        "recordSource": response_meta["recordSource"],
        "sourceImageUrl": upload_req.image_url,
    }

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
    upload_req = None

    # 1. Acquire Image data
    logger.info("-" * 80)
    logger.info("📥 STEP 1: ACQUIRING IMAGE DATA")
    logger.info("-" * 80)
    
    image_file = request.FILES.get("image")
    if image_file:
        logger.info("Multipart file upload: %s", image_file.name)
        try:
            file_bytes = np.frombuffer(image_file.read(), np.uint8)
            img_ndarray = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            image_file.seek(0)
            save_dest = f"uploads/{uuid.uuid4()}_{image_file.name}"
            save_path = default_storage.save(save_dest, ContentFile(image_file.read()))
        except Exception as exc:
            return Response({"error": f"Decoding failed: {exc}"}, status=400)
    else:
        # Base64 path
        logger.info("📦 Base64 encoded image detected")
        image_b64 = request.data.get("image_base64") or request.data.get("image")
        if not image_b64:
            return Response({"error": "No image data found."}, status=400)
        
        try:
            if "," in image_b64: image_b64 = image_b64.split(",", 1)[1]
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
        return Response({"error": "Failed to decode image into CV2 array."}, status=400)

    req_id = str(uuid.uuid4())
    upload_req = UploadRequest.objects.create(
        id=req_id,
        user_id=request.data.get("userId", "anonymous"),
        document_type="scoresheet",
        image_url=save_path,
        status="PROCESSING",
    )

    # 2. Preprocess & Extract
    try:
        if not cv2 or not np:
            return Response({"error": "Backend missing CV2/NumPy dependencies."}, status=500)
            
        temp_id = uuid.uuid4()
        temp_path = os.path.join(django_settings.MEDIA_ROOT, f"{temp_id}.png")
        if not os.path.exists(django_settings.MEDIA_ROOT): 
            os.makedirs(django_settings.MEDIA_ROOT)
        
        cv2.imwrite(temp_path, img_ndarray)
        
        try:
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

             if "error" in payload:
                 logger.warning("OCR extraction failed. Falling back to dummy payload. error=%s", payload["error"])
                 payload = build_dummy_extraction_payload(str(payload["error"]))

             raw_ocr_payload = payload.get("raw_ocr", {})
             extracted_payload = payload.get("extracted", {})
             confidence = payload.get("confidence", payload.get("confidence_summary", 0.0))
             missing = payload.get("missing_fields", [])
             ocr_provider = payload.get("ocr_provider", "unknown")

             logger.info(
                 "[OCR] Extraction complete. Provider: %s | Confidence: %.2f | Missing: %d",
                 ocr_provider,
                 confidence,
                 len(missing),
             )
        except Exception as t_err:
             logger.exception("Extraction failed in pipeline. Falling back to dummy payload.")
             payload = build_dummy_extraction_payload(f"OCR Engine Error: {t_err}")
             raw_ocr_payload = payload.get("raw_ocr", {})
             extracted_payload = payload.get("extracted", {})
             confidence = payload.get("confidence", 0.0)
             missing = payload.get("missing_fields", [])
             ocr_provider = payload.get("ocr_provider", "dummy")
        finally:
             if os.path.exists(temp_path): os.remove(temp_path)
        
        # 3. Store extraction record
        ExtractedData.objects.create(
            request=upload_req,
            raw_payload=raw_ocr_payload,
            extracted_payload=extracted_payload,
            confidence_score=confidence,
            missing_fields=missing,
        )
        upload_req.status = "EXTRACTED"
        upload_req.save(update_fields=["status", "updated_at"])

        response_meta = _extract_response_meta(upload_req.extracted_data)

        return Response({
            "requestId": req_id,
            "status": "EXTRACTED",
            "ocrProvider": ocr_provider,
            "usingDummyData": response_meta["usingDummyData"],
            "ocrError": response_meta["ocrError"],
            "processingTimeMs": int((time.time() - start) * 1000),
            "dataPreview": extracted_payload
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as exc:
        logger.exception("OCR pipeline crashed")
        if upload_req:
            upload_req.status = "FAILED"
            upload_req.save(update_fields=["status", "updated_at"])
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
        return Response({"requestId": request_id, "status": "PROCESSING"})

    try:
        upload_req.extracted_data
    except ExtractedData.DoesNotExist:
        logger.error("❌ No extracted data found for request: %s", request_id)
        return Response({"error": "No extracted data found."}, status=404)
    return Response(_build_review_response(upload_req))


# ─── Step 4: Human Review & Update ───────────────────────────────────────────

@api_view(["PUT"])
@parser_classes([JSONParser])
def review_put(request, request_id):
    """PUT /api/review/<request_id>/update/"""
    try:
        upload_req = UploadRequest.objects.get(id=request_id)
        logger.info("✅ UploadRequest found")
    except UploadRequest.DoesNotExist:
        logger.error("❌ Request not found: %s", request_id)
        return Response({"error": "Request not found."}, status=404)

    updated_data = request.data.get("updatedData")
    reviewer_id  = request.data.get("reviewerId", "anonymous")

    if not updated_data or not isinstance(updated_data, dict):
        return Response({"error": "'updatedData' must be provided."}, status=400)

    try:
        extracted = upload_req.extracted_data
    except ExtractedData.DoesNotExist:
        return Response({"error": "No extracted data found."}, status=404)

    extracted_payload = extracted.extracted_payload or {}

    try:
        reviewed = upload_req.reviewed_data
    except ReviewedData.DoesNotExist:
        reviewed = None

    previous_data = reviewed.final_payload if reviewed and reviewed.final_payload else extracted_payload

    if is_full_payload(updated_data):
        next_final = updated_data
    else:
        next_final = deep_merge(previous_data, updated_data)

    user_edits = diff_payload(extracted_payload, next_final) or {}
    final_payload = deep_merge(extracted_payload, user_edits) if user_edits else extracted_payload

    AuditLog.objects.create(
        request=upload_req,
        user_id=reviewer_id,
        action_type="REVIEW",
        previous_value=previous_data,
        new_value=final_payload
    )

    ReviewedData.objects.update_or_create(
        request=upload_req,
        defaults={
            "reviewer_id": reviewer_id,
            "user_edits": user_edits,
            "final_payload": final_payload,
            "comments": request.data.get("comments"),
        },
    )

    upload_req.status = "REVIEWED"
    upload_req.save(update_fields=["status", "updated_at"])

    review_status, pending_required = _build_review_status(final_payload)

    return Response({
        "requestId": request_id,
        "status": review_status,
        "workflowStatus": "REVIEWED",
        "message": "Review saved successfully.",
        "userEdits": user_edits,
        "finalData": final_payload,
        "pendingRequiredFields": pending_required,
    })


# ─── Step 5: Final Confirmation ──────────────────────────────────────────────

@api_view(["POST"])
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

    try:
        extracted = upload_req.extracted_data
    except ExtractedData.DoesNotExist:
        return Response({"error": "No extracted data found."}, status=404)

    extracted_payload = extracted.extracted_payload or {}

    try:
        reviewed = upload_req.reviewed_data
    except ReviewedData.DoesNotExist:
        reviewed = None

    reviewer_id = request.data.get("reviewerId", "anonymous")
    skip_validation = bool(request.data.get("skipValidation"))
    previous_data = reviewed.final_payload if reviewed and reviewed.final_payload else extracted_payload
    user_edits = reviewed.user_edits if reviewed else {}
    request_final_payload = request.data.get("finalPayload")
    if isinstance(request_final_payload, dict) and is_full_payload(request_final_payload):
        final_payload = request_final_payload
        user_edits = diff_payload(extracted_payload, final_payload) or {}
    else:
        final_payload = deep_merge(extracted_payload, user_edits) if user_edits else extracted_payload

    missing = find_missing_fields(final_payload, REQUIRED_FIELDS)
    if missing and not skip_validation:
        return Response({
            "error": "Incomplete data.",
            "status": "REVIEW_REQUIRED",
            "missingFields": missing,
            "missing_fields": missing,
        }, status=400)
    
    logger.info("✅ All required fields present - Validation passed!")

    ReviewedData.objects.update_or_create(
        request=upload_req,
        defaults={
            "reviewer_id": reviewer_id,
            "user_edits": user_edits,
            "final_payload": final_payload,
            "comments": reviewed.comments if reviewed else None,
        },
    )

    match = _persist_match_record(upload_req, final_payload)

    AuditLog.objects.create(
        request=upload_req,
        user_id=reviewer_id,
        action_type="SUBMIT",
        previous_value=previous_data,
        new_value=final_payload,
    )

    upload_req.status = "COMPLETED"
    upload_req.save(update_fields=["status", "updated_at"])

    return Response({
        "requestId": request_id,
        "status": "COMPLETED",
        "message": "Successfully confirmed.",
        "finalPayload": final_payload,
        "matchId": match.id,
        "sourceImageUrl": upload_req.image_url,
        "validationSkipped": skip_validation,
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
