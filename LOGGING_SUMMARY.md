# 📋 Kho-Kho OCR Pipeline - Comprehensive Logging Implementation

## 🎯 Summary
Added comprehensive logging throughout the entire OCR extraction and data processing pipeline. **All extracted data is now logged with detailed information** including field-by-field extraction details, confidence scores, missing fields, data changes, and audit trails.

---

## 📝 What Gets Logged

### ✅ **Extraction Pipeline** (template_extractor.py)
When an image is uploaded and processed:
- ✅ Image loading confirmation and dimensions
- ✅ Preprocessing completion
- ✅ **Match Information** - tournament, venue, date, time, court details, toss info
- ✅ **Team Names** - with confidence scores
- ✅ **Player Lists** - all players per team with raw OCR text
- ✅ **Officials** - umpires, scorers, etc.
- ✅ **Scores** - team points with raw text
- ✅ **Remarks** - any additional notes
- ✅ **Confidence Scores** - for each field and overall
- ✅ **Missing Fields** - any required data that wasn't extracted
- ✅ **Complete JSON Payload** - final structured data

### ✅ **API Pipeline** (ocr_pipeline_views.py)

#### Upload Endpoint (POST /api/upload/)
- 📤 Request metadata (Content-Type, User-Agent, IP)
- 📥 Image acquisition method (multipart or base64)
- 🔐 Base64 decoding details
- 💾 Database storage confirmation
- ⏱️ Total processing time

#### Review Endpoint (GET /api/review/)
- 📖 Request lookup status
- 🔍 Data source (raw extracted vs human-reviewed)
- 📋 Complete extracted data payload
- 📊 Confidence scores and missing fields

#### Update Endpoint (PUT /api/review/)
- 👤 Reviewer information
- 🔄 Field-level changes (old vs new values)
- 📝 Audit trail creation
- 💾 Database update confirmation

#### Submit Endpoint (POST /api/submit/)
- ✅ Final validation steps
- 🔍 Completeness checks
- 📦 Final payload selection (reviewed vs extracted)
- 💾 Status update to COMPLETED

#### Audit Logs (GET /api/audit/)
- 📋 Complete audit trail enumeration
- 👤 User information for each change
- 📅 Timestamps
- 📊 Before/after values

---

## 📂 Log File Location
```
📁 kho-kho-api/logs/
   └── 📄 kho_kho.log (rotating - 5MB max, 5 backups)
```

---

## 🎨 Log Formatting Features

### Visual Indicators
```
✅ - Success/completed operations
❌ - Errors/failures  
⚠️  - Warnings/missing data
📋 - Processing steps
📤 - Upload operations
📥 - Data intake
📖 - Data retrieval
🔄 - Changes/updates
🔐 - Security operations
💾 - Database operations
🔍 - Validation
📊 - Statistics/metrics
⏱️  - Timing information
🎉 - Major milestones
```

### Log Format
```
[TIMESTAMP] LEVEL [MODULE:LINE] Message
```

Example:
```
[2026-03-21 14:25:33] INFO [ocr_pipeline_views:150] ✅ Template extraction complete
[2026-03-21 14:25:34] DEBUG [template_extractor:85] Tournament: "National Championship 2026"
```

---

## 📊 Example Log Output

