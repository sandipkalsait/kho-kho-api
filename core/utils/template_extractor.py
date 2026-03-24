import cv2
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from .roi_config import ROI_LAYOUT
from .ocr_preprocessing import preprocess_image
from .ocr_provider import OCRDocument, build_document_ocr_service
from .ocr_validation import MISSING_VALUE, calculate_confidence, normalize_field

logger = logging.getLogger("ocr_pipeline.extractor")


class KhoKhoExtractor:
    """Structured OCR extraction with OCR.Space primary and simulated fallback."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.roi_config = ROI_LAYOUT
        self.placeholder = MISSING_VALUE
        self.ocr_service = build_document_ocr_service(tesseract_cmd)

    def _coords_to_bbox(self, image_shape, coords: List[float]) -> Tuple[int, int, int, int]:
        h, w = image_shape[:2]
        ymin, xmin, ymax, xmax = coords
        x1, y1 = int(xmin * w), int(ymin * h)
        x2, y2 = int(xmax * w), int(ymax * h)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        return x1, y1, x2, y2

    def _extract_text_from_bbox(self, document: OCRDocument, bbox: Tuple[int, int, int, int]) -> str:
        x1, y1, x2, y2 = bbox
        selected_words = []

        for word in document.words:
            center_x = word.left + (word.width / 2)
            center_y = word.top + (word.height / 2)
            if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                selected_words.append(word)

        selected_words.sort(key=lambda item: (item.line_index, item.top, item.left, item.word_index))
        return " ".join(word.text for word in selected_words).strip()

    def _extract_field_text(self, document: OCRDocument, image_shape, coords: List[float]) -> str:
        return self._extract_text_from_bbox(document, self._coords_to_bbox(image_shape, coords))

    def _extract_player_rows(
        self,
        document: OCRDocument,
        image_shape,
        table_coords: List[float],
        team_key: str,
        count: int = 15,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], int]:
        x1, y1, x2, y2 = self._coords_to_bbox(image_shape, table_coords)
        table_height = max(1, y2 - y1)
        row_height = table_height / count

        raw_players: List[Dict[str, Any]] = []
        extracted_players: List[Dict[str, Any]] = []
        missing_fields: List[str] = []
        valid_count = 0

        for index in range(count):
            row_y1 = int(y1 + (index * row_height))
            row_y2 = int(y1 + ((index + 1) * row_height))
            raw_text = self._extract_text_from_bbox(document, (x1, row_y1, x2, row_y2))
            player_name = normalize_field("player_name", raw_text, placeholder=self.placeholder)

            raw_players.append({"no": index + 1, "name": raw_text})
            extracted_players.append({"no": index + 1, "name": player_name})

            if player_name == self.placeholder:
                missing_fields.append(f"teams.{team_key}.players.{index}.name")
            else:
                valid_count += 1

        return raw_players, extracted_players, missing_fields, valid_count

    def extract(self, image_path: str) -> Dict[str, Any]:
        logger.info("[OCR] Starting strict extraction for %s", image_path)
        start_time = datetime.now()

        img = cv2.imread(image_path)
        if img is None:
            return {"error": f"Image load failed for {image_path}"}

        processed = preprocess_image(img)

        try:
            document = self.ocr_service.extract_document(processed, overlay_required=True, is_table=True)
        except Exception as exc:
            logger.exception("[OCR] Document OCR failed")
            return {"error": f"Document OCR failed: {exc}"}

        res: Dict[str, Any] = {
            "raw_ocr": {
                "match_info": {},
                "teams": {
                    "team_a": {"name": "", "players": []},
                    "team_b": {"name": "", "players": []},
                },
                "score": {"team_a_points": "", "team_b_points": ""},
                "officials": {},
                "remarks": "",
            },
            "extracted": {
                "match_info": {},
                "teams": {
                    "team_a": {"name": self.placeholder, "players": []},
                    "team_b": {"name": self.placeholder, "players": []},
                },
                "score": {"team_a_points": self.placeholder, "team_b_points": self.placeholder},
                "officials": {},
                "remarks": self.placeholder,
            },
            "missing_fields": [],
            "confidence": 0.0,
            "confidence_summary": 0.0,
            "ocr_provider": document.provider,
            "_performance": {
                "ocr_provider": document.provider,
                "ocr_source": document.source,
            },
        }

        validated_count = 0
        total_fields_to_track = 0

        def extract_single_field(
            raw_target: Dict[str, Any],
            extracted_target: Dict[str, Any],
            storage_key: str,
            validator_key: str,
            missing_path: str,
            coords: List[float],
        ):
            nonlocal validated_count, total_fields_to_track
            raw_text = self._extract_field_text(document, processed.shape, coords)
            normalized_value = normalize_field(validator_key, raw_text, placeholder=self.placeholder)

            total_fields_to_track += 1
            if normalized_value != self.placeholder:
                validated_count += 1
            else:
                res["missing_fields"].append(missing_path)

            raw_target[storage_key] = raw_text
            extracted_target[storage_key] = normalized_value

        for field, coords in self.roi_config["match_info"].items():
            extract_single_field(
                res["raw_ocr"]["match_info"],
                res["extracted"]["match_info"],
                field,
                field,
                f"match_info.{field}",
                coords,
            )

        for team_key in ["team_a", "team_b"]:
            extract_single_field(
                res["raw_ocr"]["teams"][team_key],
                res["extracted"]["teams"][team_key],
                "name",
                team_key,
                f"teams.{team_key}.name",
                self.roi_config["team_names"][team_key],
            )

            raw_players, extracted_players, missing_players, valid_players = self._extract_player_rows(
                document=document,
                image_shape=processed.shape,
                table_coords=self.roi_config["players"][team_key],
                team_key=team_key,
            )
            res["raw_ocr"]["teams"][team_key]["players"] = raw_players
            res["extracted"]["teams"][team_key]["players"] = extracted_players
            res["missing_fields"].extend(missing_players)
            validated_count += valid_players
            total_fields_to_track += len(extracted_players)

        for official, coords in self.roi_config["officials"].items():
            extract_single_field(
                res["raw_ocr"]["officials"],
                res["extracted"]["officials"],
                official,
                official,
                f"officials.{official}",
                coords,
            )

        for team_key in ["team_a", "team_b"]:
            score_key = f"{team_key}_points"
            extract_single_field(
                res["raw_ocr"]["score"],
                res["extracted"]["score"],
                score_key,
                score_key,
                f"score.{score_key}",
                self.roi_config["scores"][team_key],
            )

        remarks_text = self._extract_field_text(document, processed.shape, self.roi_config["remarks"])
        res["raw_ocr"]["remarks"] = remarks_text
        res["extracted"]["remarks"] = normalize_field("remarks", remarks_text, placeholder=self.placeholder)
        total_fields_to_track += 1
        if res["extracted"]["remarks"] != self.placeholder:
            validated_count += 1
        else:
            res["missing_fields"].append("remarks")

        confidence = calculate_confidence(validated_count, total_fields_to_track)
        res["confidence"] = confidence
        res["confidence_summary"] = confidence
        res["_performance"]["process_time_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(
            "[OCR] Extraction complete. Provider: %s (%s) | Confidence: %.2f%%",
            document.provider,
            document.source,
            res["confidence"],
        )
        return res
