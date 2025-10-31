# TLDRScraper

Newsletter aggregator that scrapes tech newsletters from multiple sources, displays them in a unified interface, and provides AI-powered summaries and TLDRs.

## Architecture

- **Frontend**: Vue 3 + Vite (in `client/`)
- **Backend**: Flask + Python (serverless on Vercel)
- **AI**: OpenAI GPT-5 for summaries

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

## Development

### Local Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install and build the Vue app:**
   ```bash
   cd client
   npm install
   npm run build
   ```

3. **Run the Flask server:**
   ```bash
   python serve.py
   ```

The app will be available at http://localhost:5001

### Development Mode

For frontend development with hot reload:

```bash
cd client
npm run dev
```

This runs Vite dev server on port 3000 with API proxy to localhost:5000.

## Vercel Deployment

### How It Works

The application is deployed to Vercel as a Python serverless function with a built Vue frontend:

1. **Build Phase** (`buildCommand` in `vercel.json`):
   - `cd client && npm install && npm run build`
   - Builds Vue app to `static/dist/`

2. **Install Phase** (automatic):
   - Vercel auto-detects `requirements.txt`
   - Installs Python dependencies for the serverless function

3. **Runtime**:
   - `/api/index.py` imports the Flask app from `serve.py`
   - All routes (`/`, `/api/*`) are handled by the Python serverless function
   - Flask serves the built Vue app from `static/dist/`
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

- **buildCommand**: Builds the Vue frontend
- **outputDirectory**: Points to where Vue builds output (matches `client/vite.config.js` outDir)
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
# Configure Flask to serve Vue build output
app = Flask(
    __name__,
    static_folder='static/dist/assets',
    static_url_path='/assets'
)

@app.route("/")
def index():
    """Serve the Vue app"""
    static_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'dist')
    return send_from_directory(static_dist, 'index.html')
```

Flask is configured to:
- Serve static assets from `static/dist/assets` at `/assets/*`
- Serve the Vue app's `index.html` at the root `/`
- Handle API routes at `/api/*`

### Deployment Requirements

1. **Vue build output** must be in `static/dist/` (configured in `client/vite.config.js`)
2. **Python dependencies** must be in `requirements.txt` (Vercel auto-installs)
3. **Module imports** in `api/index.py` must handle parent directory path
4. **Flask static configuration** must point to built Vue assets

### Common Deployment Issues

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

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture and data flow
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - File structure overview
- [BUGS.md](BUGS.md) - Known issues
- [CLIENTSIDE_TESTING.md](CLIENTSIDE_TESTING.md) - Frontend testing guide

## Environment Variables

Create a `.env` file with:

```bash
OPENAI_API_KEY=your_api_key_here
LOG_LEVEL=INFO  # Optional, defaults to INFO
```

## License

MIT