### Upload Success Flow
```
================================================================================
📤 NEW IMAGE UPLOAD REQUEST RECEIVED
================================================================================
Content-Type: multipart/form-data
User-Agent: PostmanClient/10.0
Remote Address: 192.168.1.100
--------------------------------------------------------------------------------
📥 STEP 1: ACQUIRING IMAGE DATA
--------------------------------------------------------------------------------
✅ Multipart file detected
Filename: scoresheet_2026.jpg
File Size: 2456789 bytes
Content Type: image/jpeg
✅ Multipart file decoded successfully
Image Saved to: uploads/abc-123-def_scoresheet_2026.jpg

🚀 STARTING KHO-KHO EXTRACTION PIPELINE
================================================================================
Image Path: media/temp12345.png
✅ Image loaded successfully. Shape: (1080, 1920, 3)

📋 Step 1: Preprocessing image...
✅ Image preprocessing completed. Processed shape: (1080, 1920, 3)

📋 Step 2: Extracting Match Information...
✅ tournament: 'National Championship 2026' (confidence: 0.95)
✅ date: '21-03-2026' (confidence: 0.98)
✅ venue: 'Mumbai Sports Complex' (confidence: 0.91)

📋 Step 3: Extracting Team Names...
✅ TEAM_A name extracted: 'Tigers FC'
✅ TEAM_B name extracted: 'Eagles United'

📋 Step 4: Extracting Players Data...
✅ TEAM_A: 11 players extracted (confidence: 0.87)
  Players: [
    {"no": 1, "name": "Raj Kumar", ...},
    {"no": 2, "name": "Arun Singh", ...},
    ...
  ]

✅ EXTRACTION COMPLETE - FINAL SUMMARY
================================================================================
Overall Confidence Score: 92.34%
Missing Fields Count: 0
Total Confidences Collected: 24

FINAL EXTRACTED PAYLOAD:
{
  "match_info": {...},
  "teams": {...},
  "score": {...},
  "officials": {...},
  "remarks": "Match completed successfully",
  ...
}

================================================================================
💾 STORING EXTRACTED DATA IN DATABASE
================================================================================
Generated Request ID: 550e8400-e29b-41d4-a716-446655440000
User ID: user@example.com
Document Type: scoresheet
Image URL: uploads/abc-123-def_scoresheet_2026.jpg
✅ UploadRequest created in DB: 550e8400-e29b-41d4-a716-446655440000
✅ ExtractedData record created in DB
  - Confidence Score stored: 0.9234
  - Missing Fields stored: []

⏱️  Total Processing Time: 8432 ms
🎉 OCR UPLOAD AND EXTRACTION COMPLETE
================================================================================
```

---

## 🚀 How to View the Logs

### Real-time Monitoring
```bash
# Windows PowerShell
Get-Content logs/kho_kho.log -Wait -Tail 50

# Git Bash/WSL
tail -f logs/kho_kho.log
```

### View Last N Entries
```bash
# Last 100 lines
Get-Content logs/kho_kho.log -Tail 100

# Get entries for specific request
Select-String "550e8400-e29b-41d4-a716-446655440000" logs/kho_kho.log
```

### Search for Specific Events
```bash
# Find all extraction completions
Select-String "EXTRACTION COMPLETE" logs/kho_kho.log

# Find all errors
Select-String "ERROR|❌" logs/kho_kho.log

# Find specific user's activity
Select-String "user@example.com" logs/kho_kho.log
```

---

## 📋 Console Output
While running, you'll see structured logs:
- **Console**: Rich formatted output (real-time, colorized)
- **File**: Verbose format (4 backups, auto-rotate at 5MB)

---

## 🎓 Developer Notes

### Logging Configuration
Located in: `kho_kho_project/settings.py`

```python
LOGGING = {
    'loggers': {
        'ocr_pipeline': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',  # Detailed logging
            'propagate': True,
        },
    }
}
```

### Log Levels
- **DEBUG** - Detailed field-by-field extraction info
- **INFO** - Major steps and confirmations
- **WARNING** - Missing fields, unusual conditions
- **ERROR** - Extraction failures, validation errors
- **CRITICAL** - System failures

---

## ✨ Key Benefits

✅ **Complete Audit Trail** - Every operation is logged
✅ **Debugging** - Easy to trace issues with detailed field logging
✅ **Performance** - Processing time metrics included
✅ **Data Integrity** - Before/after values for all changes
✅ **Visual Clarity** - Emoji indicators and formatted sections
✅ **Compliance** - Full audit log of who changed what and when

---

## 📦 Modified Files

1. **core/utils/template_extractor.py** - `KhoKhoExtractor.extract()`
   - Added step-by-step logging for each extraction phase
   - Field-by-field logging with confidence scores
   - Final payload dump

2. **core/ocr_pipeline_views.py** - All API endpoints
   - `upload_image()` - Request handling and extraction
   - `review_get()` - Data retrieval
   - `review_put()` - Human review & updates
   - `submit_request()` - Final validation
   - `audit_logs()` - Audit trail retrieval

---

**Last Updated:** 2026-03-21  
**Status:** ✅ Production Ready - All syntax validated
