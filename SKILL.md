# Skill: Daily arxiv Research Paper Digest

## Overview

Automated daily pipeline that fetches new papers from arxiv, filters them by
research interests using **LLM-based relevance evaluation**, generates a
structured Markdown digest, and adds matched papers to Zotero with attached PDFs.

This skill is designed to be **invoked by an upstream agent**. The digest is
written to a Markdown file; notification/delivery is the upstream agent's
responsibility.

## What It Does

Every weekday at **14:00 GMT+8** (06:00 UTC), the pipeline:

1. **Fetches** the daily RSS feed from `rss.arxiv.org` for channels:
   `cs.RO`, `cs.CV`, `cs.AI`, `cs.LG`
2. **Pre-filters** papers with cheap keyword matching (~700 → ~150 candidates)
3. **Evaluates** candidates via an **LLM** that scores each paper 1–5 against
   the research interest descriptions (see [Relevance Evaluation](#relevance-evaluation))
4. **Enriches** matched papers via the arxiv API to retrieve venue and project
   page information from the `comment` and `journal_ref` fields
5. **Generates** a Markdown digest grouped by announce type (new / cross / replace)
6. **Adds** papers to the Zotero personal library → `automated` collection, with:
   - Correct item types: `preprint`, `conferencePaper`, or `journalArticle`
   - PDF attachments (uploaded to Zotero cloud from arxiv)
   - Deduplication via local state + Zotero tag

## File Structure

```
/workspace/
├── arxiv_digest/
│   ├── config.py              # Configuration: interests, keywords, thresholds, LLM settings
│   ├── rss_fetcher.py         # RSS feed fetching & parsing
│   ├── relevance.py           # Two-stage relevance: keyword pre-filter + LLM evaluation
│   ├── arxiv_enricher.py      # Batch arxiv API queries
│   ├── venue_detector.py      # Venue & project page detection
│   ├── digest_generator.py    # Markdown digest rendering
│   ├── zotero_client.py       # Zotero API client (items + PDFs)
│   ├── run_digest.py          # Main orchestrator
│   ├── __main__.py            # python -m arxiv_digest support
│   ├── state/
│   │   └── processed_ids.json # Tracks which papers have been added to Zotero
│   └── output/
│       ├── digest_YYYY-MM-DD.md   # Daily digest files
│       └── run_YYYY-MM-DD.log     # Pipeline run logs
├── requirements.txt
├── setup_cron.sh              # Cron job installer
└── SKILL.md                   # This file
```

## Environment Requirements

| Variable | Description | Required |
|---|---|---|
| `ZOTERO_API_KEY` | Zotero API key with read/write access | **Yes** |
| `ZOTERO_USER_ID` | Zotero user ID (default: `11347333`) | **Yes** |
| `LLM_API_KEY` | API key for the LLM provider (OpenAI-compatible) | **Yes** (for LLM evaluation) |
| `LLM_MODEL` | Model name (default: `gpt-4o-mini`) | No |
| `LLM_BASE_URL` | Custom API base URL for non-OpenAI providers | No |

### Python Dependencies

```bash
pip install -r requirements.txt
# Requires: feedparser, requests, beautifulsoup4, lxml, openai
```

## How to Run

### Manual Run (full pipeline)

```bash
cd /workspace
python3 -m arxiv_digest
```

### Dry Run (no Zotero changes)

```bash
python3 -m arxiv_digest --dry-run
```

### Skip PDF Uploads (create Zotero items only)

```bash
python3 -m arxiv_digest --no-pdf
```

### Set Up Daily Cron Job

```bash
chmod +x setup_cron.sh
./setup_cron.sh
```

This installs a cron job that runs at 06:00 UTC (14:00 GMT+8), Monday–Friday.

## Relevance Evaluation

Relevance is determined through a **two-stage pipeline**:

### Stage 1 — Keyword Pre-filter (cheap, local)

A fast keyword scan reduces ~700 daily papers to ~150 candidates, saving LLM
tokens. The pre-filter threshold (`PREFILTER_THRESHOLD = 1.5`) is intentionally
low so that borderline papers still reach the LLM.

### Stage 2 — LLM Evaluation

Each candidate paper (title + abstract) is sent to an LLM along with the
research interest descriptions. The LLM returns:

- **score** (1–5): 1=irrelevant, 3=borderline, 5=highly relevant
- **interests**: which research interests matched
- **reason**: one-sentence explanation

Papers with score ≥ `RELEVANCE_THRESHOLD` (default: 3) are included in the
digest.

Papers are batched (`LLM_BATCH_SIZE = 10` per call) to balance token efficiency
and API round-trips.

### Upstream Agent Integration

In production, the upstream agent may choose to:

- **Provide its own `LLM_API_KEY`** and let this skill call the LLM directly, or
- **Arrange sub-agents** for the evaluation step — the interface is the same:
  each paper needs `relevance_score`, `matched_interests`, and `relevance_reason`
  populated on the `ArxivPaper` dataclass.

The `relevance.py` module exposes:
- `prefilter(papers)` → keyword-filtered candidates
- `llm_evaluate(papers)` → LLM-scored results
- `filter_relevant(papers)` → full two-stage pipeline (auto-selects LLM or fallback)

### Fallback (no LLM)

When `LLM_API_KEY` is not set, the pipeline falls back to keyword-only scoring
with a warning. This is functional but less accurate than LLM evaluation.

### Supported LLM Providers

Any **OpenAI-compatible** API works. Examples:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` |
|---|---|---|
| OpenAI | *(leave empty)* | `gpt-4o-mini` |
| Anthropic (via proxy) | `https://api.anthropic.com/v1` | `claude-3-5-haiku-latest` |
| Ollama (local) | `http://localhost:11434/v1` | `llama3` |
| vLLM | `http://localhost:8000/v1` | model name |
| Together AI | `https://api.together.xyz/v1` | model name |

## How to Modify Research Interests

Edit `arxiv_digest/config.py` → `INTEREST_PROFILES` list. Each profile has:
- `name`: Display name for the interest
- `description`: One-line description (used in the LLM prompt)
- `keywords`: List of `(phrase, weight)` tuples (used for the pre-filter stage)

For the **LLM evaluation**, the `name` and `description` fields are what matter
most — write clear, precise descriptions of your research interests.

For the **keyword pre-filter**, the `keywords` list determines which papers
reach the LLM. Add keywords generously (low weights are fine) to avoid
filtering out borderline papers before the LLM sees them.

### Adjusting the Relevance Threshold

In `config.py`:

- `PREFILTER_THRESHOLD` (default: `1.5`): keyword pre-filter cutoff.
  Lower = more candidates reach the LLM (costs more tokens).
- `RELEVANCE_THRESHOLD` (default: `3`): LLM score cutoff (1–5 scale).
  Lower = more papers included; higher = stricter.

### Adding New RSS Channels

Edit `RSS_CHANNELS` in `config.py`:
```python
RSS_CHANNELS = ["cs.RO", "cs.CV", "cs.AI", "cs.LG", "cs.CL"]
```

## Venue Detection

The pipeline checks for venue information in this order:
1. `journal_ref` field from arxiv API (most authoritative)
2. `comment` field — pattern matching for "Accepted at/by/for {Venue}"
3. Direct venue abbreviation matching (ICRA, CVPR, NeurIPS, etc.)

Known venues are defined in `config.py` → `VENUE_PATTERNS` dict.

## Deduplication

Papers are tracked by arxiv ID in two ways:
1. **Local state**: `state/processed_ids.json` — fast lookup
2. **Zotero tags**: Items tagged with `arxiv-digest` — recovers from state loss

On each run, local state is synced with Zotero before checking for new papers.

## Scheduling Details

- **arxiv RSS updates**: ~05:00 UTC (midnight Eastern Time)
- **Pipeline runs**: 06:00 UTC (1 hour buffer)
- **No weekend runs**: arxiv doesn't publish on Saturday/Sunday

If the arxiv RSS update time changes, adjust the cron schedule in `setup_cron.sh`.

## Output

### Digest Location

Digests are written to `arxiv_digest/output/digest_YYYY-MM-DD.md`.

The upstream agent is responsible for delivering the digest (e.g., email, Slack,
chat message). This skill only generates the file.

### Digest Format

Each paper in the digest includes:
- **arXiv link** (clickable)
- **Project page** (if found in comment field)
- **Venue** (conference/journal name, or "Preprint (arXiv)")
- **Announce type** (🆕 new / 🔀 cross / 🔄 replace / 🔁 replace-cross)
- **Authors**
- **Abstract** (full text)
- **Why Relevant** (LLM-generated explanation, or keyword matches in fallback mode)

## Troubleshooting

### No papers matched
- Check that `LLM_API_KEY` is set (keyword fallback is less accurate)
- Check `RELEVANCE_THRESHOLD` — lower it if the LLM is too strict
- Check `PREFILTER_THRESHOLD` — lower it if too few candidates reach the LLM
- Verify RSS feed: `curl https://rss.arxiv.org/rss/cs.RO | head`
- Check `output/run_YYYY-MM-DD.log`

### LLM evaluation issues
- Verify `LLM_API_KEY` is valid for the configured provider
- If using a non-OpenAI provider, set `LLM_BASE_URL`
- Check the log for "LLM API call failed" messages
- Reduce `LLM_BATCH_SIZE` if hitting token limits

### Zotero items not created
- Verify `ZOTERO_API_KEY` and `ZOTERO_USER_ID` environment variables
- Check API key permissions (needs read/write access to personal library)

### PDF upload failures
- arxiv may rate-limit PDF downloads (2-second delay is built in)
- Check disk space in `/tmp`
- Zotero storage quota may be exceeded

### Cron job not running
- Verify cron service: `service cron status`
- Check cron logs: `grep CRON /var/log/syslog`
- Verify env file: `cat /workspace/.env.cron`
- Test wrapper: `/workspace/run_digest_cron.sh`
