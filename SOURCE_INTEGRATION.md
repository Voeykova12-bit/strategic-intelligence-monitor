# Strategy Radar source integration

The supplied `Ресурсы для рисеча 2.docx` is represented by
`config/research_sources.json`: 15 additional source adapters and eight mappings
to existing coverage. Frank RG's repeated entry is one collector. Existing
New Retail, Data Insight, Banki.ru, RBC Realty, Romir and CBR feeds are reused;
CBR's research section adds discovery under the same publisher identity.

## Editorial weights

Weights are editorial priors on a 1–5 scale, not probabilities or guarantees.
CBR: 5.0; primary industry researchers DSM, INFOLine, Frank RG: 4.8;
consumer research: 4.7; research distribution and professional media: 4.2–4.6.
Fashion Consulting Group Telegram: 3.3, supplementary only. It cannot by itself
confirm a trend and is excluded from the homepage's leading news.

Pharma and Fashion are first-class market and report categories. Other
categories are assigned from the source's sector and article keywords; mortgage
coverage can therefore appear in both banking and real estate. Levada and
VCIOM require consumer or economic relevance and reject political headlines.

## Collection and limitations

RSS and public HTML are fetched with bounded timeouts. HTML articles must have
a parseable publication date in metadata, structured data, a date element or
their own listing link. Missing dates are skipped, never set to the crawl date.
JavaScript-only pages, blocked requests, paywalls and pages without reliable
dates do not produce fabricated records. An empty result is explicitly recorded
as `no_dated_items`; transport failures are `error`. `source_stats` and `errors`
in the news dataset contain the per-run audit. Source registration does not mean
that every source contributes a qualifying story on every refresh.

Deduplication uses canonical URLs with tracking parameters removed and normalized
headlines across both collectors. Query identifiers such as INFOLine's `news`
are preserved. RBC sections and CBR feeds share publisher identities when
counting independent evidence. Trend descriptions are editorial interpretations
of topic-matched evidence, not automated causal verification.

The preceding 365-day archive is retained across transient collection errors.
Reports retain their publication/landing URLs, public PDF links when discovered,
and existing locally archived PDFs. Unverified report links are marked visibly.
Metric fallback retains the last successful value and flags it as saved.

## Publishing

`docs/` is the published site; `site/` holds the same UI assets. Dataset copies
and the browser fallback are built together. Validation rejects empty datasets,
duplicate article URLs/IDs, invalid dates, missing PDFs and unsynchronized assets.

GitHub Actions runs tests on pull requests. On main and the daily 05:15 UTC
schedule it collects, validates, saves the archive with race-safe retries,
uploads the Pages artifact, and deploys it explicitly. Scheduled jobs may start
later than their configured time according to GitHub's queue.

Tests: `python -m pytest tests/test_static_pipeline.py -q`,
`node --test tests/static_ui.test.cjs`, and `python scripts/validate_static.py`.
