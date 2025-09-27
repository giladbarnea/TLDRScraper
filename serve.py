#!/usr/bin/env python3
"""
TLDR Newsletter Scraper Backend with Proxy
"""

from flask import Flask, render_template, request, jsonify
import logging
from datetime import datetime, timedelta
import requests
from markitdown import MarkItDown
from io import BytesIO
import re
from bs4 import BeautifulSoup
import time
import os

from blob_cache import is_cache_eligible, get_cached_json, put_cached_json, _get_token
from edge_config import is_available as ec_available, get_last_write_status, get_last_write_body, get_effective_env_summary
import urllib.parse as _urlparse
import collections

app = Flask(__name__)
logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'))
logger = logging.getLogger("serve")
md = MarkItDown()
LOGS = collections.deque(maxlen=200)
def _log(msg):
    try:
        LOGS.append(msg)
    except Exception:
        pass
    logger.info(msg)

# Per-request run diagnostics (simple globals, reset at start of scrape)
EDGE_READ_ATTEMPTS = 0
EDGE_READ_HITS = 0
EDGE_WRITE_ATTEMPTS = 0
EDGE_WRITE_SUCCESS = 0

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape_newsletters():
    """Backend proxy to scrape TLDR newsletters"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400
        
        # Validate required fields
        if 'start_date' not in data or 'end_date' not in data:
            return jsonify({'success': False, 'error': 'start_date and end_date are required'}), 400
            
        start_date = datetime.fromisoformat(data['start_date'])
        end_date = datetime.fromisoformat(data['end_date'])
        
        # Backend validation
        if start_date > end_date:
            return jsonify({'success': False, 'error': 'start_date must be before or equal to end_date'}), 400
            
        # Limit maximum date range to prevent abuse (31 days inclusive)
        if (end_date - start_date).days >= 31:
            return jsonify({'success': False, 'error': 'Date range cannot exceed 31 days'}), 400
        
        _log(f"[serve.scrape_newsletters] start start_date={data['start_date']} end_date={data['end_date']}")
        # reset run diagnostics
        global EDGE_READ_ATTEMPTS, EDGE_READ_HITS, EDGE_WRITE_ATTEMPTS, EDGE_WRITE_SUCCESS
        EDGE_READ_ATTEMPTS = EDGE_READ_HITS = EDGE_WRITE_ATTEMPTS = EDGE_WRITE_SUCCESS = 0
        result = scrape_date_range(start_date, end_date)
        _log(f"[serve.scrape_newsletters] done dates_processed={result['stats']['dates_processed']} total_articles={result['stats']['total_articles']}")
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_date_range(start_date, end_date):
    """Generate list of dates between start and end (inclusive)"""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates

def format_date_for_url(date):
    """Format date as YYYY-MM-DD for TLDR URL"""
    if isinstance(date, str):
        return date
    return date.strftime('%Y-%m-%d')

def is_sponsored_section(text):
    """Check if a section header indicates sponsored content"""
    sponsored_indicators = [
        'sponsor', 'sponsored', 'advertisement', 'advertise', 'partner',
        'tldr deals', 'deals', 'promo', 'promotion'
    ]
    return any(indicator in text.lower() for indicator in sponsored_indicators)

def is_sponsored_link(title, url):
    """Check if a link appears to be sponsored content"""
    # Only check title for explicit sponsored indicators, not URL UTM params
    # since TLDR articles legitimately use UTM tracking
    sponsored_keywords = [
        'sponsor', 'sponsored', 'advertisement', 'advertise', 
        'partner content', 'affiliate', 'promo', 'promotion'
    ]
    
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in sponsored_keywords)

def is_sponsored_url(url: str) -> bool:
    """Treat links as sponsored based on UTM query params.

    Rules:
    - If utm_medium=newsletter (case-insensitive) => sponsored
    - If utm_campaign is present (any value) => sponsored
    """
    try:
        import urllib.parse as urlparse
        parsed = urlparse.urlparse(url)
        query_params = {k.lower(): v for k, v in urlparse.parse_qs(parsed.query).items()}
        medium_values = [v.lower() for v in query_params.get('utm_medium', [])]
        if 'newsletter' in medium_values:
            return True
        if 'utm_campaign' in query_params:
            return True
        return False
    except Exception:
        return False

def extract_newsletter_content(html):
    """Extract newsletter content from HTML using BeautifulSoup"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the main newsletter content area
    # TLDR typically has the content in specific containers
    content_selectors = [
        '[id*="content"]', '[class*="newsletter"]', '[class*="content"]',
        'main', 'article', '.container'
    ]
    
    newsletter_content = None
    for selector in content_selectors:
        newsletter_content = soup.select_one(selector)
        if newsletter_content:
            break
    
    if not newsletter_content:
        newsletter_content = soup.body or soup
    
    # Convert to markdown
    content_html = str(newsletter_content)
    content_stream = BytesIO(content_html.encode('utf-8'))
    result = md.convert_stream(content_stream, file_extension=".html")
    
    return result.text_content

