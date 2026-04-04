---
last_updated: 2026-04-04 09:05
---
# TLDRScraper - Pi Agent System Instructions

You are working on TLDRScraper, a newsletter aggregator with AI-powered summaries.

## Stack
- **Backend**: Python Flask (serverless on Vercel)
- **Frontend**: React 19 + Vite
- **Database**: Supabase PostgreSQL
- **AI**: Gemini 3 Pro Preview for summaries

## Key Files & Architecture
- `ARCHITECTURE.md` - Detailed flows and interactions
- `PROJECT_STRUCTURE.md` - File organization
- `server/` - Flask backend, API endpoints
- `client/` - React frontend
- `.claude/agents/` & `.claude/skills/` - Available utilities

## Available Commands
```bash
./setup.sh              # Install dependencies, build client, verify environment
pi -p "prompt"          # Non-interactive mode (returns immediately)
pi --models auto        # Switch models with Ctrl+P
pi --thinking high      # Enable extended thinking for complex tasks
```

## Model Recommendations
- **Fast & reliable**: `auto` (best for quick tasks)
- **Most capable**: `google/gemini-3.1-pro-preview` (reasoning, complex analysis)
- **Fast coding**: `z-ai/glm-5` (Chinese model, excellent for code)
- **Multimodal**: `minimax/minimax-m2.5` (if images needed)
- **Hardware-efficient**: `google/gemini-3-flash-preview` (balanced)

## Key Environment Variables
- `GEMINI_API_KEY` - Google Gemini API
- `OPENROUTER_API_KEY` - Access to multiple models
- `SUPABASE_URL`, `SUPABASE_SECRET_KEY` - Database

## Pro Tips
1. Use `./setup.sh` before starting to verify environment
2. Use `/catchup` skill to gather project context
3. For API testing: `curl http://localhost:5001/api/scrape`
4. Frontend dev: `cd client && npm run dev` (hot reload on :3000)
5. Always use `uv` for Python: `uv run python3 ...`

## Development Principles (from CLAUDE.md)
- Fail early and clearly rather than with fallbacks
- Use existing logic; don't re-implement
- Optimize for simplicity and clarity
- Trust upstream code to have completed its job
- No unnecessary defensive/speculative code
