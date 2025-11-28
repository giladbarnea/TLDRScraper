---
last_updated: 2025-11-28 19:07, ff18d4b
---
# Cloudflare Tunnel for Remote Testing

## Active Tunnel

**URL:** https://handy-waters-diary-liz.trycloudflare.com
**Target:** localhost:3000 (Vite dev server)
**PID:** 89176 (saved to `~/.cache/cloudflared/tunnel.pid`)  (may change by the time you read this)
**Logs:** `~/.cache/cloudflared/tunnel.log`

## Remote Shell Access

Remote shell API: `https://josue-ungreedy-unphysically.ngrok-free.dev`

```bash
# Create session
SID=$(curl -X POST https://josue-ungreedy-unphysically.ngrok-free.dev/session -s)

# Run commands
curl -X POST "https://josue-ungreedy-unphysically.ngrok-free.dev/session/$SID" \
  -d "cd ~/dev/TLDRScraper && pwd" -s
```

**Important:** Commands >5 seconds timeout via the ngrok URL. Use background processes with PID files.

## Browser Testing via Tunnel

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://handy-waters-diary-liz.trycloudflare.com')
    page.screenshot(path='/tmp/app.png')
    browser.close()
```

## Background Process Pattern

```bash
# Start process in background, persist PID
(
  command args > /tmp/output.log 2>&1 &
  echo $! > /tmp/process.pid
  wait
) &

# Probe status
cat /tmp/process.pid
ps -p $(cat /tmp/process.pid)
tail /tmp/output.log
```

## Tunnel Management

```bash
# Check tunnel status
ps -p 89176

# View tunnel URL
grep "trycloudflare.com" ~/.cache/cloudflared/tunnel.log
```

Note: may give good results https://github.com/ultrafunkamsterdam/undetected-chromedriver

this is also interesting: https://github.com/coder/agentapi
