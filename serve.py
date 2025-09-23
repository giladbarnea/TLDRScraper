#!/usr/bin/env python3
"""
TLDR Newsletter Scraper Backend with Proxy
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import requests
from markitdown import MarkItDown
from io import BytesIO
import re
from bs4 import BeautifulSoup
import time

app = Flask(__name__)
md = MarkItDown()

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
        
        result = scrape_date_range(start_date, end_date)
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

def parse_articles_from_markdown(markdown, date, newsletter_type):
    """Parse articles from markdown content, preserving chronological order"""
    lines = markdown.split('\n')
    articles = []
    current_category = 'Miscellaneous'
    in_sponsored_section = False
    
    # Category mapping for consistency
    category_mapping = {
        'big tech & startups': 'Big Tech & Startups',
        'science & futuristic technology': 'Science & Futuristic Technology',
        'programming, design & data science': 'Programming',
        'programming': 'Programming', 
        'design & data science': 'Design & Data Science',
        'miscellaneous': 'Miscellaneous',
        'quick links': 'Quick Links'
    }
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Detect section headers
        if line.startswith('###') or line.startswith('##'):
            header_text = re.sub(r'^#+\s*', '', line).strip()
            
            # Check if this is a sponsored section
            if is_sponsored_section(header_text):
                in_sponsored_section = True
                continue
            else:
                in_sponsored_section = False
                
            # Map to standard category name
            normalized = header_text.lower().strip()
            current_category = category_mapping.get(normalized, header_text)
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
                
            # Skip if appears to be sponsored
            if is_sponsored_link(title, url):
                continue
                
            # Clean up title and URL
            title = title.strip()
            url = url.strip()
            
            articles.append({
                'title': title,
                'url': url, 
                'category': current_category,
                'date': date,
                'newsletter_type': newsletter_type
            })
    
    return articles

def fetch_newsletter(date, newsletter_type):
    """Fetch and parse a single newsletter"""
    date_str = format_date_for_url(date)
    url = f"https://tldr.tech/{newsletter_type}/{date_str}"
    
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; TLDR-Scraper/1.0)'
        })
        
        if response.status_code == 404:
            return None  # No newsletter for this date
            
        response.raise_for_status()
        
        markdown_content = extract_newsletter_content(response.text)
        articles = parse_articles_from_markdown(markdown_content, date, newsletter_type)
        
        return {
            'date': date,
            'newsletter_type': newsletter_type,
            'articles': articles
        }
        
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def scrape_date_range(start_date, end_date):
    """Scrape all newsletters in date range"""
    dates = get_date_range(start_date, end_date)
    newsletter_types = ['tech', 'ai']
    
    all_articles = []
    url_set = set()  # For deduplication
    processed_count = 0
    total_count = len(dates) * len(newsletter_types)
    
    for date in dates:
        for newsletter_type in newsletter_types:
            processed_count += 1
            print(f"Processing {newsletter_type} newsletter for {format_date_for_url(date)} ({processed_count}/{total_count})")
            
            result = fetch_newsletter(date, newsletter_type)
            if result and result['articles']:
                # Deduplicate by URL
                for article in result['articles']:
                    if article['url'] not in url_set:
                        url_set.add(article['url'])
                        all_articles.append(article)
            
            # Rate limiting - be respectful
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
    
    return {
        'success': True,
        'output': output,
        'stats': {
            'total_articles': len(all_articles),
            'unique_urls': len(url_set),
            'dates_processed': len(dates),
            'dates_with_content': len(grouped_articles)
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
        
        # Group articles by category
        category_groups = {}
        for article in articles:
            category = article['category']
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(article)
        
        # Preserve original category order from the newsletter
        # Get unique categories in the order they first appeared
        seen_categories = set()
        original_category_order = []
        for article in articles:
            if article['category'] not in seen_categories:
                original_category_order.append(article['category'])
                seen_categories.add(article['category'])
        
        for category in original_category_order:
            category_articles = category_groups[category]
            
            # Use H4 for categories (as required)
            output += f"#### {category}\n\n"
            
            # Keep original chronological order within categories
            # (articles are already in chronological order from parsing)
            for i, article in enumerate(category_articles, 1):
                output += f"{i}. [{article['title']}]({article['url']})\n"
            
            output += "\n"
    
    return output

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)