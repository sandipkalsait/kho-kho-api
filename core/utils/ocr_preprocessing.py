import cv2
import numpy as np
import logging
from functools import lru_cache

logger = logging.getLogger("ocr.preprocessing")

# Cache for Hough line angle calculation
_deskew_cache = {}

def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def adaptive_thresholding(image):
    """Applies adaptive thresholding for high contrast."""
    return cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

def remove_table_lines(image):
    """Uses morphological operations to remove horizontal and vertical lines."""
    # Create kernels for line detection
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

    # Detect horizontal lines
    detect_horizontal = cv2.morphologyEx(image, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    cnts = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(image, [c], -1, (0,0,0), 3)

    # Detect vertical lines
    detect_vertical = cv2.morphologyEx(image, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    cnts = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(image, [c], -1, (0,0,0), 3)
        
    return image

def deskew(image):
    """Deskews the image based on detected text orientation."""
    coords = np.column_stack(np.where(image > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def sharpen(image):
    """Applies a sharpening kernel to enhance text edges."""
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    return cv2.filter2D(image, -1, kernel)

def preprocess_image(image_ndarray):
    """Full production pipeline for scoresheet preprocessing."""
    logger.info("Running strict preprocessing pipeline")
    
    # 1. Grayscale
    gray = get_grayscale(image_ndarray) if len(image_ndarray.shape) == 3 else image_ndarray
    
    # 2. Adaptive Threshold (high contrast)
    thresh = adaptive_thresholding(gray)
    
    # 3. Remove table lines (Morphology)
    line_free = remove_table_lines(thresh)
    
    # 4. Deskew
    deskewed = deskew(line_free)
    
    # 5. Sharpen
    sharpened = sharpen(deskewed)
    
    # 6. Invert back for Tesseract (wants black text on white background usually, 
    # but we extracted white on black in step 2. Let's return high contrast black on white.)
    final = cv2.bitwise_not(sharpened)
    
    logger.info("✅ Preprocessing complete (shape: %s)", final.shape)
    return final
