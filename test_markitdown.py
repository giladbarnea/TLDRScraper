#!/usr/bin/env python3
"""
Test script for Microsoft's MarkItDown on TLDR newsletter
"""

import requests
from markitdown import MarkItDown
import sys
from urllib.parse import urlparse
from io import BytesIO

def test_markitdown_on_url(url):
    """Test MarkItDown extraction on a given URL"""
    print(f"Testing MarkItDown on: {url}")
    print("=" * 60)
    
    try:
        # Initialize MarkItDown
        md = MarkItDown()
        
        # Fetch the URL content
        print("Fetching URL content...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        print(f"HTTP Status: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"Content Length: {len(response.content)} bytes")
        print()
        
        # Convert using MarkItDown
        print("Converting with MarkItDown...")
        content_stream = BytesIO(response.content)
        result = md.convert_stream(content_stream, file_extension=".html")
        
        print("EXTRACTION RESULTS:")
        print("=" * 60)
        print(result.text_content)
        print("=" * 60)
        
        # Analyze the extraction
        lines = result.text_content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        print(f"\nEXTRACTION ANALYSIS:")
        print(f"Total lines: {len(lines)}")
        print(f"Non-empty lines: {len(non_empty_lines)}")
        print(f"Total characters: {len(result.text_content)}")
        
        # Look for typical TLDR newsletter content
        tldr_indicators = [
            'TLDR', 'tech news', 'programming', 'startup', 'AI', 'developer',
            'Big Tech', 'Science', 'Miscellaneous'
        ]
        
        content_lower = result.text_content.lower()
        found_indicators = [ind for ind in tldr_indicators if ind.lower() in content_lower]
        
        print(f"TLDR newsletter indicators found: {found_indicators}")
        
        # Check for typical newsletter structure
        has_links = 'http' in result.text_content
        has_headlines = any(line.startswith('#') for line in lines)
        has_bullet_points = any(line.strip().startswith('*') or line.strip().startswith('-') for line in lines)
        
        print(f"\nSTRUCTURAL ANALYSIS:")
        print(f"Contains links: {has_links}")
        print(f"Has markdown headers: {has_headlines}")
        print(f"Has bullet points/lists: {has_bullet_points}")
        
        return True
        
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return False
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False

def main():
    """Main function to test different TLDR URLs"""
    # Test URLs
    test_urls = [
        "https://tldr.tech/tech/2025-09-22",
        "https://tldr.tech/tech/2025-09-21"  # Fallback in case today's doesn't exist
    ]
    
    print("Microsoft MarkItDown Test on TLDR Newsletter")
    print("=" * 60)
    
    success = False
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        if test_markitdown_on_url(url):
            success = True
            break
        else:
            print(f"Failed to process {url}, trying next...")
    
    if not success:
        print("\nAll test URLs failed. You may want to try a different date or check if TLDR is accessible.")

if __name__ == "__main__":
    main()