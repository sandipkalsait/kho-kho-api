import cv2
import numpy as np
import logging

logger = logging.getLogger("ocr.preprocessing")

def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def remove_noise(image):
    return cv2.bilateralFilter(image, 9, 75, 75)

def thresholding(image):
    return cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

def deskew(image):
    coords = np.column_stack(np.where(image > 0))
    if not coords.any(): return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    logger.debug("Deskewing image by %.2f degrees", angle)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def preprocess_image(image_ndarray):
    """Refines a CV2 ndarray image for better OCR extraction."""
    logger.info("Starting image preprocessing pipeline")
    gray = get_grayscale(image_ndarray) if len(image_ndarray.shape) == 3 else image_ndarray
    denoised = remove_noise(gray)
    skew_corrected = deskew(denoised)
    thresh = thresholding(skew_corrected)
    logger.info("Preprocessing complete.")
    return thresh
