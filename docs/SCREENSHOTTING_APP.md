---
last_updated: 2025-11-18 10:35, af7d9f0
---
# How to Get Screenshots of the App from Remote

**Setup:** User has ngrok endpoint at `https://josue-ungreedy-unphysically.ngrok-free.dev/`

## Steps

1. **Verify Playwright is installed locally:**
```bash
curl -X POST https://josue-ungreedy-unphysically.ngrok-free.dev/shell -d "ls ~/Library/Caches/ms-playwright"
```

2. **Create and run Playwright script via heredoc:**
```bash
curl -X POST https://josue-ungreedy-unphysically.ngrok-free.dev/shell -d "cat > /tmp/screenshot.js << 'EOF'
const {chromium} = require('playwright');
(async () => {
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage();
  await page.setViewport({width: 1920, height: 1080});
  await page.goto('http://localhost:3000', {waitUntil: 'domcontentloaded', timeout: 30000});
  await page.waitForSelector('body');
  await new Promise(r => setTimeout(r, 4000));
  await page.screenshot({path: '/tmp/tldr_local.png', fullPage: true});
  await browser.close();
  console.log('Screenshot saved');
})();
EOF
cd ~/dev/TLDRScraper && node /tmp/screenshot.js && ls -lh /tmp/tldr_local.png" -s
```

3. **Transfer screenshot via Git:**
```bash
# Create temporary branch
curl -X POST https://josue-ungreedy-unphysically.ngrok-free.dev/shell -d "cd ~/dev/TLDRScraper && git checkout -b screenshots-$(date +%s)" -s

# Copy, commit, and push
curl -X POST https://josue-ungreedy-unphysically.ngrok-free.dev/ -d "cd ~/dev/TLDRScraper && cp /tmp/tldr_local.png ./screenshot.png && git commit -am 'Add screenshot' && git push --set-upstream origin HEAD 2>&1 | grep -E 'screenshots-|branch'" -s
```

Note the branch name from output (e.g., `screenshots-1763449916`)

4. **Download screenshot via GitHub raw URL:**
```bash
curl -s "https://raw.githubusercontent.com/giladbarnea/TLDRScraper/screenshots-1763449916/screenshot.png" -o /tmp/tldr_screenshot.png
file /tmp/tldr_screenshot.png  # Verify it's a valid PNG
```

5. **Display in conversation:** Use Read tool on `/tmp/tldr_screenshot.png`

## Cleanup

**Remote machine:**
```bash
# Remove temp files
curl -X POST https://josue-ungreedy-unphysically.ngrok-free.dev/ -d "rm /tmp/tldr_local.png /tmp/screenshot.js" -s

# Delete local git branch
curl -X POST https://josue-ungreedy-unphysically.ngrok-free.dev/ -d "cd ~/dev/TLDRScraper && git checkout - && git branch -D screenshots-1763449916" -s
```

**Remote GitHub:**
```bash
# Delete remote branch (requires valid GITHUB_API_TOKEN)
curl -X DELETE "https://api.github.com/repos/giladbarnea/TLDRScraper/git/refs/heads/screenshots-1763449916" \
  -H "Authorization: token ${GITHUB_API_TOKEN}" -s
```

**Local machine:**
```bash
rm /tmp/tldr_screenshot.png /tmp/screenshot_script.js
```

## Notes

* **Heredoc vs inline:** Heredoc approach (`cat > file << 'EOF'`) works better than inline escaped JavaScript - avoids quote escaping hell
* **File upload services:** `file.io` and `transfer.sh` timeout with ngrok (ERR_NGROK_3004) - likely a bug in the remoteshell server handling long-running commands
* **Git method:** Most reliable for this setup despite extra steps
