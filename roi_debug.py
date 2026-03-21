"""
ROI Debugging Utility - Visualize field extraction regions on scoresheet images.

This tool helps you calibrate and verify ROI (Region of Interest) coordinates by:
1. Loading an image
2. Drawing rectangles for each field
3. Displaying extracted text for each field
4. Allowing you to adjust coordinates in roi_config.py

Usage:
    python roi_debug.py <image_path>

Example:
    python roi_debug.py media/scoresheet.png
"""

import sys
import cv2
import numpy as np
import os
import json
from core.utils.roi_config import ROI_LAYOUT
from core.utils.ocr_preprocessing import preprocess_image
import pytesseract
from PIL import Image

def get_roi(image, coords):
    """Extract region from image using normalized coordinates."""
    h, w = image.shape[:2]
    ymin, xmin, ymax, xmax = coords
    y1, x1, y2, x2 = int(ymin * h), int(xmin * w), int(ymax * h), int(xmax * w)
    y1, x1 = max(0, y1), max(0, x1)
    y2, x2 = min(h, y2), min(w, x2)
    return image[y1:y2, x1:x2]

def ocr_region(region):
    """Extract text from region using Tesseract."""
    if region.size == 0:
        return ""
    try:
        pil_img = Image.fromarray(region)
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, config="--psm 7")
        text = " ".join([t for t in data['text'] if str(t).strip()]).strip()
        return text
    except Exception as e:
        return f"[OCR Error: {e}]"

def draw_roi_rectangles(image, roi_layout, highlight_field=None):
    """Draw rectangles for all ROI fields on image."""
    vis_image = image.copy()
    h, w = image.shape[:2]
    
    # Flatten the nested dictionary structure
    fields = []
    def flatten_dict(d, prefix=""):
        for k, v in d.items():
            if isinstance(v, dict):
                flatten_dict(v, f"{prefix}{k}.")
            else:
                fields.append((f"{prefix}{k}", v))
    
    flatten_dict(roi_layout)
    
    for field_name, coords in fields:
        ymin, xmin, ymax, xmax = coords
        y1, x1, y2, x2 = int(ymin * h), int(xmin * w), int(ymax * h), int(xmax * w)
        y1, x1 = max(0, y1), max(0, x1)
        y2, x2 = min(h, y2), min(w, x2)
        
        # Color: red for highlighted, green for others
        color = (0, 0, 255) if field_name == highlight_field else (0, 255, 0)
        thickness = 3 if field_name == highlight_field else 1
        
        cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, thickness)
        
        # Label the field
        label = field_name.split('.')[-1][:15]  # Short label
        cv2.putText(vis_image, label, (x1 + 5, y1 + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    return vis_image

def debug_single_field(image_path, field_name):
    """Debug a specific field - show extraction and region."""
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Cannot load image: {image_path}")
        return
    
    print(f"\n{'='*80}")
    print(f"Debugging Field: {field_name}")
    print(f"{'='*80}")
    
    # Find field in ROI_LAYOUT
    def find_field(d, name):
        for k, v in d.items():
            if isinstance(v, dict) and not isinstance(v[next(iter(v))], (list, tuple)):
                result = find_field(v, name)
                if result:
                    return result
            elif k == name or k.endswith('.' + name):
                return v
        return None
    
    coords = find_field(ROI_LAYOUT, field_name)
    if coords is None:
        print(f"❌ Field '{field_name}' not found in ROI_LAYOUT")
        return
    
    # Extract and display
    roi = get_roi(img, coords)
    text = ocr_region(roi)
    
    print(f"Coordinates (normalized): {coords}")
    print(f"ROI Size: {roi.shape}")
    print(f"Extracted Text: '{text}'")
    
    # Show visualization
    vis = draw_roi_rectangles(img, ROI_LAYOUT, field_name)
    output_path = f"roi_debug_{field_name}.png"
    cv2.imwrite(output_path, vis)
    print(f"✅ Visualization saved: {output_path}")

def debug_all_fields(image_path):
    """Debug all fields - create report with extractions."""
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Cannot load image: {image_path}")
        return
    
    # Preprocess
    processed = preprocess_image(img)
    
    print(f"\n{'='*80}")
    print(f"ROI EXTRACTION DEBUG REPORT")
    print(f"{'='*80}")
    print(f"Image: {image_path}")
    print(f"Shape: {img.shape}")
    print(f"{'='*80}\n")
    
    # Flatten and extract all fields
    results = {}
    def flatten_and_extract(d, prefix="", parent_key=""):
        for k, v in d.items():
            full_key = f"{prefix}{k}"
            if isinstance(v, dict) and not isinstance(v[next(iter(v))], (list, tuple)):
                flatten_and_extract(v, f"{full_key}.", k)
            elif isinstance(v, (list, tuple)) and len(v) == 4:
                roi = get_roi(processed, v)
                text = ocr_region(roi)
                results[full_key] = {
                    'coords': v,
                    'size': roi.shape,
                    'text': text,
                    'quality': '✅' if text and text != '__MISSING__' else '⚠️'
                }
    
    flatten_and_extract(ROI_LAYOUT)
    
    # Print results
    for field, data in sorted(results.items()):
        print(f"{data['quality']} {field:30} | Text: '{data['text'][:50]}'")
        print(f"    Coords: {data['coords']} | Size: {data['size']}")
    
    # Summary
    success_count = sum(1 for d in results.values() if d['quality'] == '✅')
    total_count = len(results)
    print(f"\n{'='*80}")
    print(f"Summary: {success_count}/{total_count} fields extracted successfully")
    print(f"{'='*80}\n")
    
    # Save full results
    output_file = "roi_debug_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"📄 Full results saved: {output_file}")
    
    # Create annotated image
    vis = draw_roi_rectangles(img, ROI_LAYOUT)
    output_image = "roi_debug_full_map.png"
    cv2.imwrite(output_image, vis)
    print(f"🖼️  Visualization saved: {output_image}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample:")
        print("  python roi_debug.py media/scoresheet.png")
        print("\nTo debug a specific field:")
        print("  python roi_debug.py media/scoresheet.png tournament")
        sys.exit(1)
    
    image_path = sys.argv[1]
    field_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    if field_name:
        debug_single_field(image_path, field_name)
    else:
        debug_all_fields(image_path)