def is_file_url(url):
    """Check if URL points to a file (image, PDF, etc.) rather than a web page"""
    file_extensions = [
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp',  # Images
        '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',  # Documents
        '.mp4', '.mp3', '.avi', '.mov', '.wav',  # Media files
        '.zip', '.tar', '.gz', '.rar'  # Archives
    ]
    
    # Remove query parameters to check the actual file path
    url_path = url.split('?')[0].lower()
    return any(url_path.endswith(ext) for ext in file_extensions)

def get_utm_source_category(url):
    """Extract UTM source from URL and map to category"""
    import urllib.parse as urlparse
    
    try:
        parsed = urlparse.urlparse(url)
        query_params = urlparse.parse_qs(parsed.query)
        utm_source = query_params.get('utm_source', [''])[0].lower()
        
        # Map UTM sources to categories - only "general" and AI
        if utm_source in ['tldr', 'tldrtech']:
            return 'TLDR Tech'
        elif utm_source in ['tldrai', 'tldr-ai', 'tldr_ai']:
            return 'TLDR AI'
        else:
            return None  # Filter out other sources
            
    except:
        return None

def parse_articles_from_markdown(markdown, date, newsletter_type):
    """Parse articles from markdown content, using UTM source for categorization"""
    lines = markdown.split('\n')
    articles = []
    in_sponsored_section = False
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Detect section headers to skip sponsored sections
        if line.startswith('###') or line.startswith('##'):
            header_text = re.sub(r'^#+\s*', '', line).strip()
            
            # Check if this is a sponsored section
            if is_sponsored_section(header_text):
                in_sponsored_section = True
                continue
            else:
                in_sponsored_section = False
            continue
        
        # Skip content in sponsored sections
        if in_sponsored_section:
            continue
            
        # Extract article links [Title](URL)
        link_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line)
        for title, url in link_matches:
            # Skip if URL doesn't start with http (internal links, etc.)
            if not url.startswith('http'):
                continue
            
            # Skip file URLs (images, PDFs, etc.)
            if is_file_url(url):
                continue
                
            # Skip if appears to be sponsored in title
            if is_sponsored_link(title, url):
                continue
            
            # Skip if URL UTM flags indicate sponsorship
            if is_sponsored_url(url):
                continue
            
            # Get category from UTM source
            category = get_utm_source_category(url)
            if not category:
                continue  # Skip articles that don't match our desired sources
                
            # Clean up title and URL
            title = title.strip()
            url = url.strip()
            
            # Clean up title (remove markdown artifacts)
            title = re.sub(r'^#+\s*', '', title)  # Remove leading ###
            title = re.sub(r'^\s*\d+\.\s*', '', title)  # Remove leading numbers
            
            articles.append({
                'title': title,
                'url': url, 
                'category': category,
                'date': date,
                'newsletter_type': newsletter_type
            })
    
    return articles

