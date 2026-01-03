#!/bin/bash

set -e

echo "Setting up Gemini CLI with Vertex AI using service account..."

# 1. Check if GCLOUD_SERVICE_ACCOUNT_KEY is set
if [ -z "$GCLOUD_SERVICE_ACCOUNT_KEY" ]; then
    echo "❌ Error: GCLOUD_SERVICE_ACCOUNT_KEY environment variable is not set"
    exit 1
fi

# 2. Remove *.googleapis.com from NO_PROXY to allow proxy DNS resolution
# The proxy (CLAUDE_CODE_PROXY_RESOLVES_HOSTS=true) handles DNS correctly,
# but NO_PROXY bypasses it, causing DNS failures
export NO_PROXY="${NO_PROXY//,*.googleapis.com/}"
export NO_PROXY="${NO_PROXY//,*.google.com/}"
export no_proxy="$NO_PROXY"
export GLOBAL_AGENT_NO_PROXY="$NO_PROXY"

# 3. Write raw JSON key to temp file
echo "$GCLOUD_SERVICE_ACCOUNT_KEY" > /tmp/gcp-key.rawjson

# 4. Parse and format JSON properly using Python
uv run python3 - <<'EOF'
import json
import sys

# Read the raw JSON
with open('/tmp/gcp-key.rawjson', 'r') as f:
    raw_content = f.read().strip()

try:
    # First parse: remove outer JSON encoding
    decoded = json.loads(raw_content)

    # If it's a string (double-encoded), parse it as Python dict literal
    if isinstance(decoded, str):
        # The string is a Python dict with actual newlines in it
        # Escape newlines so eval can parse it
        escaped = decoded.replace('\n', '\\n')
        parsed = eval(escaped)
    else:
        parsed = decoded

    # Write properly formatted JSON
    with open('/tmp/gcp-key.json', 'w') as out:
        json.dump(parsed, out, indent=2)

    # Extract project_id for verification
    project_id = parsed.get('project_id', 'UNKNOWN')
    print(f"✓ Parsed service account for project: {project_id}", file=sys.stderr)

except (json.JSONDecodeError, SyntaxError, ValueError) as e:
    print(f"❌ Error parsing credentials: {e}", file=sys.stderr)
    sys.exit(1)
EOF

# 5. Set authentication
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json

# 6. Extract project ID from the JSON key
PROJECT_ID=$(uv run python3 -c "import json; print(json.load(open('/tmp/gcp-key.json'))['project_id'])")

# 7. Set project and location
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="us-central1"

# 8. Tell Gemini CLI to use Vertex AI (CRITICAL!)
export GOOGLE_GENAI_USE_VERTEXAI=true

# 9. Unset conflicting variables
unset GOOGLE_API_KEY
unset GEMINI_API_KEY

echo "✓ Gemini CLI configured for Vertex AI"
echo "  Project: $GOOGLE_CLOUD_PROJECT"
echo "  Location: $GOOGLE_CLOUD_LOCATION"
echo "  Credentials: $GOOGLE_APPLICATION_CREDENTIALS"
echo ""
echo "Environment variables set:"
echo "  - GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json"
echo "  - GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
echo "  - GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION"
echo "  - GOOGLE_GENAI_USE_VERTEXAI=true"
echo ""
echo "NOTE: You must source this script to export variables to your shell:"
echo "  source scripts/setup_gemini_vertex_ai.sh"
