#!/usr/bin/env python3
"""
Debug script to test markitdown PDF processing specifically.
"""
import sys
from markitdown import MarkItDown, StreamInfo
from io import BytesIO
import requests

def test_markitdown_pdf(url):
    print(f"Testing markitdown with PDF URL: {url}")
    print("=" * 50)
    
    md = MarkItDown()
    
    # Test 1: Direct URL conversion
    print("Test 1: Direct URL conversion with md.convert_url()")
    try:
        result = md.convert_url(url)
        print(f"✓ Successfully converted URL")
        print(f"Result type: {type(result)}")
        print(f"Text content length: {len(result.text_content)}")
        print(f"First 500 characters:")
        print(repr(result.text_content[:500]))
        print("...")
        print(f"Last 500 characters:")
        print(repr(result.text_content[-500:]))
    except Exception as e:
        print(f"✗ Error in direct URL conversion: {e}")
    
    print("\n" + "=" * 30)
    
    # Test 2: Download and convert stream
    print("Test 2: Download and convert as stream")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        print(f"✓ Successfully downloaded PDF ({len(response.content)} bytes)")
        
        stream = BytesIO(response.content)
        result = md.convert_stream(
            stream,
            stream_info=StreamInfo(mimetype="application/pdf", charset="utf-8"),
        )
        print(f"✓ Successfully converted stream")
        print(f"Text content length: {len(result.text_content)}")
        print(f"First 500 characters:")
        print(repr(result.text_content[:500]))
        print("...")
        print(f"Last 500 characters:")
        print(repr(result.text_content[-500:]))
    except Exception as e:
        print(f"✗ Error in stream conversion: {e}")
    
    print("\n" + "=" * 30)
    
    # Test 3: Check if it's actually extracting text or returning raw PDF
    print("Test 3: Analyzing content type")
    try:
        result = md.convert_url(url)
        content = result.text_content
        
        # Check if it looks like raw PDF
        if content.startswith('%PDF'):
            print("⚠️  WARNING: Content appears to be raw PDF, not extracted text")
            print("This suggests markitdown is not properly processing the PDF")
        elif 'PDF' in content[:100] and '%' in content[:100]:
            print("⚠️  WARNING: Content may contain PDF metadata/headers")
        else:
            print("✓ Content appears to be extracted text")
        
        # Check for common PDF artifacts
        pdf_artifacts = ['obj', 'endobj', 'stream', 'endstream', 'xref', 'trailer']
        found_artifacts = [artifact for artifact in pdf_artifacts if artifact in content[:1000]]
        if found_artifacts:
            print(f"⚠️  WARNING: Found PDF artifacts: {found_artifacts}")
        
        # Check for actual text content
        text_indicators = ['Abstract', 'Introduction', 'Conclusion', 'References', 'Figure', 'Table']
        found_text = [indicator for indicator in text_indicators if indicator in content]
        if found_text:
            print(f"✓ Found text indicators: {found_text}")
        else:
            print("⚠️  WARNING: No typical academic text indicators found")
            
    except Exception as e:
        print(f"✗ Error analyzing content: {e}")

if __name__ == "__main__":
    url = "https://www.arxiv.org/pdf/2510.00184"
    test_markitdown_pdf(url)