---
name: vercel
description: read this before performing Vercel operations
last_updated: 2026-01-05 06:42, 473c5f4
---
# Vercel Deployment Operations

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
