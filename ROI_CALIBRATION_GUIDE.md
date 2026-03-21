# ROI Calibration Guide

## Problem

Your scoresheet fields are being extracted from incorrect regions, resulting in garbled text like "oO oO =e" (checkboxes) and "jaw SST MENS = WOMENS" (labels). The ROI (Region of Interest) coordinates need to be calibrated to match your actual scoresheet layout.

## Solution: 3-Step Calibration Process

### Step 1: Visualize Current ROI Regions

Run the debug tool to see which regions each field is currently mapping to:

```bash
cd c:\Users\Abhishek\Desktop\lego\kho-kho-api
python roi_debug.py media/3f4d68e1-be70-4708-b077-21693e7429e1_40adfb49-bdf7-4cbf-b329-2495f615e546
```

This creates:
- `roi_debug_full_map.png` - Visual map showing all ROI rectangles
- `roi_debug_results.json` - Detailed extraction results for each field

### Step 2: Analyze the Visualization

Look at `roi_debug_full_map.png` and identify:
1. Which colored rectangles are on the CORRECT field locations
2. Which rectangles are on WRONG locations (checkboxes, labels, margins)

For example, if you see:
- Rectangle on text field ✅ → Coordinates are correct
- Rectangle on checkbox/symbol ❌ → Coordinates need adjustment
- Rectangle on white space ❌ → Coordinates need adjustment

### Step 3: Adjust Coordinates in `roi_config.py`

The coordinate system uses normalized values [y_min, x_min, y_max, x_max] where:
- 0.0 = top/left edge
- 1.0 = bottom/right edge
- Example: [0.10, 0.25, 0.14, 0.42] = 10-14% down, 25-42% across

To adjust a field:

```python
# Before (incorrect)
"date": [0.10, 0.20, 0.13, 0.35]

# After (adjusted to actual location)
"date": [0.10, 0.25, 0.14, 0.42]  # Adjusted down and right
```

## Standard Scoresheet Layout (Reference)

Most Kho Kho scoresheets follow this structure:

```
0%  ┌─────────────────────────────────────────────────┐
    │  TOURNAMENT NAME (header)                       │ ~5%
    │  VENUE                                           │ ~10%
5%  ├──────────────────────────────────────────────────┤
    │ Date | Time | Court | Match No                  │ ~15%
10% ├──────────────────────────────────────────────────┤
    │ Section | Group | Toss Won | Choice            │ ~20%
15% ├──────────────────────────────────────────────────┤
    │ TEAM A NAME        │        TEAM B NAME         │ ~25%
20% ├────────────────────┼─────────────────────────────┤
    │ Players 1-15       │       Players 1-15         │
    │ (roster table)     │       (roster table)        │ ~70%
70% ├────────────────────┼─────────────────────────────┤
    │ Officials/Staff    │  Scorer/Umpire/Referee     │ ~80%
75% ├────────────────────┼─────────────────────────────┤
    │ POINTS: XX         │  POINTS: XX                │ ~85%
80% ├──────────────────────────────────────────────────┤
    │ REMARKS/COMMENTS (wide field)                  │ ~95%
90% └──────────────────────────────────────────────────┘
```

## Quick Calibration Workflow

1. **Identify problem field** → Look at extraction results showing garbled text
2. **Find region in visualization** → Check `roi_debug_full_map.png`
3. **Calculate correct coordinates** → Estimate % position of actual field
4. **Update roi_config.py** → Change coordinate values
5. **Test extraction** → Re-upload image and check if text improves
6. **Repeat** → Refine until confident

## Coordinate Adjustment Examples

### Example 1: Field reading checkboxes instead of text field

**Symptom:** "tournament": "oO oO =e" (checkbox symbols)

**Fix:**
```python
# The rectangle is too far left/up, capturing checkbox area
# Original: [0.03, 0.20, 0.08, 0.85]  ← Too narrow top margin

# Adjusted: [0.02, 0.25, 0.06, 0.95]  ← More centered, with padding
"tournament": [0.02, 0.25, 0.06, 0.95]
```

### Example 2: Field includes label text

**Symptom:** "section": "jaw SST MENS = WOMENS" (partial label + field)

**Fix:**
```python
# The rectangle includes the label area
# Original: [0.13, 0.20, 0.15, 0.40]  ← Includes label area

# Adjusted: [0.14, 0.25, 0.18, 0.42]  ← Below label, field only
"section": [0.14, 0.25, 0.18, 0.42]
```

### Example 3: Field reading partial/garbled text

**Symptom:** Low confidence, mixed characters

**Fix:**
```python
# The rectangle is too small or misaligned
# Original: [0.10, 0.20, 0.13, 0.35]  ← Too narrow

# Adjusted: [0.10, 0.20, 0.14, 0.42]  ← Taller and wider
"date": [0.10, 0.20, 0.14, 0.42]
```

## Manual Method (No Visualization)

If you prefer manual calibration without running the debug tool:

1. Open your scoresheet image in an image viewer
2. Use pixel ruler or measure tool
3. Identify actual position of each field in pixels
4. Calculate normalized coordinates:
   ```
   norm_x_min = pixel_x_min / image_width
   norm_y_min = pixel_y_min / image_height
   norm_x_max = pixel_x_max / image_width
   norm_y_max = pixel_y_max / image_height
   ```
5. Round to 2 decimal places
6. Update roi_config.py with normalized coordinates

## Testing After Adjustment

After updating coordinates:

```bash
# 1. Verify Django settings
python manage.py check

# 2. Re-upload same scoresheet image
# Should see improved OCR results with better confidence scores

# 3. Check logs for extraction quality
# Look for fewer "⚠️ Missing:" warnings
```

## Common Issues & Fixes

| Problem | Cause | Solution |
|---------|-------|----------|
| "oO oO =e" (symbols) | Rectangle on checkbox area | Shift right/down, increase x/y_min |
| Partial text ("JAW SST") | Rectangle includes label | Increase y_min to skip labels |
| Empty result | Rectangle on white space | Adjust coordinates to actual field |
| Garbled mixed text | Rectangle too large/small | Narrow the rectangle boundaries |
| Very low confidence (<5%) | Reading wrong field entirely | Compare with visualization and readjust |

## Next Steps

1. Run roi_debug.py on your test image to generate visualizations
2. Study the `roi_debug_full_map.png` output
3. Identify which fields are correctly mapped and which aren't
4. Adjust incorrect field coordinates in roi_config.py
5. Re-test extraction to verify improvements
6. Iterate until confidence scores improve significantly

Need help? Make sure to:
- Save all changes to roi_config.py before re-testing
- Use the debug tool visualization to verify changes
- Test with the SAME image file for consistency
- Check logs for specific field extraction details
