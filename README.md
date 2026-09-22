# Strategic Intelligence Monitor

Internal news-intelligence platform for an advertising-agency strategy team. It collects news, normalizes and deduplicates them into story clusters, classifies market/brand/topic relevance, adds strategic analysis, tracks clients/competitors, exposes search/API endpoints, generates signals/trends and builds a daily brief.

## What is implemented in this MVP

- Configurable RSS collectors (`config/sources.yaml`)
- robots.txt-aware article extraction
- canonical URL + title-similarity deduplication and story clusters
- cheap prefilter before AI
- OpenAI Responses API integration with JSON Schema Structured Outputs
- heuristic local fallback when no OpenAI key is configured
- client trackers (`config/clients.yaml`)
- strategic scoring 1–5
- embeddings + pgvector semantic search when OpenAI/PostgreSQL are enabled
- persistent AI token/cost ledger and daily budget guard
- FastAPI backend and Swagger docs
- Streamlit internal dashboard
- signal/trend detection
- morning digest
- Telegram delivery
- Celery + Redis background collection / scheduled digest
- PostgreSQL + pgvector via Docker Compose
- SQLite fallback for simple local development/tests
- pytest test suite

## Architecture

`SOURCE -> FETCH -> PARSE -> NORMALIZE -> DEDUP -> PREFILTER -> AI ANALYSIS -> SCORE -> DB -> SEARCH/DASHBOARD/DIGEST`

The code is split into collectors, parsers, AI providers, services, API, workers and UI so a new source or model provider does not require rewriting the pipeline.

## Fastest start: Docker Desktop

1. Install Docker Desktop.
2. Copy environment settings:

```bash
cp .env.example .env
```

3. Open `.env`. Add `OPENAI_API_KEY=...` if you want full AI analysis. If the key is empty, the product still runs using the built-in heuristic analyzer.
4. Start the stack:

```bash
docker compose up --build
```

5. Open:
   - Dashboard: http://localhost:8501
   - API docs: http://localhost:8000/docs
   - Health: http://localhost:8000/api/health

6. Click **Collect now** in the dashboard, or call:

```bash
curl -X POST http://localhost:8000/api/collect
```

## Load demo data first

If you want to see the interface immediately:

```bash
docker compose exec api python scripts/seed_demo.py
```

Refresh the dashboard.

## Run without Docker (simple local mode)

This uses SQLite by default.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/seed_demo.py
uvicorn app.main:app --reload
```

In a second terminal:

```powershell
.venv\Scripts\Activate.ps1
streamlit run dashboard/app.py
```

For Streamlit outside Docker, set:

```powershell
$env:DASHBOARD_API_URL="http://localhost:8000"
```

## Sources

Edit `config/sources.yaml` to add/remove feeds. No core-code changes are needed.

Example:

```yaml
- name: Company newsroom
  type: rss
  url: https://example.com/feed.xml
  language: ru
  country: RU
  reliability_score: 4.5
  priority: 5
  topics: [retail, marketing]
```

RSS/API should be preferred over HTML scraping. The extractor respects `robots.txt` by default.

### Current starter feeds

The starter configuration uses Google News RSS topic queries for broad market discovery and a Habr RSS feed for technology. Treat aggregators as discovery surfaces; the stored article URL/source should be inspected and source-quality weights adjusted as your agency builds a vetted source list.

## Client trackers

Edit `config/clients.yaml`:

```yaml
- slug: client-name
  name: Client Name
  industry: Retail
  brands: [Brand A]
  competitors: [Brand B, Brand C]
  track: [advertising, pricing, launches, sponsorship]
```

The pipeline calculates per-client relevance and the dashboard exposes client-specific feeds.

## OpenAI

Set in `.env`:

```env
OPENAI_API_KEY=...
AI_PROVIDER=auto
OPENAI_MODEL=gpt-5.6-terra
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

`auto` uses OpenAI when a key exists and otherwise falls back to local heuristics. The default analysis model is `gpt-5.6-terra` to balance quality and high-volume cost. The provider is isolated under `app/ai/`, so it can be replaced later. The pipeline stops paid AI calls when the configured daily budget is reached.

## Telegram

1. Create a bot with BotFather.
2. Put token/chat ID into `.env`:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Celery Beat sends the morning digest at `DIGEST_HOUR_LOCAL` in `APP_TIMEZONE`. For commands (`/today`, `/search`, `/signals`, `/trends`, `/industry`, `/client`), point Telegram webhook to `https://YOUR_DOMAIN/api/telegram/webhook`.

## Useful API endpoints

- `GET /api/articles`
- `GET /api/search?q=...`
- `GET /api/search/semantic?q=...`
- `GET /api/signals?days=30`
- `GET /api/trends?days=30`
- `GET /api/clients`
- `GET /api/clients/{slug}/articles`
- `GET /api/digest`
- `GET /api/articles/{id}/strategy-slide`
- `GET /api/sources/health`
- `GET /api/ai/usage`
- `POST /api/collect`
- `POST /api/telegram/webhook`

## Tests

```bash
pytest -q
```

## Production hardening recommended before agency-wide rollout

The MVP is deliberately functional and extensible, but an agency-wide deployment should add: SSO/RBAC, a source-admin UI, persistent AI cost ledger with model-price configuration, alerting/observability (Sentry/Prometheus), queue-level rate limits, legal review of each non-RSS source, a curated source whitelist, multilingual entity resolution, stronger semantic clustering, backup/retention policy, and evaluation datasets for strategic scoring quality.

## Important operating principle

Do not send every collected item to the LLM. The pipeline first performs cheap filtering and deduplication. This is essential when coverage expands across many markets.
