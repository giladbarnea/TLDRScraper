#!/usr/bin/env python3
"""
TLDR Newsletter Scraper Web App
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import os

app = Flask(__name__)

@app.route('/')
def index():
    """Main page with date input form"""
    # Calculate default dates
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d')
    
    return render_template('index.html', start_date=start_date, end_date=end_date)

@app.route('/scrape', methods=['POST'])
def scrape_newsletters():
    """Handle the scraping request"""
    try:
        # Get form data
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        # TODO: Implement scraping logic
        result = f"Scraping from {start_date} to {end_date}"
        
        return jsonify({'success': True, 'result': result})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)