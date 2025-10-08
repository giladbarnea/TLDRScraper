#!/usr/bin/env python3
"""
Debug script to examine the exact API call being made to OpenAI.
"""
import json
import sys
import requests
from summarizer import url_to_markdown, _fetch_summarize_prompt, _insert_markdown_into_template, _call_llm
import util

def debug_api_call(url):
    print(f"Debugging API call for URL: {url}")
    print("=" * 50)
    
    # Step 1: Get the content
    print("Step 1: Getting content...")
    try:
        markdown_content = url_to_markdown(url)
        print(f"✓ Content length: {len(markdown_content)} characters")
    except Exception as e:
        print(f"✗ Error getting content: {e}")
        return
    
    # Step 2: Get template and create prompt
    print("\nStep 2: Creating prompt...")
    try:
        template = _fetch_summarize_prompt()
        full_prompt = _insert_markdown_into_template(template, markdown_content)
        print(f"✓ Prompt length: {len(full_prompt)} characters")
    except Exception as e:
        print(f"✗ Error creating prompt: {e}")
        return
    
    # Step 3: Check API key
    print("\nStep 3: Checking API key...")
    api_key = util.resolve_env_var("OPENAI_API_TOKEN", "")
    if not api_key:
        print("✗ No API key found")
        return
    print(f"✓ API key found (length: {len(api_key)})")
    
    # Step 4: Prepare the API call manually
    print("\nStep 4: Preparing API call...")
    url_api = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-5",
        "input": full_prompt,
        "reasoning": {"effort": "low"},
        "stream": False,
    }
    
    print(f"API URL: {url_api}")
    print(f"Headers: {headers}")
    print(f"Body keys: {list(body.keys())}")
    print(f"Input length: {len(body['input'])}")
    print(f"Model: {body['model']}")
    
    # Step 5: Check for potential issues
    print("\nStep 5: Checking for potential issues...")
    
    # Check input length
    if len(full_prompt) > 200000:
        print(f"⚠️  WARNING: Very long input ({len(full_prompt)} chars) - may exceed limits")
    
    # Check for special characters
    special_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', '\x0b', '\x0c', '\x0e', '\x0f']
    found_special = [char for char in special_chars if char in full_prompt]
    if found_special:
        print(f"⚠️  WARNING: Found special control characters: {found_special}")
    
    # Check for very long lines
    lines = full_prompt.split('\n')
    long_lines = [i for i, line in enumerate(lines) if len(line) > 1000]
    if long_lines:
        print(f"⚠️  WARNING: Found {len(long_lines)} very long lines")
    
    # Check JSON serialization
    try:
        json_body = json.dumps(body)
        print(f"✓ JSON serialization successful (length: {len(json_body)})")
    except Exception as e:
        print(f"✗ JSON serialization failed: {e}")
        return
    
    # Step 6: Make the actual API call
    print("\nStep 6: Making API call...")
    try:
        resp = requests.post(url_api, headers=headers, data=json_body, timeout=600)
        print(f"Response status: {resp.status_code}")
        print(f"Response headers: {dict(resp.headers)}")
        
        if resp.status_code == 200:
            print("✓ API call successful!")
            data = resp.json()
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        else:
            print(f"✗ API call failed with status {resp.status_code}")
            print(f"Response text: {resp.text}")
            
    except Exception as e:
        print(f"✗ API call error: {e}")

if __name__ == "__main__":
    url = "https://www.arxiv.org/pdf/2510.00184"
    debug_api_call(url)