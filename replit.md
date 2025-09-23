# Overview

A Flask-based web application that scrapes TLDR newsletters within specified date ranges. The application provides a simple web interface for users to select date ranges and fetches newsletter content using Microsoft's MarkItDown library for content extraction and conversion to markdown format.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Flask Framework**: Lightweight Python web framework serving as the main application server
- **RESTful API Design**: Single `/api/scrape` endpoint handling POST requests for newsletter scraping operations
- **Content Processing Pipeline**: Uses Microsoft's MarkItDown library to convert HTML newsletter content to markdown format
- **Request Validation**: Backend validation for date ranges, input sanitization, and abuse prevention (31-day maximum range limit)

## Frontend Architecture
- **Server-Side Rendering**: Traditional HTML templates served by Flask using Jinja2 templating
- **Minimal JavaScript**: Client-side form handling and API communication
- **Responsive Design**: CSS-based responsive layout for cross-device compatibility

## Data Processing
- **HTTP Client**: Uses Python requests library for external HTTP communications
- **Content Extraction**: MarkItDown library handles conversion from HTML to structured markdown
- **BeautifulSoup Integration**: HTML parsing capabilities for content processing
- **Stream Processing**: BytesIO streams for efficient memory handling of large content

## Error Handling
- **Input Validation**: Comprehensive validation for date inputs and JSON payloads
- **Exception Management**: Try-catch blocks with proper HTTP status codes
- **Rate Limiting**: Built-in abuse prevention through date range restrictions

# External Dependencies

## Core Libraries
- **Flask**: Web application framework
- **MarkItDown**: Microsoft's content extraction and conversion library
- **Requests**: HTTP client for external API calls
- **BeautifulSoup4**: HTML parsing and manipulation
- **Python datetime**: Date handling and validation

## Web Technologies
- **HTML5**: Frontend markup
- **CSS3**: Styling and responsive design
- **Vanilla JavaScript**: Client-side functionality

## External Services
- **TLDR Newsletter URLs**: Target websites for content scraping
- **HTTP/HTTPS**: Protocol for external content fetching

## Development Tools
- **Python 3**: Runtime environment
- **Jinja2**: Template engine (included with Flask)