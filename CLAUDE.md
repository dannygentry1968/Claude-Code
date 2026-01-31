# AI Article Generator

An AI-powered tool for researching and generating education articles, saved directly to Google Docs.

## Project Overview

- **Purpose**: Research topics and draft education articles using Claude AI
- **Deployment**: Docker container on Hostinger VPS with Cloudflare Tunnel
- **Stack**: Python 3.11, FastAPI, Google Docs API, Anthropic Claude API

## Key Files

| File | Purpose |
|------|---------|
| `src/article_generator/web.py` | FastAPI web interface |
| `src/article_generator/ai_writer.py` | Claude AI article generation |
| `src/article_generator/research.py` | Web research module |
| `src/article_generator/google_docs.py` | Google Docs integration |
| `src/article_generator/cli.py` | Command-line interface |
| `docker-compose.yml` | Docker deployment config |

## Deployment

**Hostinger server location:** `/home/ai-article-generator`

**Update workflow:**
1. Make changes in this session
2. Commit and push to `claude/ai-article-generator-BapLI`
3. On Hostinger, run:
   ```bash
   cd /home/ai-article-generator
   git pull origin claude/ai-article-generator-BapLI
   docker compose down
   docker compose up -d --build
   ```

## Credentials

- Google OAuth credentials: `credentials/credentials.json`
- Google token: `credentials/token.json`
- Anthropic API key: In `.env` file on server

## Feature Ideas (Not Yet Implemented)

- Article templates (lesson plans, newsletters, etc.)
- Edit before saving to Google Docs
- Article length slider
- Source URL input for specific research
- Batch generation from topic list
