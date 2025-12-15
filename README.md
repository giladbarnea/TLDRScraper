---
last_updated: 2025-12-11 15:05, 05f0d95
description: light overview over the project
---
# TLDRScraper

Newsletter aggregator that scrapes tech newsletters from multiple sources, displays them in a unified interface, and provides AI-powered TLDRs.

## Architecture

- **Frontend**: React 19 + Vite (in `client/`)
- **Backend**: Flask + Python (serverless on Vercel)
- **AI**: Google Gemini 3 Pro for TLDRs

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed flows & user interactions documentation and [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for a map of the project structure.

## Development

## Development & Setup

### Running the server and logs watchdog
```bash
# Verify the environment and dependencies are set up correctly.
source ./setup.sh

# Start the server and watchdog in the background. Logs output to file.
source ./setup.sh && start_server_and_watchdog

# Verify the server is running.
source ./setup.sh && print_server_and_watchdog_pids

# Exercise the API with curl requests.
curl http://localhost:5001/api/scrape
curl http://localhost:5001/api/tldr-url
curl ...additional endpoints that may be relevant...

# Stop the server and watchdog.
source ./setup.sh && kill_server_and_watchdog
```


## Client setup

```bash
source ./setup.sh && build_client
# Alias for cd client && npm install && npm run build
```

### Frontend development

For frontend development with hot reload:

```bash
cd client
npm run dev
```

This runs Vite dev server on port 3000 with API proxy to localhost:5000.


### `uv` installation and usage

- Install `uv` and use Python via `uv`:
```bash
source setup.sh  # This installs uv if needed
uv --version
```

## Vercel Deployment

### How It Works

The application is deployed to Vercel as a Python serverless function with a built React frontend:

1. **Build Phase** (`buildCommand` in `vercel.json`):
   - `cd client && npm install && npm run build`
   - Builds React app

2. **Install Phase** (automatic):
   - Vercel auto-detects `requirements.txt`
   - Installs Python dependencies for the serverless function

3. **Runtime**:
   - `/api/index.py` imports the Flask app from `serve.py`
   - All routes (`/`, `/api/*`) are handled by the Python serverless function
   - Flask serves the built React app from `client/static/dist/`
   - API endpoints process requests

### Key Configuration Files

#### `vercel.json`
```json
{
  "buildCommand": "cd client && npm install && npm run build",
  "outputDirectory": "static/dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/api/index" }
  ]
}
```

- **buildCommand**: Builds the React frontend
- **outputDirectory**: Points to where React builds output (matches `client/vite.config.js` outDir)
- **rewrites**: Routes all requests to the Python serverless function

#### `api/index.py`
```python
import sys
import os

# Add parent directory to path so we can import serve.py and other modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from serve import app as app
```

This is the Vercel serverless function entry point. The path manipulation is required because Vercel's Python runtime doesn't automatically add the parent directory to `sys.path`.

#### `serve.py`
```python
# Configure Flask to serve React build output
app = Flask(
    __name__,
    static_folder='static/dist/assets',
    static_url_path='/assets'
)

@app.route("/")
def index():
    """Serve the React app"""
    static_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'dist')
    return send_from_directory(static_dist, 'index.html')
```

Flask is configured to:
- Serve static assets from `static/dist/assets` at `/assets/*`
- Serve the React app's `index.html` at the root `/`
- Handle API routes at `/api/*`

### Deployment Requirements

1. **React build output** must be in `client/static/dist/` (configured in `client/vite.config.js`)
2. **Python dependencies** are managed by `uv` and must manually be added to `requirements.txt` (Vercel auto-installs)
3. **Module imports** in `api/index.py` must handle parent directory path
4. **Flask static configuration** must point to built React assets

### Common Vercel Deployment Issues

**Issue**: `pip: command not found`
- **Cause**: Explicit `installCommand` in vercel.json trying to run pip in Node.js context
- **Solution**: Remove `installCommand` - Vercel auto-installs from requirements.txt

**Issue**: `No Output Directory named "public" found`
- **Cause**: Vercel looking for default output directory
- **Solution**: Add `"outputDirectory": "static/dist"` to vercel.json

**Issue**: `404 for /api/index`
- **Cause**: Python module import failing in serverless function
- **Solution**: Add parent directory to sys.path in api/index.py

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed flows & user interactions documentation
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Map of the project structure
- [GOTCHAS.md](GOTCHAS.md) - Documented solved tricky past bugs
- [BUGS.md](BUGS.md) - Known issues