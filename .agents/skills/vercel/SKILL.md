---
name: vercel
description: read this before performing Vercel operations
last_updated: 2026-05-07 12:50, df68ef0
---
# Vercel Deployment Operations

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

---

## Vercel CLI Limitations

The Vercel CLI does not function in this environment:

- `vercel deploy --token="$VERCEL_TOKEN"` fails with "No existing credentials found"
- Passing token via environment variable (`VERCEL_TOKEN=... vercel deploy`) fails identically
- Creating `.vercel/project.json` with orgId and projectId does not resolve authentication
- Git author permission errors ("Git author noreply@anthropic.com must have access") are misleading - authentication is the actual blocker

**Do not use the Vercel CLI.**

## Vercel API via curl Limitations

Direct API calls using curl fail with token authentication:

```bash
curl -H "Authorization: Bearer $VERCEL_TOKEN" \
  https://api.vercel.com/v6/deployments?projectId=$VERCEL_PROJECT_ID
```

Returns: `{"error": {"code": "forbidden", "message": "The request is missing an authentication token", "missingToken": true}}`

This occurs despite:
- Token existing in environment (`${#VERCEL_TOKEN}` confirms length)
- Correct Bearer token syntax
- Valid token format verification

Root cause: shell variable interpolation or curl header parsing fails to properly handle the token value.

**Do not use curl for Vercel API calls.**

## Working Method: Python requests Library

Use Python's `requests` library with `os.environ.get()` for token access:

```python
import os, requests, json

token = os.environ.get('VERCEL_TOKEN')
project_id = os.environ.get('VERCEL_PROJECT_ID')
org_id = os.environ.get('VERCEL_ORG_ID')

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Get project repoId
url = f'https://api.vercel.com/v9/projects/{project_id}?teamId={org_id}'
r = requests.get(url, headers=headers)
repo_id = r.json()['link']['repoId']

# Create deployment
payload = {
    'name': 'tldr-flask-scraper',
    'project': project_id,
    'gitSource': {
        'type': 'github',
        'ref': 'branch-name',
        'repoId': repo_id
    }
}

url = 'https://api.vercel.com/v13/deployments'
r = requests.post(url, headers=headers, json=payload)
result = r.json()

if r.status_code == 200:
    print(f"Preview URL: https://{result['url']}")
    print(f"Inspector: {result['inspectorUrl']}")
```

## Required Parameters

**For deployments:**
- `name`: Project name (string)
- `project`: Project ID from `$VERCEL_PROJECT_ID`
- `gitSource.type`: "github"
- `gitSource.ref`: Branch name or commit SHA
- `gitSource.repoId`: Numeric GitHub repository ID (must fetch from project API)

**Do not include:**
- `target`: Parameter is invalid for preview deployments. Omit entirely.

## Obtaining repoId

The GitHub repository ID must be retrieved from the project API:

```python
url = f'https://api.vercel.com/v9/projects/{project_id}?teamId={org_id}'
r = requests.get(url, headers=headers)
repo_id = r.json()['link']['repoId']  # Returns integer like 1063075532
```

Cannot be hardcoded. Must be fetched per deployment.

## Available Environment Variables

- `VERCEL_TOKEN`: Authentication token
- `VERCEL_PROJECT_ID`: Project identifier
- `VERCEL_ORG_ID`: Team/organization identifier
- `VERCEL_PROJECT_NAME`: Human-readable project name
- `VERCEL_PROD_DEPLOYMENT_URL`: Production URL

## Execution Pattern

Always use `uv run --with=requests python3` for Vercel operations. Inline scripts prevent file creation overhead:

```bash
uv run --with=requests python3 <<'PYTHON'
import os, requests, json
# ... Python code here
PYTHON
```
