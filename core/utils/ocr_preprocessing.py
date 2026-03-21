import cv2
import numpy as np
import logging

logger = logging.getLogger("ocr.preprocessing")

def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def remove_noise(image):
    return cv2.bilateralFilter(image, 9, 75, 75)

def thresholding(image):
    return cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

def clean_borders(image):
    """Removes black borders or scan artifacts from edges."""
    h, w = image.shape[:2]
    # Simple fix: crop 2% from each edge
    oy, ox = int(h * 0.02), int(w * 0.02)
    return image[oy:h-oy, ox:w-ox]

def get_deskew_angle(image):
    """Calculates deskew angle using Hough Line transform for better precision."""
    gray = get_grayscale(image) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
    
    if lines is not None:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2-y1, x2-x1))
            if -45 < angle < 45: angles.append(angle)
        return np.median(angles) if angles else 0
    return 0

def deskew(image, angle=None):
    if angle is None:
        angle = get_deskew_angle(image)
    if abs(angle) < 0.5: return image
    
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    logger.debug("Deskewing image by %.2f degrees", angle)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def morphology_cleanup(image):
    """Uses morphological ops to thicken text and thin grid lines."""
    kernel = np.ones((1,1), np.uint8)
    image = cv2.dilate(image, kernel, iterations=1)
    image = cv2.erode(image, kernel, iterations=1)
    return image

def preprocess_image(image_ndarray):
    """Full pipeline for form extraction."""
    logger.info("Starting advanced image preprocessing pipeline")
    
    # 1. Grayscale & Borders
    gray = get_grayscale(image_ndarray) if len(image_ndarray.shape) == 3 else image_ndarray
    
    # 2. Deskew (Critical for ROI matching)
    angle = get_deskew_angle(gray)
    skew_corrected = deskew(gray, angle)
    
    # 3. Denoise
    denoised = cv2.fastNlMeansDenoising(skew_corrected, None, 10, 7, 21)
    
    # 4. Thresholding (ROI extraction often works best on inverted binary)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 5)
    
    # 5. Clean morphology
    final = morphology_cleanup(thresh)
    
    logger.info("Preprocessing complete.")
    return final
