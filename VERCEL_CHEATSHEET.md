## Vercel Edge Config + API Cheatsheet

### What we actually used (and what tripped us up)

- Edge Config read via connection string
  - Connection string: `https://edge-config.vercel.com/<EDGE_ID>?token=<READ_TOKEN>`
  - Read all items: `curl -H "Authorization: Bearer <READ_TOKEN>" https://edge-config.vercel.com/<EDGE_ID>/items`
  - Note: That endpoint is read-only and uses the Edge Config read token from the connection string, not the Vercel API token.

- Edge Config write via Vercel REST API
  - Base: `https://api.vercel.com/v1/edge-config`
  - The write endpoint: `PATCH /v1/edge-config/{EDGE_ID}/items`
  - Auth: header `Authorization: Bearer <VERCEL_TOKEN>`
  - Payload shape that actually succeeded:
    ```json
    {
      "items": [
        { "operation": "delete", "key": "old-key" },
        { "operation": "upsert", "key": "2025-09-20-ai", "value": { "articles": [ { "title": "...", "url": "..." } ] } }
      ]
    }
    ```
  - Common gotcha: using `op` instead of `operation` yields 400 with message about missing `operation`.
  - Another gotcha: wrong HTTP method or path. `POST /v1/edge-config/{id}/items` returned 404. Use `PATCH`.
  

- Discovering account + team + configs
  - Current user: `GET https://api.vercel.com/v2/user` (shows `defaultTeamId`).
  - List configs: `GET https://api.vercel.com/v1/edge-config` (optionally `?teamId=<TEAM_ID>`). Response contains `id`, `slug`, `itemCount`.

### Practical commands that worked

- Read items via connection string token:
  ```bash
  curl -s -H "Authorization: Bearer $READ_TOKEN" "https://edge-config.vercel.com/$EDGE_ID/items" | jq -S .
  ```

- Write items (batch upsert/delete) via API token and team scope:
  ```bash
  curl -s -X PATCH \
    "https://api.vercel.com/v1/edge-config/$EDGE_ID/items" \
    -H "Authorization: Bearer $VERCEL_TOKEN" \
    -H "Content-Type: application/json" \
    --data-binary @ops.json
  ```

- List configs to confirm ownership/scope:
  ```bash
  curl -s -H "Authorization: Bearer $VERCEL_TOKEN" \
    "https://api.vercel.com/v1/edge-config" | jq .
  ```

### Data modeling tips we implemented

- Keys: `{YYYY-MM-DD}-{type}` (date-first for sortability).
- Values: `{ "articles": [ { "title": str, "url": str }, ... ] }`.
- Do not duplicate `type`, `date`, `category`, or `status` in the value; derive from key or omit.
- Remove all `utm_*` query params from stored URLs.
- Exclude sponsor links: treat `utm_medium=newsletter` (or typo `newletter`) as sponsored and skip.

### Common pitfalls (and how we solved them)

#### 1) Using the wrong auth/host for reads vs writes
- Reads use the Edge Config connection string host `edge-config.vercel.com` with the `token` from the connection string.
- Writes use the Vercel REST API host `api.vercel.com` with the `VERCEL_TOKEN`.

#### 2) Wrong HTTP method/path for mutations
- `POST /v1/edge-config/{id}/items` returned 404.
- The correct method was `PATCH /v1/edge-config/{id}/items`.

#### 3) Wrong payload shape
- `{"items":[{"op":"upsert", ...}]}` failed with 400. It requires `operation` instead of `op`.
- Working shape is `{"items":[{"operation":"upsert", ...},{"operation":"delete",...}]}`.

#### 4) 
 

#### 5) Mixing redundant fields in values
- Storing `newsletter_type`, `date`, `category`, `status` bloated values and caused inconsistencies. We standardized on deriving type/date from the key and omitting `status` entirely.

### Handy one-liners

- Extract `EDGE_ID` and `READ_TOKEN` from connection string:
  ```bash
  CONN="$TLDR_SCRAPER_EDGE_CONFIG_CONNECTION_STRING"
  EDGE_ID=$(basename "${CONN%%\?*}")
  READ_TOKEN="${CONN##*token=}"
  ```

- Count items in the store:
  ```bash
  curl -s -H "Authorization: Bearer $READ_TOKEN" "https://edge-config.vercel.com/$EDGE_ID/items" | jq 'to_entries | length'
  ```

- Pretty-print and sort by keys:
  ```bash
  curl -s -H "Authorization: Bearer $READ_TOKEN" "https://edge-config.vercel.com/$EDGE_ID/items" | jq -S .
  ```