def fetch_newsletter(date, newsletter_type):
    """Fetch and parse a single newsletter"""
    date_str = format_date_for_url(date)
    url = f"https://tldr.tech/{newsletter_type}/{date_str}"
    
    # Always try Edge cache read first (no Blob fallback)
    global EDGE_READ_ATTEMPTS, EDGE_READ_HITS
    EDGE_READ_ATTEMPTS += 1
    cache_start = time.time()
    cached = get_cached_json(newsletter_type, date)
    if cached is not None and cached.get('status') == 'hit':
        EDGE_READ_HITS += 1
        cached_articles = cached.get('articles', [])
        for a in cached_articles:
            a['fetched_via'] = 'hit'
            a['timing_total_ms'] = int(round((time.time() - cache_start) * 1000))
        _log(f"[serve.fetch_newsletter] cache HIT date={date_str} type={newsletter_type} count={len(cached_articles)}")
        return {
            'date': date,
            'newsletter_type': newsletter_type,
            'articles': cached_articles
        }

    try:
        net_start = time.time()
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; TLDR-Scraper/1.0)'
        })
        net_ms = int(round((time.time() - net_start) * 1000))
        
        if response.status_code == 404:
            return None
            
        response.raise_for_status()
        
        convert_start = time.time()
        markdown_content = extract_newsletter_content(response.text)
        convert_ms = int(round((time.time() - convert_start) * 1000))

        parse_start = time.time()
        articles = parse_articles_from_markdown(markdown_content, date, newsletter_type)
        parse_ms = int(round((time.time() - parse_start) * 1000))
        total_ms = net_ms + convert_ms + parse_ms
        # Tag fetched source for UI: only tag as 'other' when network was used
        fetched_status = 'other'
        for a in articles:
            a['fetched_via'] = fetched_status
            a['timing_total_ms'] = total_ms
            a['timing_fetch_ms'] = net_ms
            a['timing_convert_ms'] = convert_ms
            a['timing_parse_ms'] = parse_ms
        result = {
            'date': date,
            'newsletter_type': newsletter_type,
            'articles': articles
        }

        # Always write to Edge for fast repeats (per env rules handled in put_cached_json)
        def _sanitize(a):
            clean = {k: v for k, v in a.items() if k != 'fetched_via' and not k.startswith('timing_')}
            try:
                if 'date' in clean and not isinstance(clean['date'], str):
                    clean['date'] = format_date_for_url(clean['date'])
                # Strip utm_* params from stored URLs
                if 'url' in clean and isinstance(clean['url'], str):
                    import urllib.parse as urlparse
                    p = urlparse.urlparse(clean['url'])
                    # Keep only non-utm_* query params
                    query_pairs = [(k, v) for (k, v) in urlparse.parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith('utm_')]
                    new_query = urlparse.urlencode(query_pairs, doseq=True)
                    clean['url'] = urlparse.urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip('/') if len(p.path) > 1 and p.path.endswith('/') else p.path, p.params, new_query, p.fragment))
            except Exception:
                pass
            return clean
        sanitized_articles = [_sanitize(a) for a in articles]
        payload = {
            'status': 'hit',
            'date': date_str,
            'newsletter_type': newsletter_type,
            'articles': sanitized_articles
        }
        try:
            global EDGE_WRITE_ATTEMPTS, EDGE_WRITE_SUCCESS
            EDGE_WRITE_ATTEMPTS += 1
            ok = put_cached_json(newsletter_type, date, payload)
            if ok:
                EDGE_WRITE_SUCCESS += 1
            status = get_last_write_status()
            body = get_last_write_body()
            _log(f"[serve.fetch_newsletter] wrote cache date={date_str} type={newsletter_type} count={len(sanitized_articles)} ok={bool(ok)} status={status} body={(body or '')}")
        except Exception:
            logger.exception("[serve.fetch_newsletter] failed writing cache date=%s type=%s", date_str, newsletter_type)

        return result
        
    except requests.RequestException as e:
        logger.exception("[serve.fetch_newsletter] request error url=%s", url)
        return None

def canonicalize_url(url):
    """Canonicalize URL for better deduplication"""
    import urllib.parse as urlparse
    
    try:
        parsed = urlparse.urlparse(url)
        # Keep only the base URL without query parameters for deduplication
        canonical = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
        # Remove trailing slash for consistency
        if canonical.endswith('/') and len(canonical) > 1:
            canonical = canonical[:-1]
        return canonical
    except:
        return url.lower()

