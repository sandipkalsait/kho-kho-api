import base64
import json
import logging
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import cv2
from PIL import Image
import pytesseract

logger = logging.getLogger("ocr.provider")


class OCRProviderError(RuntimeError):
    """Raised when an OCR provider fails to return usable OCR output."""


@dataclass
class OCRWord:
    text: str
    left: int
    top: int
    width: int
    height: int
    line_index: int
    word_index: int


@dataclass
class OCRDocument:
    provider: str
    source: str
    text: str
    words: List[OCRWord]
    raw_response: Dict[str, Any]


def _encode_png_bytes(image) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise OCRProviderError("Failed to encode image for OCR.")
    return encoded.tobytes()


class OCRSpaceClient:
    def __init__(self):
        self.endpoint = os.environ.get("OCR_SPACE_ENDPOINT", "https://api.ocr.space/parse/image")
        self.api_key = os.environ.get("OCR_SPACE_API_KEY", "").strip()
        self.language = os.environ.get("OCR_SPACE_LANGUAGE", "eng")
        self.engine = os.environ.get("OCR_SPACE_ENGINE", "2")
        self.timeout_seconds = int(os.environ.get("OCR_SPACE_TIMEOUT_SECONDS", "45"))

    def extract_document(self, image, overlay_required: bool = True, is_table: bool = False) -> OCRDocument:
        if not self.api_key:
            raise OCRProviderError("OCR_SPACE_API_KEY is not configured.")

        image_bytes = _encode_png_bytes(image)
        payload = urllib.parse.urlencode(
            {
                "base64Image": "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
                "language": self.language,
                "isOverlayRequired": "true" if overlay_required else "false",
                "detectOrientation": "true",
                "scale": "true",
                "isTable": "true" if is_table else "false",
                "OCREngine": self.engine,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "apikey": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except Exception as exc:
            raise OCRProviderError(f"OCR.Space request failed: {exc}") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise OCRProviderError("OCR.Space returned invalid JSON.") from exc

        errors = parsed.get("ErrorMessage") or []
        if isinstance(errors, str):
            errors = [errors]

        parsed_results = parsed.get("ParsedResults") or []
        if parsed.get("IsErroredOnProcessing") and not parsed_results:
            detail = "; ".join(str(item) for item in errors if item) or parsed.get("ErrorDetails") or "unknown error"
            raise OCRProviderError(f"OCR.Space processing failed: {detail}")

        document = self._build_document(parsed, parsed_results)
        if overlay_required and not document.words:
            raise OCRProviderError("OCR.Space returned no overlay words for mapped extraction.")
        if not document.text and not document.words:
            raise OCRProviderError("OCR.Space returned empty OCR output.")
        return document

    def _build_document(self, parsed: Dict[str, Any], parsed_results: List[Dict[str, Any]]) -> OCRDocument:
        words: List[OCRWord] = []
        text_parts: List[str] = []
        line_index = 0

        for result in parsed_results:
            parsed_text = (result.get("ParsedText") or "").strip()
            if parsed_text:
                text_parts.append(parsed_text)

            overlay = result.get("TextOverlay") or {}
            for line in overlay.get("Lines") or []:
                line_words = line.get("Words") or []
                for word_index, word in enumerate(line_words):
                    word_text = (word.get("WordText") or "").strip()
                    if not word_text:
                        continue
                    words.append(
                        OCRWord(
                            text=word_text,
                            left=int(word.get("Left", 0) or 0),
                            top=int(word.get("Top", 0) or 0),
                            width=int(word.get("Width", 0) or 0),
                            height=int(word.get("Height", 0) or 0),
                            line_index=line_index,
                            word_index=word_index,
                        )
                    )
                line_index += 1

        return OCRDocument(
            provider="ocr_space",
            source="primary",
            text="\n".join(text_parts).strip(),
            words=words,
            raw_response=parsed,
        )


class SimulatedTesseractClient:
    """Local fallback that simulates the remote OCR contract using Tesseract."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_document(self, image, overlay_required: bool = True, is_table: bool = False) -> OCRDocument:
        pil_image = Image.fromarray(image)
        try:
            data = pytesseract.image_to_data(
                pil_image,
                output_type=pytesseract.Output.DICT,
                config="--psm 6",
            )
            full_text = pytesseract.image_to_string(pil_image, config="--psm 6").strip()
        except Exception as exc:
            raise OCRProviderError(f"Simulated Tesseract OCR failed: {exc}") from exc

        words: List[OCRWord] = []
        line_order: Dict[Any, int] = {}

        text_items = data.get("text", [])
        for index, raw_text in enumerate(text_items):
            word_text = str(raw_text).strip()
            if not word_text:
                continue

            line_key = (
                (data.get("page_num") or [1])[index],
                (data.get("block_num") or [0])[index],
                (data.get("par_num") or [0])[index],
                (data.get("line_num") or [0])[index],
            )
            if line_key not in line_order:
                line_order[line_key] = len(line_order)

            words.append(
                OCRWord(
                    text=word_text,
                    left=int((data.get("left") or [0])[index]),
                    top=int((data.get("top") or [0])[index]),
                    width=int((data.get("width") or [0])[index]),
                    height=int((data.get("height") or [0])[index]),
                    line_index=line_order[line_key],
                    word_index=index,
                )
            )

        return OCRDocument(
            provider="simulate",
            source="fallback",
            text=full_text or " ".join(word.text for word in words).strip(),
            words=words,
            raw_response={
                "provider": "simulate",
                "mode": "local_tesseract",
                "overlay_required": overlay_required,
                "is_table": is_table,
                "text": full_text,
            },
        )


class OCRDocumentService:
    def __init__(self, primary_client, fallback_client=None):
        self.primary_client = primary_client
        self.fallback_client = fallback_client

    def extract_document(self, image, overlay_required: bool = True, is_table: bool = False) -> OCRDocument:
        try:
            document = self.primary_client.extract_document(
                image,
                overlay_required=overlay_required,
                is_table=is_table,
            )
            return document
        except OCRProviderError as exc:
            if not self.fallback_client:
                raise

            logger.warning("Primary OCR provider failed. Falling back to simulated OCR. error=%s", exc)
            document = self.fallback_client.extract_document(
                image,
                overlay_required=overlay_required,
                is_table=is_table,
            )
            document.raw_response = {
                **document.raw_response,
                "fallback_reason": str(exc),
            }
            return document


def build_document_ocr_service(tesseract_cmd: Optional[str] = None) -> OCRDocumentService:
    primary_provider = os.environ.get("OCR_PRIMARY_PROVIDER", "ocr_space").strip().lower()
    fallback_provider = os.environ.get("OCR_FALLBACK_PROVIDER", "simulate").strip().lower()

    primary_client = OCRSpaceClient() if primary_provider == "ocr_space" else SimulatedTesseractClient(tesseract_cmd)

    if fallback_provider in ("", "none", primary_provider):
        fallback_client = None
    elif fallback_provider in ("simulate", "tesseract", "local_tesseract"):
        fallback_client = SimulatedTesseractClient(tesseract_cmd)
    else:
        logger.warning("Unknown OCR fallback provider '%s'. Fallback disabled.", fallback_provider)
        fallback_client = None

    return OCRDocumentService(primary_client=primary_client, fallback_client=fallback_client)
