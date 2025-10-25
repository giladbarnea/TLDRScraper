#!/usr/bin/env python3
"""
Download media files and prepare them for description.
Handles redirects and saves actual media content.
"""

import requests
import json
import os
import sys
from urllib.parse import urlparse, urljoin
from pathlib import Path

# Create output directory
MEDIA_DIR = Path("/tmp/ralph_media")
MEDIA_DIR.mkdir(exist_ok=True)

def follow_redirects(url, max_attempts=5):
    """
    Follow redirects to get the actual media content.
    Returns (content, final_url, content_type) or (None, None, None) if failed.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    for attempt in range(max_attempts):
        try:
            response = session.get(url, timeout=10, allow_redirects=True)

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')

                # Check if it's actual media content
                media_types = ['image/', 'video/', 'audio/']
                if any(mt in content_type for mt in media_types):
                    return response.content, response.url, content_type

                # If HTML, might be an embed page - could try to parse it
                if 'text/html' in content_type:
                    print(f"  Got HTML page at {response.url}, not direct media")
                    return None, response.url, content_type

                # Unknown content type, return it anyway
                return response.content, response.url, content_type

            else:
                print(f"  Attempt {attempt+1}: Status {response.status_code}")

        except requests.RequestException as e:
            print(f"  Attempt {attempt+1}: Error: {e}")

    return None, None, None

def download_media(media_items):
    """Download media items and return mapping of URLs to local files."""
    downloaded = []

    for i, item in enumerate(media_items, 1):
        url = item.get('url', '')
        media_type = item.get('type', 'unknown')

        print(f"\n[{i}/{len(media_items)}] {media_type.upper()}: {url[:80]}...")

        # Skip tracking pixels and profile icons
        if 'noscript.gif' in url or 'icon/' in url:
            print("  Skipping (tracking/icon)")
            continue

        # For tweets, we can't download the content directly
        if media_type == 'tweet':
            print("  Skipping (tweet - would need Twitter API)")
            downloaded.append({
                **item,
                'status': 'skipped',
                'reason': 'tweet_embed'
            })
            continue

        # For external links (non-media)
        if media_type == 'external_link' or url.startswith('https://github.com'):
            print("  Skipping (external link)")
            downloaded.append({
                **item,
                'status': 'skipped',
                'reason': 'external_link'
            })
            continue

        # Try to download the media
        content, final_url, content_type = follow_redirects(url)

        if content:
            # Determine file extension
            ext = 'bin'
            if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                ext = 'jpg'
            elif 'image/png' in content_type:
                ext = 'png'
            elif 'image/gif' in content_type:
                ext = 'gif'
            elif 'video/mp4' in content_type:
                ext = 'mp4'
            else:
                # Try to get from URL
                parsed = urlparse(final_url)
                path = parsed.path
                if '.' in path:
                    ext = path.split('.')[-1][:4]  # max 4 chars

            # Save file
            filename = f"media_{i:02d}.{ext}"
            filepath = MEDIA_DIR / filename

            with open(filepath, 'wb') as f:
                f.write(content)

            file_size = len(content) / 1024  # KB
            print(f"  ✓ Downloaded: {filename} ({file_size:.1f} KB, {content_type})")

            downloaded.append({
                **item,
                'status': 'downloaded',
                'local_path': str(filepath),
                'filename': filename,
                'content_type': content_type,
                'size_kb': round(file_size, 1)
            })
        else:
            print(f"  ✗ Failed to download")
            downloaded.append({
                **item,
                'status': 'failed',
                'reason': 'download_failed'
            })

    return downloaded

def main():
    # Load the article structure
    with open('/tmp/article_structure.json', 'r') as f:
        data = json.load(f)

    media_items = data.get('media', [])

    print(f"Found {len(media_items)} media items to process")
    print(f"Download directory: {MEDIA_DIR}")

    # Download media
    results = download_media(media_items)

    # Save results
    results_file = MEDIA_DIR / 'download_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    downloaded = [r for r in results if r['status'] == 'downloaded']
    skipped = [r for r in results if r['status'] == 'skipped']
    failed = [r for r in results if r['status'] == 'failed']

    print(f"Downloaded: {len(downloaded)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failed: {len(failed)}")
    print(f"\nResults saved to: {results_file}")
    print(f"Media files in: {MEDIA_DIR}")

    # List downloaded files
    if downloaded:
        print("\nDownloaded files:")
        for item in downloaded:
            print(f"  - {item['filename']}: {item.get('alt', 'No description')[:60]}")

    return results

if __name__ == '__main__':
    results = main()