def scrape_date_range(start_date, end_date):
    """Scrape all newsletters in date range"""
    dates = get_date_range(start_date, end_date)
    newsletter_types = ['tech', 'ai']
    
    all_articles = []
    url_set = set()  # For deduplication by canonical URL
    processed_count = 0
    total_count = len(dates) * len(newsletter_types)
    # Diagnostics
    hits = 0
    misses = 0
    others = 0
    
    for date in dates:
        for newsletter_type in newsletter_types:
            processed_count += 1
            print(f"Processing {newsletter_type} newsletter for {format_date_for_url(date)} ({processed_count}/{total_count})")
            
            result = fetch_newsletter(date, newsletter_type)
            if result and result['articles']:
                # Deduplicate by canonical URL
                for article in result['articles']:
                    canonical_url = canonicalize_url(article['url'])
                    if canonical_url not in url_set:
                        url_set.add(canonical_url)
                        all_articles.append(article)
                        # Count source
                        src = article.get('fetched_via')
                        if src == 'hit':
                            hits += 1
                        elif src == 'miss':
                            misses += 1
                        else:
                            others += 1
            
            # Rate limiting - be respectful only when we actually fetched from network
            if result and any(a.get('fetched_via') == 'other' for a in (result.get('articles') or [])):
                time.sleep(0.2)
    
    # Group articles by date
    grouped_articles = {}
    for article in all_articles:
        date_str = format_date_for_url(article['date'])
        if date_str not in grouped_articles:
            grouped_articles[date_str] = []
        grouped_articles[date_str].append(article)
    
    # Format output
    output = format_final_output(start_date, end_date, grouped_articles)
    
    # Edge config ID consistency check (read URL vs ID)
    ec_url = os.environ.get('EDGE_CONFIG_CONNECTION_STRING') or os.environ.get('TLDR_SCRAPER_EDGE_CONFIG_CONNECTION_STRING')
    ec_id_env = os.environ.get('EDGE_CONFIG_ID') or os.environ.get('TLDR_SCRAPER_EDGE_CONFIG_ID')
    def _extract_id(u: str):
        try:
            p = _urlparse.urlparse(u)
            # path like /ecfg_xxx or /ecfg_xxx/...
            seg = p.path.strip('/').split('/')[0]
            return seg if seg.startswith('ecfg_') else None
        except Exception:
            return None
    ec_id_from_url = _extract_id(ec_url) if ec_url else None

    return {
        'success': True,
        'output': output,
        'stats': {
            'total_articles': len(all_articles),
            'unique_urls': len(url_set),
            'dates_processed': len(dates),
            'dates_with_content': len(grouped_articles),
            'cache_hits': hits,
            'cache_misses': misses,
            'cache_other': others,
            # Env and cache diagnostics
            **get_effective_env_summary(),
            'edge_config_available': bool(ec_available()),
            'edge_id_match': bool(ec_id_from_url and ec_id_env and ec_id_from_url == ec_id_env),
            'edge_reads_attempted': EDGE_READ_ATTEMPTS,
            'edge_reads_hit': EDGE_READ_HITS,
            'edge_writes_attempted': EDGE_WRITE_ATTEMPTS,
            'edge_writes_success': EDGE_WRITE_SUCCESS,
            'debug_logs': list(LOGS)
        }
    }

def format_final_output(start_date, end_date, grouped_articles):
    """Format the final output according to requirements"""
    output = f"# TLDR Newsletter Articles ({format_date_for_url(start_date)} to {format_date_for_url(end_date)})\n\n"
    
    # Sort dates chronologically
    sorted_dates = sorted(grouped_articles.keys())
    
    for date_str in sorted_dates:
        articles = grouped_articles[date_str]
        
        # Use H3 for issue dates (as required)
        output += f"### {date_str}\n\n"
        
        # Group articles by category (TLDR Tech vs TLDR AI)
        category_groups = {}
        for article in articles:
            category = article['category']
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(article)
        
        # Sort categories: TLDR Tech first, then TLDR AI
        category_order = []
        if 'TLDR Tech' in category_groups:
            category_order.append('TLDR Tech')
        if 'TLDR AI' in category_groups:
            category_order.append('TLDR AI')
        
        for category in category_order:
            category_articles = category_groups[category]
            
            # Use H4 for categories (TLDR Tech / TLDR AI)
            output += f"#### {category}\n\n"
            
            # Keep original chronological order within categories
            for i, article in enumerate(category_articles, 1):
                status = article.get('fetched_via')
                if status not in ('hit', 'miss', 'other'):
                    status = 'other'
                # Timing summary
                total_ms = article.get('timing_total_ms')
                if total_ms is not None and status == 'other':
                    timing_label = f", {total_ms}ms"
                elif total_ms is not None and status == 'hit':
                    timing_label = f", {total_ms}ms"
                else:
                    timing_label = ""
                title_with_status = f"{article['title']} ({status}{timing_label})"
                output += f"{i}. [{title_with_status}]({article['url']})\n"
            
            output += "\n"
    
    return output

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)