#!/usr/bin/env python3
"""
Debug script to examine PDF content extraction and API call details.
"""
import json
import sys
from summarizer import url_to_markdown, _fetch_summarize_prompt, _insert_markdown_into_template

def debug_pdf_processing(url):
    print(f"Processing URL: {url}")
    print("=" * 50)
    
    # Step 1: Extract content from PDF
    print("Step 1: Extracting content from PDF...")
    try:
        markdown_content = url_to_markdown(url)
        print(f"✓ Successfully extracted content")
        print(f"Content length: {len(markdown_content)} characters")
        print(f"First 500 characters:")
        print(markdown_content[:500])
        print("...")
        print(f"Last 500 characters:")
        print(markdown_content[-500:])
    except Exception as e:
        print(f"✗ Error extracting content: {e}")
        return
    
    print("\n" + "=" * 50)
    
    # Step 2: Get prompt template
    print("Step 2: Getting prompt template...")
    try:
        template = _fetch_summarize_prompt()
        print(f"✓ Successfully fetched template")
        print(f"Template length: {len(template)} characters")
        print(f"Template preview:")
        print(template[:300])
        print("...")
    except Exception as e:
        print(f"✗ Error fetching template: {e}")
        return
    
    print("\n" + "=" * 50)
    
    # Step 3: Insert markdown into template
    print("Step 3: Inserting markdown into template...")
    try:
        full_prompt = _insert_markdown_into_template(template, markdown_content)
        print(f"✓ Successfully created full prompt")
        print(f"Full prompt length: {len(full_prompt)} characters")
        
        # Check for potential issues
        print("\nAnalyzing prompt for potential issues:")
        
        # Check for very long content
        if len(full_prompt) > 100000:
            print(f"⚠️  WARNING: Very long prompt ({len(full_prompt)} chars) - may exceed API limits")
        
        # Check for special characters that might cause issues
        special_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', '\x0b', '\x0c', '\x0e', '\x0f']
        found_special = [char for char in special_chars if char in full_prompt]
        if found_special:
            print(f"⚠️  WARNING: Found special control characters: {found_special}")
        
        # Check for very long lines
        lines = full_prompt.split('\n')
        long_lines = [i for i, line in enumerate(lines) if len(line) > 1000]
        if long_lines:
            print(f"⚠️  WARNING: Found {len(long_lines)} very long lines (>{len(long_lines[0])} chars)")
        
        # Show a sample of the full prompt
        print(f"\nFull prompt preview (first 1000 chars):")
        print(full_prompt[:1000])
        print("...")
        print(f"Full prompt ending (last 1000 chars):")
        print(full_prompt[-1000:])
        
    except Exception as e:
        print(f"✗ Error creating full prompt: {e}")
        return
    
    print("\n" + "=" * 50)
    print("Analysis complete!")

if __name__ == "__main__":
    url = "https://www.arxiv.org/pdf/2510.00184"
    debug_pdf_processing(url)