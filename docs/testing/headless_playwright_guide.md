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

### Rule #1: Visibility Matters
Playwright's visibility checks are strict. Visual-only hiding (e.g., `opacity: 0`, `height: 0`) is often insufficient for `expect(locator).not_to_be_visible()` assertions or ensuring elements are removed from the accessibility tree.
*   **Best Practice:** Always pair transitions with `visibility: hidden` or `display: none` for the final collapsed state.
*   **Interaction:** Standard `.click()` works reliably if the element is truly visible and not covered. `force=True` should be a last resort for known overlays, not a default fix.

### Rule #2: Use Or Create Stable Selectors
In dynamic situations (for example, when lists re-render or re-sort), avoid "reverse engineering" the element's true state with convoluted CSS selector (in the resorted list case, a bad example is index-based selectors) because they become stale instantly.
-   **Best Practice:** Use existing or otherwise instrument component HTML elements with data attributes that always reflect that component's current state as well as the data it contains (mirroring the shape of the data that was used to build it for least surprise) to make it trivial to find that component and inspect its state in a headless Playwright session.
-   **Rule of Thumb:** If what you're probing for about an HTML element is important, has to do with state, or involves trial and error to infer, it should have a dedicated data attribute that makes it easy to debug.

### Rule #3: Trust JS Execution for Setup
For setting up test state (e.g., seeding `localStorage`, bypassing lengthy UI flows), direct execution is faster and cleaner.

```python
# ✅ RELIABLE: Direct localStorage manipulation
page.evaluate("localStorage.setItem('user-settings', JSON.stringify({theme: 'dark'}))")
```

### Rule #4: Forget Video & Drag-n-Drop
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
| **Clicking** | ✅ **Stable** | Standard clicks work if DOM visibility is handled correctly. |
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


## 6. Practical Recipes & Patterns

### How to Handle Collapsible Content (Visibility)
If `expect(locator).not_to_be_visible()` fails for a collapsed element:
1.  **Check CSS:** Ensure the element has `visibility: hidden` (Tailwind `invisible`) or `display: none` (`hidden`).
2.  **Avoid:** Relying solely on `opacity: 0` or `height: 0`. These hide the element visually but leave it in the DOM/accessibility tree, causing test assertions to fail.
3.  **Pattern:**
    ```jsx
    // React Component
    <div className={`transition-all ... ${expanded ? 'opacity-100' : 'opacity-0 invisible'}`}>
      {content}
    </div>
    ```

### How to Select Elements in Dynamic Lists
If your tests fail with "element detached" or "element not visible" after modifying a list (e.g., removing an item):
1.  **Stop:** Do not use index-based selectors like `.first`, `.nth(0)`, or `.locator('div').first`.
2.  **Start:** Add stable `data-testid` attributes to your components.
    ```jsx
    // React Component
    <div data-testid={`article-card-${article.url}`}>...</div>
    ```
3.  **Test:**
    ```python
    # Playwright
    card = page.locator(f'div[data-testid="article-card-{url}"]')
    ```

### How to Ensure Clean Test Runs
If tests fail randomly due to previous state:
1.  **Script It:** Create a transient cleanup script (e.g., `clean_today.py`) that connects to the database and wipes relevant rows.
2.  **Run It:** Execute this script *before* your test command in the pipeline or shell.
    ```bash
    uv run python3 clean_today.py && uv run --with=playwright python3 test_my_feature.py
    ```

### How to Debug "Invisible" Interactions
If an interaction (click) seems to happen but the UI doesn't update:
1.  **Trace Lifecycle:** Add `console.log` to the component's render and event handlers.
2.  **Listen:** In your Playwright script, pipe console logs to stdout:
    ```python
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    ```
3.  **Verify:** Check if the event handler actually fired. If yes, the issue is likely CSS/Rendering (see "Visibility"). If no, the issue is likely the selector or overlay (see "Golden Rule #1").
