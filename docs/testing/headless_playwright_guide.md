---
last_updated: 2025-11-29
---
# Headless Playwright Guide: SSH, Sandboxes, & Tunnels

**Goal:** Reliable end-to-end testing and automation in constrained environments (headless Linux, SSH-only, Docker containers) where standard GUI interactions fail.

## 1. The "Safe" Configuration

When running in a sandbox or headless environment (especially as root or without proper GPU support), use these specific launch arguments to prevent crashes and permission errors.

```python
from playwright.sync_api import sync_playwright

def launch_safe_browser(p):
    return p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',        # Prevents crash on low shared memory
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-web-security',         # Optional: Handle CORS/mixed content
            '--disable-features=IsolateOrigins,site-per-process', # Optional: iframe stability
        ]
    )
```

## 2. Environment & Process Management (Local/SSH)

When working directly on the machine (e.g., via SSH), no tunnels or "remote shells" are required. You manage the application lifecycle directly.

### Checking Status
Before starting services, verify if they are already running:

```bash
# Check Backend
pgrep -fal serve.py

# Check Frontend
pgrep -fal vite
```

### Manual Startup (Fallback)
If `setup.sh` helper functions (like `start_server_and_watchdog`) fail or you need more control, run the services manually in the background.

**Backend (Flask):**
```bash
(
  cd $(git rev-parse --show-toplevel)
  uv run python3 serve.py >> flask_server.log 2>&1 &
  echo $! > flask_server.pid
  wait
) &
```

**Frontend (Vite):**
```bash
(
  cd $(git rev-parse --show-toplevel)/client
  npm run dev -- --host >> vite_client.log 2>&1 &
  echo $! > vite_client.pid
  wait
) &
```

### Restart/Cleanup
If the environment is in an uncertain state, kill the processes and restart:

```bash
# Kill by known PIDs
[ -f flask_server.pid ] && kill $(cat flask_server.pid)
[ -f vite_client.pid ] && kill $(cat vite_client.pid)

# Or kill by name (careful!)
pkill -f serve.py
pkill -f vite
```

## 3. The Golden Rules of Sandboxed Automation

### Rule #1: Trust JS Execution (`page.evaluate`) Over UI Interactions
Direct DOM manipulation is 100% reliable. Simulated pointer events are flaky in headless mode due to missing layout engines or overlay interception.

```python
# ❌ FLAKY: Might hit an overlay or miscalculate position
page.locator("#submit-btn").click()

# ✅ RELIABLE: Direct JS execution
page.evaluate("document.querySelector('#submit-btn').click()")

# ✅ RELIABLE: Direct localStorage manipulation
page.evaluate("localStorage.setItem('user-settings', JSON.stringify({theme: 'dark'}))")
```

### Rule #2: If You Must Click, Use Force
If you need Playwright's specific event dispatching, always bypass visibility/overlay checks.

```python
# ✅ RELIABLE
page.locator(".btn").click(force=True)
```

### Rule #3: Forget Video & Drag-n-Drop
Tested limitations in sandboxed environments:
*   **Video Recording:** Fails silently (directory created, but empty).
*   **Drag & Drop:** Causes the browser target to crash immediately.

## 3. Capability Matrix

| Feature | Status | Notes |
| :--- | :--- | :--- |
| **page.evaluate()** | ✅ **Stable** | Preferred method for all state/DOM interactions. |
| **localStorage** | ✅ **Stable** | Full read/write access via `evaluate`. |
| **Screenshots** | ✅ **Stable** | Works for full page and specific elements. |
| **Network Mocking** | ✅ **Stable** | `page.route` and `page.on("request")` work perfectly. |
| **Form Fill** | ✅ **Stable** | `fill()` and `type()` work reliably. |
| **Clicking** | ⚠️ **Caveats** | Requires `force=True` to avoid overlay errors. |
| **Video Record** | ❌ **Broken** | Does not produce output files. |
| **Drag & Drop** | ❌ **Broken** | Crashes the browser tab. |

## 4. Tunneling & Remote Access

### Preferred: Cloudflare Tunnel (`cloudflared`)
More stable than ngrok for long sessions.

1.  **Start Tunnel:**
    ```bash
    # Expose localhost:3000
    cloudflared tunnel --url http://localhost:3000 > tunnel.log 2>&1 &
    ```
2.  **Get URL:**
    ```bash
    grep "trycloudflare.com" tunnel.log
    ```

### Running Background Tasks
Prevent SSH timeouts or disconnection from killing your tests.

```bash
# Run script in background and save PID
(
  uv run python3 test_script.py > output.log 2>&1 &
  echo $! > script.pid
)

# Check status
ps -p $(cat script.pid)
tail -f output.log
```

## 5. Retrieving Artifacts (Screenshots)

If direct file transfer (scp, sftp) or upload services (transfer.sh) are blocked/broken: **Use Git.**

1.  **Snapshot:** Save screenshot to repo folder.
    ```python
    page.screenshot(path="debug_screenshots/state_01.png")
    ```
2.  **Push:**
    ```bash
    git checkout -b debug-$(date +%s)
    git add debug_screenshots/
    git commit -m "chore: add debug screenshots"
    git push origin HEAD
    ```
3.  **View:** Browse the branch on GitHub/GitLab to view the image.
