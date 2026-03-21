import cv2
import numpy as np
import logging
from functools import lru_cache

logger = logging.getLogger("ocr.preprocessing")

# Cache for Hough line angle calculation
_deskew_cache = {}

def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def remove_noise(image):
    """Faster denoising - use fastNlMeans instead of bilateral filter."""
    return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)

def thresholding(image):
    return cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

def clean_borders(image):
    """Removes black borders or scan artifacts from edges."""
    h, w = image.shape[:2]
    # Simple fix: crop 2% from each edge
    oy, ox = int(h * 0.02), int(w * 0.02)
    return image[oy:h-oy, ox:w-ox]

def get_deskew_angle(image, use_cache=True):
    """Calculates deskew angle using Hough Line transform with optional caching."""
    gray = get_grayscale(image) if len(image.shape) == 3 else image
    
    # Create cache key based on image shape (for same format documents)
    cache_key = (gray.shape, hash(gray.tobytes()[:256])) if use_cache else None
    
    if cache_key and cache_key in _deskew_cache:
        logger.debug("⚡ Using cached deskew angle")
        return _deskew_cache[cache_key]
    
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
    
    angle = 0
    if lines is not None:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle_val = np.degrees(np.arctan2(y2-y1, x2-x1))
            if -45 < angle_val < 45: 
                angles.append(angle_val)
        angle = np.median(angles) if angles else 0
    
    if cache_key:
        _deskew_cache[cache_key] = angle
    
    return angle

def deskew(image, angle=None):
    """Deskew image - skip if angle is minimal."""
    if angle is None:
        angle = get_deskew_angle(image)
    if abs(angle) < 0.5: 
        return image
    
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    logger.debug("Deskewing image by %.2f degrees", angle)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def morphology_cleanup(image):
    """Lightweight morphological cleanup."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    image = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=1)
    return image

def preprocess_image(image_ndarray, fast_mode=False):
    """
    Full pipeline for form extraction.
    
    Args:
        image_ndarray: Input image
        fast_mode: If True, skip deskew and heavy denoising
    
    Returns:
        Preprocessed image
    """
    logger.info("📋 Starting image preprocessing (fast_mode=%s)", fast_mode)
    
    # 1. Grayscale
    gray = get_grayscale(image_ndarray) if len(image_ndarray.shape) == 3 else image_ndarray
    
    # 2. Deskew (skip in fast mode)
    if not fast_mode:
        angle = get_deskew_angle(gray, use_cache=True)
        skew_corrected = deskew(gray, angle)
        logger.debug("✅ Deskew completed (angle: %.2f°)", angle)
    else:
        skew_corrected = gray
        logger.debug("⚡ Skipping deskew (fast mode)")
    
    # 3. Light denoise
    if fast_mode:
        logger.debug("⚡ Using fast denoise")
        denoised = cv2.GaussianBlur(skew_corrected, (5, 5), 0)
    else:
        logger.debug("Running standard denoise")
        denoised = remove_noise(skew_corrected)
    
    # 4. Thresholding (faster - single pass)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 5)
    
    # 5. Clean morphology
    if not fast_mode:
        final = morphology_cleanup(thresh)
        logger.debug("✅ Morphology cleanup completed")
    else:
        final = thresh
        logger.debug("⚡ Skipping morphology (fast mode)")
    
    logger.info("✅ Preprocessing complete (shape: %s)", final.shape)
    return final
