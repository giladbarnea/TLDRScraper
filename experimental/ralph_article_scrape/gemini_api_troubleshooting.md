---
last_updated: 2025-11-14 16:24, 722a1a0
---
# Gemini API Troubleshooting Results

**Date:** 2025-10-25
**Issue:** Gemini API returns 403 Forbidden on all requests

## What We Tried

### 1. Environment Variables ✓
```bash
GEMINI_API_TOKEN="AIzaSyADr47Pi-Htd39GtrgOa6inWlMuxKR-oXE"
GEMINI_API_KEY="AIzaSyADr47Pi-Htd39GtrgOa6inWlMuxKR-oXE"
```
Both are set correctly.

### 2. Direct API Testing ✗
```bash
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"What is 2+2?"}]}]}' \
     -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GEMINI_API_TOKEN}"
```
**Result:** `Error 403 (Forbidden)!!1`

### 3. List Models Endpoint ✗
```bash
curl "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_TOKEN}"
```
**Result:** `Error 403 (Forbidden)!!1`

### 4. Gemini CLI ✗
```bash
GEMINI_API_KEY=$GEMINI_API_TOKEN gemini "What is 2+2?"
```
**Result:** `Error when talking to Gemini API`

### 5. Gemini CLI with File Input ✗
```bash
gemini "Describe this image: @media_02.jpg"
```
**Result:** `Error when talking to Gemini API`

## Root Cause

The API key is returning **403 Forbidden** on ALL endpoints, including basic operations like listing models. This indicates:

### Most Likely Issues (in order):

1. **Generative Language API Not Enabled**
   - The API key's Google Cloud project doesn't have the Generative Language API enabled
   - Solution: Go to Google Cloud Console → APIs & Services → Enable "Generative Language API"

2. **API Key Restrictions**
   - The key may be restricted to specific IPs, domains, or applications
   - Solution: Check API key restrictions in Google Cloud Console

3. **Billing Not Enabled**
   - The Google Cloud project may not have billing enabled
   - Solution: Enable billing in Google Cloud Console

4. **API Key Invalid/Expired**
   - The key may have been revoked or expired
   - Solution: Generate a new API key at https://aistudio.google.com/app/apikey

5. **Quota Exceeded**
   - Less likely since even listing models fails
   - Solution: Check quotas in Google Cloud Console

## What We Accomplished Despite API Issues

✓ **Downloaded 12 media files locally** (1.4 MB total):
- media_02.jpg - Ralph Wiggum hero image (121 KB)
- media_08.png - Playground diagram (261 KB)
- media_11.jpg - CURSED language image (110 KB)
- media_13.jpg - Secure code generation (113 KB)
- media_15.jpg - Coding agent workshop (190 KB)
- media_17.jpg - MCP servers dancing (309 KB)
- And 6 more images...

✓ **Created download infrastructure** with redirect following
✓ **Identified and cataloged** all media elements
✓ **Prepared files** for description (local paths ready)

## Files Ready for Manual Processing

All media files are in: `/tmp/ralph_media/`

Download results with metadata: `/tmp/ralph_media/download_results.json`

## Recommended Next Steps

### Immediate (If API Access is Critical):
1. Visit https://aistudio.google.com/app/apikey
2. Check if the API key is valid
3. Generate a new API key if needed
4. Enable the Generative Language API in Google Cloud Console
5. Ensure billing is enabled

### Alternative (If API Access Unavailable):
1. Use the downloaded image files
2. Manually describe the images (they're now local)
3. Use a different AI service (OpenAI GPT-4 Vision, Anthropic Claude with vision, etc.)
4. Create descriptions based on alt text and context (already done in enhanced markdown)

## Test Command for New API Key

Once you have a working API key:

```bash
export NEW_GEMINI_KEY="your-new-key-here"

# Test basic functionality
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Say hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$NEW_GEMINI_KEY"

# If that works, test with Gemini CLI
GEMINI_API_KEY=$NEW_GEMINI_KEY gemini "Hello"
```

## Media Files Available for Description

When the API is working, use this script:

```python
import os
import google.generativeai as genai

genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')

media_dir = "/tmp/ralph_media"
for filename in sorted(os.listdir(media_dir)):
    if filename.startswith('media_') and filename.endswith(('.jpg', '.png')):
        filepath = os.path.join(media_dir, filename)
        print(f"\n--- {filename} ---")

        # Upload the image
        image = genai.upload_file(filepath)

        # Get description
        response = model.generate_content([
            "Describe this image in detail, focusing on visual elements, "
            "colors, composition, text, and any relevant context.",
            image
        ])
        print(response.text)
```
