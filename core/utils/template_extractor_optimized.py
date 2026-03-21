"""
Optimized Kho Kho Score Sheet Extractor with parallel processing and caching.
"""
import cv2
import numpy as np
import pytesseract
import logging
import json
import os
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import time

from .roi_config import ROI_LAYOUT
from .ocr_preprocessing import preprocess_image, deskew

logger = logging.getLogger("ocr_pipeline.extractor")

class KhoKhoExtractorOptimized:
    """Optimized extractor with parallel processing and caching."""
    
    # Class-level cache for OCR results
    _ocr_cache = {}
    _max_cache_size = 1000
    
    def __init__(self, tesseract_cmd: Optional[str] = None, fast_mode: bool = False, use_threading: bool = True):
        """
        Initialize extractor.
        
        Args:
            tesseract_cmd: Path to Tesseract executable
            fast_mode: Skip heavy preprocessing (deskew, morphology)
            use_threading: Enable parallel region extraction
        """
        if tesseract_cmd:
            if os.path.exists(tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            else:
                logger.warning("Tesseract path not found: %s", tesseract_cmd)
        
        self.roi_config = ROI_LAYOUT
        self.placeholder = "__MISSING__"
        self.fast_mode = fast_mode
        self.use_threading = use_threading
        self.max_workers = 4  # Parallel threads for OCR

    def _get_roi(self, image: np.ndarray, coords: List[float]) -> np.ndarray:
        """Crops the image based on normalized coordinates."""
        h, w = image.shape[:2]
        ymin, xmin, ymax, xmax = coords
        y1, x1, y2, x2 = int(ymin * h), int(xmin * w), int(ymax * h), int(xmax * w)
        y1, x1 = max(0, y1), max(0, x1)
        y2, x2 = min(h, y2), min(w, x2)
        return image[y1:y2, x1:x2]

    def _get_cache_key(self, region: np.ndarray, config: str) -> str:
        """Generate cache key for OCR region."""
        try:
            region_hash = hash(region.tobytes()[:256]) if region.size > 0 else 0
            return f"{region_hash}_{config}"
        except:
            return None

    def _ocr_region_cached(self, region: np.ndarray, config: str = "--psm 7") -> Tuple[str, float]:
        """Performs OCR on a specific region with caching."""
        if region.size == 0:
            return "", 0.0
        
        # Try cache first
        cache_key = self._get_cache_key(region, config)
        if cache_key and cache_key in self._ocr_cache:
            return self._ocr_cache[cache_key]
        
        # Perform OCR
        result = self._ocr_region(region, config)
        
        # Cache result
        if cache_key and len(self._ocr_cache) < self._max_cache_size:
            self._ocr_cache[cache_key] = result
        
        return result

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
            logger.error("❌ OCR Region failed: %s", e)
            return "", 0.0

    def _extract_field(self, field_name: str, roi_id: str, processed: np.ndarray, config: str = "--psm 7") -> Tuple[str, float]:
        """Extract a single field - designed for parallel processing."""
        try:
            coords = self.roi_config.get(roi_id)
            if not coords:
                return field_name, self.placeholder, 0.0
            
            roi = self._get_roi(processed, coords)
            text, conf = self._ocr_region_cached(roi, config)
            val = text if text else self.placeholder
            
            if val == self.placeholder:
                logger.warning("⚠️  Missing: %s", field_name)
            
            return field_name, val, conf
        except Exception as e:
            logger.error("❌ Field extraction failed for %s: %s", field_name, e)
            return field_name, self.placeholder, 0.0

    def _extract_regions_parallel(self, regions_spec: List[Tuple[str, str, str]], processed: np.ndarray) -> Dict[str, Tuple[str, float]]:
        """Extract multiple regions in parallel."""
        results = {}
        
        if not self.use_threading or len(regions_spec) < 2:
            # Sequential extraction for small batches
            for field_name, roi_id, config in regions_spec:
                _, val, conf = self._extract_field(field_name, roi_id, processed, config)
                results[field_name] = (val, conf)
        else:
            # Parallel extraction
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(regions_spec))) as executor:
                futures = {
                    executor.submit(self._extract_field, field_name, roi_id, processed, config): field_name
                    for field_name, roi_id, config in regions_spec
                }
                
                for future in as_completed(futures):
                    try:
                        field_name, val, conf = future.result()
                        results[field_name] = (val, conf)
                    except Exception as e:
                        logger.error("❌ Parallel extraction error: %s", e)
        
        return results

    def extract(self, image_path: str) -> Dict[str, Any]:
        """Main entry point for extracting full structured data from a score sheet."""
        logger.info("="*80)
        logger.info("🚀 STARTING OPTIMIZED EXTRACTION (fast_mode=%s, threading=%s)", 
                   self.fast_mode, self.use_threading)
        logger.info("="*80)
        logger.info("Image Path: %s", image_path)
        
        start_time = time.time()
        
        img = cv2.imread(image_path)
        if img is None:
            logger.error("❌ Could not load image at: %s", image_path)
            return {"error": f"File not found: {image_path}"}

        logger.info("✅ Image loaded. Shape: %s (%.2fMB)", img.shape, img.nbytes / 1_000_000)

        # 1. Preprocessing (optimized)
        pre_start = time.time()
        processed = preprocess_image(img, fast_mode=self.fast_mode)
        pre_time = time.time() - pre_start
        logger.info("✅ Preprocessing completed in %.2fs", pre_time)
        
        # Initialize result structures
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

        # 2. Parallel Match Info Extraction
        logger.info("📋 Step 2: Extracting Match Information (parallel)...")
        match_fields = [
            (field, field, "--psm 7")
            for field in ["tournament", "venue", "date", "time", "court_no", "match_no", "section", "group", "toss_won", "choice"]
        ]
        
        extract_start = time.time()
        match_results = self._extract_regions_parallel(match_fields, processed)
        
        for field, (val, conf) in match_results.items():
            match_info[field] = val
            raw_ocr[field] = val if val != self.placeholder else ""
            all_confidences.append(conf)
            if val == self.placeholder:
                missing_fields.append(f"match_info.{field}")
        
        match_time = time.time() - extract_start
        logger.info("✅ Match info extracted in %.2fs", match_time)

        # 3. Team Names (parallel)
        logger.info("📋 Step 3: Extracting Team Names...")
        team_fields = [
            ("team_a_name", "team_a_name", "--psm 7"),
            ("team_b_name", "team_b_name", "--psm 7"),
        ]
        
        team_results = self._extract_regions_parallel(team_fields, processed)
        for field, (val, conf) in team_results.items():
            team_key = "team_a" if "team_a" in field else "team_b"
            teams[team_key]["name"] = val
            all_confidences.append(conf)
        
        logger.info("✅ Teams extracted: %s vs %s", teams["team_a"].get("name", "?"), teams["team_b"].get("name", "?"))

        # 4. Players (parallel extraction, but table parsing is sequential)
        logger.info("📋 Step 4: Extracting Players...")
        players_start = time.time()
        
        for team_key, roi_id in [("team_a", "team_a_players"), ("team_b", "team_b_players")]:
            coords = self.roi_config.get(roi_id)
            if coords:
                roi = self._get_roi(processed, coords)
                raw_table, conf = self._ocr_region_cached(roi, config="--psm 6")
                all_confidences.append(conf)
                
                lines = raw_table.splitlines()
                for i, line in enumerate(lines[:15]):
                    teams[team_key]["players"].append({
                        "no": i + 1,
                        "name": line.strip(),
                        "raw": line,
                        "confidence": conf
                    })
                
                logger.info("✅ %s: %d players extracted", team_key.upper(), len(teams[team_key]["players"]))
        
        players_time = time.time() - players_start

        # 5. Officials (parallel)
        logger.info("📋 Step 5: Extracting Officials...")
        off_coords_map = self.roi_config.get("officials", {})
        if isinstance(off_coords_map, dict):
            official_fields = [
                (off_title, off_title, "--psm 7")  # Using roi_id same as field for nested lookup
                for off_title in off_coords_map.keys()
            ]
            
            # Custom extraction for nested officials config
            for off_title, coords in off_coords_map.items():
                roi = self._get_roi(processed, coords)
                text, conf = self._ocr_region_cached(roi, "--psm 7")
                off_name = text if text else self.placeholder
                officials[off_title] = off_name
                all_confidences.append(conf)
            
            logger.info("✅ Officials extracted: %d positions", len(officials))

        # 6. Scores (parallel)
        logger.info("📋 Step 6: Extracting Scores...")
        score_fields = [
            ("team_a_points", "points_team_a", "--psm 7"),
            ("team_b_points", "points_team_b", "--psm 7"),
        ]
        
        score_results = self._extract_regions_parallel(score_fields, processed)
        for field, (val, conf) in score_results.items():
            try:
                score_val = int("".join(filter(str.isdigit, val))) if val != self.placeholder else self.placeholder
            except (ValueError, TypeError):
                score_val = self.placeholder
            
            score_key = field.replace("_points", "_points")
            score[score_key] = score_val
            all_confidences.append(conf)
        
        logger.info("✅ Scores extracted: Team A=%s, Team B=%s", score.get("team_a_points"), score.get("team_b_points"))

        # 7. Remarks
        logger.info("📋 Step 7: Extracting Remarks...")
        remarks = self.placeholder
        rem_coords = self.roi_config.get("remarks")
        if rem_coords:
            roi = self._get_roi(processed, rem_coords)
            text, _ = self._ocr_region_cached(roi, config="--psm 6")
            remarks = text if text else self.placeholder

        # Calculate stats
        confidence_summary = float(np.mean(all_confidences)) if all_confidences else 0.0
        total_time = time.time() - start_time

        # Final assembly
        final_payload = {
            "match_info": match_info,
            "teams": teams,
            "score": score,
            "officials": officials,
            "remarks": remarks,
            "raw_ocr": raw_ocr,
            "missing_fields": missing_fields,
            "confidence_summary": confidence_summary,
            # Performance metrics
            "_performance": {
                "total_time_ms": int(total_time * 1000),
                "preprocess_time_ms": int(pre_time * 1000),
                "match_extraction_ms": int(match_time * 1000),
                "players_extraction_ms": int(players_time * 1000),
                "cache_size": len(self._ocr_cache),
                "fast_mode": self.fast_mode,
                "threading_enabled": self.use_threading,
            }
        }
        
        # Summary logging
        logger.info("="*80)
        logger.info("✅ EXTRACTION COMPLETE")
        logger.info("="*80)
        logger.info("Overall Confidence: %.1f%%", confidence_summary * 100)
        logger.info("Missing Fields: %d", len(missing_fields))
        logger.info("⏱️  Performance:")
        logger.info("  - Total: %.2fs", total_time)
        logger.info("  - Preprocess: %.2fs", pre_time)
        logger.info("  - Extraction: %.2fs", total_time - pre_time)
        logger.info("  - Cache size: %d", len(self._ocr_cache))
        logger.info("="*80)
        
        return final_payload

    @classmethod
    def clear_cache(cls):
        """Clear OCR cache to free memory."""
        cls._ocr_cache.clear()
        logger.info("✅ OCR cache cleared")

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(cls._ocr_cache),
            "max_size": cls._max_cache_size,
            "usage_percent": (len(cls._ocr_cache) / cls._max_cache_size) * 100,
        }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    t_path = os.getenv("TESSERACT_PATH")
    
    # Test with optimized extractor
    extractor = KhoKhoExtractorOptimized(t_path, fast_mode=False, use_threading=True)
    sample_img = "test_sheet.png"
    if os.path.exists(sample_img):
        data = extractor.extract(sample_img)
        print(json.dumps(data, indent=2))
    else:
        print(f"Sample image not found: {sample_img}")
