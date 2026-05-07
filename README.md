---
last_updated: 2026-05-07 12:13
description: light overview over the project
---
# TLDRScraper

Mobile Web Newsletter Aggregator that scrapes tech newsletters from multiple sources, displays them in a unified interface, and provides AI-powered summaries and digests.

## Architecture

- **Frontend**: React 19 + Vite (in `client/`)
- **Backend**: Flask + Python (serverless on Vercel)
- **AI**: Google Gemini 3.1 Pro Preview for summaries

See the docs in `docs/` for detailed architectural flows & user interactions documentation. Start with `docs/INDEX.md` to navigate correctly. Additionally, read [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for a map of the project structure.

## Development

## Development & Setup

### Running the server and logs watchdog
```bash
# Install all required tooling and ecosystem, and verify the environment and dependencies are set up correctly, including the server and the client in one go:
source ./setup.sh

# Start the server and client in dev mode.
# Server: 5001
# Client: 3000
just dev

# Exercise the API with curl requests.
curl http://localhost:5001/api/scrape
curl http://localhost:5001/api/summarize-url
curl ...additional endpoints that may be relevant...

# Stop the server and client. 
just stop
```

---

## Documentation

- [docs/](docs/) - Detailed architectural flows & user interactions documentation broken down by domain
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Map of the project structure
- [GOTCHAS.md](GOTCHAS.md) - Documented solved tricky past bugs
