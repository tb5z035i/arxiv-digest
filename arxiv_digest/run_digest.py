#!/usr/bin/env python3
"""
Daily arxiv Research Paper Digest — Main Orchestrator

Runs the full pipeline:
  1. Fetch RSS feed for cs.RO, cs.CV, cs.AI, cs.LG
  2. Score relevance against research interest profiles
  3. Enrich matched papers via arxiv API (comment / journal_ref / doi)
  4. Detect venue and project page
  5. Generate markdown digest
  6. Add papers to Zotero (deduplicated) with PDF attachments

Usage:
    python -m arxiv_digest.run_digest          # full pipeline
    python -m arxiv_digest.run_digest --dry-run  # skip Zotero integration
    python -m arxiv_digest.run_digest --no-pdf   # skip PDF uploads
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone

from . import config
from .arxiv_enricher import enrich_papers
from .digest_generator import write_digest
from .relevance import filter_relevant
from .rss_fetcher import fetch_papers
from .venue_detector import detect_all
from .zotero_client import add_papers_to_zotero

logger = logging.getLogger("arxiv_digest")


def setup_logging(log_file: str | None = None) -> None:
    """Configure logging to both stdout and an optional file."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)


def run(dry_run: bool = False, no_pdf: bool = False) -> None:
    """Execute the full digest pipeline."""
    start = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = str(config.OUTPUT_DIR / f"run_{today}.log")
    setup_logging(log_file)

    logger.info("=" * 60)
    logger.info("arxiv Digest Pipeline — %s", today)
    logger.info("=" * 60)

    # --- Stage 1: Fetch RSS ---
    logger.info("Stage 1/6: Fetching RSS feed...")
    papers = fetch_papers()
    if not papers:
        logger.error("No papers fetched from RSS. Aborting.")
        return
    logger.info("Fetched %d papers from RSS", len(papers))

    # --- Stage 2: Relevance scoring ---
    logger.info("Stage 2/6: Scoring relevance...")
    relevant = filter_relevant(papers)
    if not relevant:
        logger.warning("No relevant papers found. Generating empty digest.")

    # --- Stage 3: Enrich via arxiv API ---
    if relevant:
        logger.info("Stage 3/6: Enriching %d papers via arxiv API...", len(relevant))
        enrich_papers(relevant)
    else:
        logger.info("Stage 3/6: Skipping enrichment (no relevant papers)")

    # --- Stage 4: Venue & project page detection ---
    if relevant:
        logger.info("Stage 4/6: Detecting venues and project pages...")
        detect_all(relevant)
    else:
        logger.info("Stage 4/6: Skipping detection (no relevant papers)")

    # --- Stage 5: Generate digest ---
    logger.info("Stage 5/6: Generating markdown digest...")
    digest_path = write_digest(relevant, today)
    logger.info("Digest written to %s", digest_path)

    # --- Stage 6: Zotero integration ---
    if dry_run:
        logger.info("Stage 6/6: Skipping Zotero (dry-run mode)")
        items_created, pdfs_uploaded = 0, 0
    elif not relevant:
        logger.info("Stage 6/6: Skipping Zotero (no relevant papers)")
        items_created, pdfs_uploaded = 0, 0
    else:
        logger.info("Stage 6/6: Adding papers to Zotero...")
        if no_pdf:
            # Temporarily disable PDF uploads by monkey-patching
            from . import zotero_client
            orig_upload = zotero_client.upload_pdfs
            zotero_client.upload_pdfs = lambda *a, **kw: 0
            items_created, pdfs_uploaded = add_papers_to_zotero(relevant)
            zotero_client.upload_pdfs = orig_upload
        else:
            items_created, pdfs_uploaded = add_papers_to_zotero(relevant)

    # --- Summary ---
    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1f seconds", elapsed)
    logger.info("  Papers fetched:    %d", len(papers))
    logger.info("  Papers matched:    %d", len(relevant))
    logger.info("  Zotero items:      %d created", items_created)
    logger.info("  PDFs uploaded:     %d", pdfs_uploaded)
    logger.info("  Digest:            %s", digest_path)
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily arxiv Research Paper Digest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without Zotero integration",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Create Zotero items but skip PDF uploads",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run, no_pdf=args.no_pdf)


if __name__ == "__main__":
    main()
