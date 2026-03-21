import cv2
import numpy as np
import pytesseract
import logging
import json
import os
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from .roi_config import ROI_LAYOUT
from .ocr_preprocessing import preprocess_image, deskew

logger = logging.getLogger("ocr_pipeline.extractor")

class KhoKhoExtractor:
    """Production-ready extractor for Kho Kho Association score sheets."""
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            if os.path.exists(tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            else:
                logger.warning("Tesseract path not found: %s", tesseract_cmd)
        self.roi_config = ROI_LAYOUT
        self.placeholder = "__MISSING__"

    def _get_roi(self, image: np.ndarray, coords: List[float]) -> np.ndarray:
        """Crops the image based on normalized coordinates [y_min, x_min, y_max, x_max]."""
        h, w = image.shape[:2]
        ymin, xmin, ymax, xmax = coords
        y1, x1, y2, x2 = int(ymin * h), int(xmin * w), int(ymax * h), int(xmax * w)
        y1, x1 = max(0, y1), max(0, x1)
        y2, x2 = min(h, y2), min(w, x2)
        return image[y1:y2, x1:x2]

    def _ocr_region(self, region: np.ndarray, config: str = "--psm 7") -> Tuple[str, float]:
        """Performs OCR on a specific region and returns text + confidence."""
        if region.size == 0:
            return "", 0.0
        
        pil_img = Image.fromarray(region)
        try:
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, config=config)
            confidences = [float(c) for c in data['conf'] if c != '-1']
            text = " ".join([t for t in data['text'] if str(t).strip()]).strip()
            
            avg_conf = np.mean(confidences) / 100.0 if confidences else 0.0
            return text, avg_conf
        except Exception as e:
            logger.error("OCR Region failed: %s", e)
            return "", 0.0

    def extract(self, image_path: str) -> Dict[str, Any]:
        """Main entry point for extracting full structured data from a score sheet."""
        logger.info("Extracting Kho-Kho data from: %s", image_path)
        
        img = cv2.imread(image_path)
        if img is None:
            logger.error("Could not load image at: %s", image_path)
            return {"error": f"File not found: {image_path}"}

        # 1. Preprocessing
        processed = preprocess_image(img)
        
        # Intermediate storage to avoid dict mutation type errors
        match_info: Dict[str, Any] = {}
        teams: Dict[str, Any] = {
            "team_a": {"players": []},
            "team_b": {"players": []}
        }
        score: Dict[str, Any] = {}
        officials: Dict[str, Any] = {}
        raw_ocr: Dict[str, str] = {}
        missing_fields: List[str] = []
        all_confidences: List[float] = []

        # 2. Match Info
        for field in ["tournament", "venue", "date", "time", "court_no", "match_no", "section", "group", "toss_won", "choice"]:
            coords = self.roi_config.get(field)
            if coords:
                roi = self._get_roi(processed, coords)
                text, conf = self._ocr_region(roi)
                val = text if text else self.placeholder
                match_info[field] = val
                raw_ocr[field] = text
                all_confidences.append(conf)
                if val == self.placeholder: missing_fields.append(f"match_info.{field}")

        # 3. Teams
        for team_key, team_roi_id in [("team_a", "team_a_name"), ("team_b", "team_b_name")]:
            coords = self.roi_config.get(team_roi_id)
            if coords:
                roi = self._get_roi(processed, coords)
                text, conf = self._ocr_region(roi)
                teams[team_key]["name"] = text if text else self.placeholder
                all_confidences.append(conf)

        # 4. Players
        for team_key, roi_id in [("team_a", "team_a_players"), ("team_b", "team_b_players")]:
            coords = self.roi_config.get(roi_id)
            if coords:
                roi = self._get_roi(processed, coords)
                raw_table, conf = self._ocr_region(roi, config="--psm 6")
                lines = raw_table.splitlines()
                for i, line in enumerate(lines[:15]):
                    teams[team_key]["players"].append({
                        "no": i + 1,
                        "name": line.strip(),
                        "raw": line,
                        "confidence": conf
                    })

        # 5. Officials
        off_coords_map = self.roi_config.get("officials", {})
        if isinstance(off_coords_map, dict):
            for off_title, coords in off_coords_map.items():
                roi = self._get_roi(processed, coords)
                text, conf = self._ocr_region(roi)
                officials[off_title] = text if text else self.placeholder
                all_confidences.append(conf)

        # 6. Scores
        for score_key, roi_id in [("team_a_points", "points_team_a"), ("team_b_points", "points_team_b")]:
            coords = self.roi_config.get(roi_id)
            if coords:
                roi = self._get_roi(processed, coords)
                text, conf = self._ocr_region(roi, config="--psm 7")
                val: Any = self.placeholder
                try:
                    val = int("".join(filter(str.isdigit, text)))
                except (ValueError, TypeError):
                    pass
                score[score_key] = val
                all_confidences.append(conf)

        # Remarks
        remarks = self.placeholder
        rem_coords = self.roi_config.get("remarks")
        if rem_coords:
            roi = self._get_roi(processed, rem_coords)
            text, _ = self._ocr_region(roi, config="--psm 6")
            remarks = text if text else self.placeholder

        # Final assembly
        return {
            "match_info": match_info,
            "teams": teams,
            "score": score,
            "officials": officials,
            "remarks": remarks,
            "raw_ocr": raw_ocr,
            "missing_fields": missing_fields,
            "confidence_summary": float(np.mean(all_confidences)) if all_confidences else 0.0
        }

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    t_path = os.getenv("TESSERACT_PATH")
    extractor = KhoKhoExtractor(t_path)
    sample_img = "test_sheet.png"
    if os.path.exists(sample_img):
        data = extractor.extract(sample_img)
        print(json.dumps(data, indent=2))
    else:
        print(f"Sample image not found: {sample_img}")
