# Skill: Daily arxiv Research Paper Digest

## Overview

Automated daily pipeline that fetches new papers from arxiv, filters them by
research interests, generates a structured Markdown digest, and adds matched
papers to Zotero with attached PDFs.

## What It Does

Every weekday at **14:00 GMT+8** (06:00 UTC), the pipeline:

1. **Fetches** the daily RSS feed from `rss.arxiv.org` for channels:
   `cs.RO`, `cs.CV`, `cs.AI`, `cs.LG`
2. **Filters** papers by relevance to two research interest profiles:
   - **Task Planning & Execution**: algorithms that schedule, plan, and execute
     atomic actions from natural-language commands
   - **Edge Inference for Robot Learning**: fast/real-time inference of robot
     policies on edge hardware (quantization, compression, efficient architectures)
3. **Enriches** matched papers via the arxiv API to retrieve venue and project
   page information from the `comment` and `journal_ref` fields
4. **Generates** a Markdown digest grouped by announce type (new / cross / replace)
5. **Adds** papers to the Zotero personal library → `automated` collection, with:
   - Correct item types: `preprint`, `conferencePaper`, or `journalArticle`
   - PDF attachments (uploaded to Zotero cloud from arxiv)
   - Deduplication via local state + Zotero tag

## File Structure

```
/workspace/
├── arxiv_digest/
│   ├── config.py              # Configuration: interests, keywords, thresholds
│   ├── rss_fetcher.py         # RSS feed fetching & parsing
│   ├── relevance.py           # Keyword-based relevance scoring
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
├── run_digest_cron.sh         # Cron wrapper (auto-generated)
├── .env.cron                  # Environment variables for cron (auto-generated)
└── SKILL.md                   # This file
```

## Environment Requirements

| Variable | Description | Required |
|---|---|---|
| `ZOTERO_API_KEY` | Zotero API key with read/write access | Yes |
| `ZOTERO_USER_ID` | Zotero user ID (default: `11347333`) | Yes |

### Python Dependencies

```bash
pip install -r requirements.txt
# Requires: feedparser, requests, beautifulsoup4, lxml
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

## How to Modify Research Interests

Edit `arxiv_digest/config.py` → `INTEREST_PROFILES` list. Each profile has:
- `name`: Display name for the interest
- `description`: One-line description
- `keywords`: List of `(phrase, weight)` tuples

Higher weight = stronger relevance signal. Weights of 3.0+ indicate strong
matches; 1.0–2.0 are weaker supporting signals.

### Adjusting the Relevance Threshold

In `config.py`, change `RELEVANCE_THRESHOLD` (default: `4.0`):
- **Lower** (e.g., 3.0) → more papers, higher recall, lower precision
- **Higher** (e.g., 6.0) → fewer papers, lower recall, higher precision

### Adding New RSS Channels

Edit `RSS_CHANNELS` in `config.py` to add more arxiv categories:
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
- **Skip days**: The RSS feed itself skips Saturday and Sunday

If the arxiv RSS update time changes, adjust the cron schedule in `setup_cron.sh`.

## Troubleshooting

### No papers matched
- Check `RELEVANCE_THRESHOLD` in config — it may be too high
- Verify RSS feed is working: `curl https://rss.arxiv.org/rss/cs.RO | head`
- Check the run log in `output/run_YYYY-MM-DD.log`

### Zotero items not created
- Verify `ZOTERO_API_KEY` and `ZOTERO_USER_ID` environment variables
- Check API key permissions (needs read/write access to personal library)
- Check run log for error messages

### PDF upload failures
- arxiv may rate-limit PDF downloads; the pipeline has a 2-second delay between uploads
- Check disk space in `/tmp` (PDFs are downloaded to temp directory)
- Zotero storage quota may be exceeded — check at zotero.org

### Cron job not running
- Verify cron service: `service cron status`
- Check cron logs: `grep CRON /var/log/syslog`
- Verify env file: `cat /workspace/.env.cron`
- Test wrapper: `/workspace/run_digest_cron.sh`

## Output Digest Format

Each paper in the digest includes:
- **arXiv link** (clickable)
- **Project page** (if found in comment field)
- **Venue** (conference/journal name, or "Preprint (arXiv)")
- **Announce type** (🆕 new / 🔀 cross / 🔄 replace / 🔁 replace-cross)
- **Authors**
- **Abstract** (full text)
- **Why Relevant** (which keywords matched, in title or abstract)
