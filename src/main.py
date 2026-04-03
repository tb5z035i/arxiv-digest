#!/usr/bin/env python3
"""arXiv daily digest pipeline.

Usage (from the project root):
    python src/main.py fetch
    python src/main.py process --relevance data/relevance.json [--dry-run]
"""

import sys
import json
import logging
import argparse
from pathlib import Path

# Ensure sibling modules are importable regardless of invocation method.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from arxiv_fetcher import fetch_papers  # noqa: E402
from venue_detector import detect_venue, detect_venue_from_html  # noqa: E402
from project_page_finder import find_project_page, fetch_project_page_html  # noqa: E402
from digest_writer import write_digest, write_discord_components  # noqa: E402
from zotero_client import ZoteroClient  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("arxiv-digest")


# ------------------------------------------------------------------
# fetch
# ------------------------------------------------------------------


def cmd_fetch(_args):
    """Fetch today's papers from arXiv RSS + API and write data/papers.json."""
    config.load_env()

    papers = fetch_papers(config.CATEGORIES)

    output = config.DATA_DIR / "papers.json"
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(papers, fh, indent=2, ensure_ascii=False)

    logger.info("Wrote %d papers to %s", len(papers), output)

    type_counts: dict = {}
    for p in papers:
        t = p.get("announce_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"Fetched {len(papers)} papers (new + cross) from arXiv")
    print(f"Categories: {', '.join(config.CATEGORIES)}")
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")
    print(f"Output: {output}")
    print(f"{'=' * 60}")


# ------------------------------------------------------------------
# judge (sequential evaluation)
# ------------------------------------------------------------------


def cmd_judge(args):
    """Judge papers for relevance using LLM (sequential, no subagents)."""
    config.load_env()

    papers_path = config.DATA_DIR / "papers.json"
    with open(papers_path, encoding="utf-8") as fh:
        papers = json.load(fh)

    logger.info("Judging %d papers sequentially", len(papers))

    # Import here to avoid circular dependencies
    from judge_relevance import judge_papers_sequential

    results = judge_papers_sequential(papers)

    output = config.DATA_DIR / "relevance.json"
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    relevant = [r for r in results if r.get("is_relevant")]
    logger.info("Found %d relevant papers", len(relevant))

    print(f"\n{'=' * 60}")
    print(f"Judged {len(papers)} papers")
    print(f"Relevant: {len(relevant)}")
    print(f"Output: {output}")
    print(f"{'=' * 60}")


# ------------------------------------------------------------------
# process
# ------------------------------------------------------------------


def cmd_process(args):
    """Enrich relevant papers, write digest, sync to Zotero."""
    config.load_env()

    papers_path = config.DATA_DIR / "papers.json"
    with open(papers_path, encoding="utf-8") as fh:
        all_papers = json.load(fh)

    with open(args.relevance, encoding="utf-8") as fh:
        relevance = json.load(fh)

    by_id = {p["arxiv_id"]: p for p in all_papers}

    relevant: list = []
    for r in relevance:
        if not r.get("is_relevant"):
            continue
        aid = r["arxiv_id"]
        paper = by_id.get(aid)
        if paper is None:
            logger.warning("Relevant paper %s not in papers.json — skipping", aid)
            continue
        paper["relevance_theme"] = r.get("theme", "")
        paper["relevance_reason"] = r.get("reason", "")
        relevant.append(paper)

    logger.info("%d relevant papers out of %d total", len(relevant), len(all_papers))

    _enrich_papers(relevant)

    digest_path = write_digest(relevant)
    logger.info("Digest written to %s", digest_path)

    if not args.dry_run:
        _sync_zotero(relevant)
    else:
        print("\n[DRY RUN] Skipping Zotero sync")

    print(f"\n{'=' * 60}")
    print(f"Processed {len(relevant)} relevant papers")
    print(f"Digest: {digest_path}")
    print(f"{'=' * 60}")


# ------------------------------------------------------------------
# enrichment helpers
# ------------------------------------------------------------------


def _enrich_papers(papers: list) -> None:
    """Mutate papers in-place with venue info and project page URLs."""
    for paper in papers:
        venue_info = detect_venue(
            journal_ref=paper.get("journal_ref"),
            comments=paper.get("comments"),
        )

        project_page = find_project_page(
            abstract=paper.get("abstract", ""),
            comments=paper.get("comments"),
        )
        paper["project_page"] = project_page

        if venue_info["venue_type"] == "preprint" and project_page:
            html = fetch_project_page_html(project_page)
            if html:
                html_venue = detect_venue_from_html(html)
                if html_venue and html_venue["venue_type"] != "preprint":
                    venue_info = html_venue

        paper["venue"] = venue_info.get("venue")
        paper["venue_type"] = venue_info["venue_type"]


# ------------------------------------------------------------------
# Zotero sync
# ------------------------------------------------------------------


def _sync_zotero(papers: list) -> None:
    try:
        creds = config.get_zotero_credentials()
    except EnvironmentError as exc:
        logger.error("Zotero credentials missing: %s", exc)
        return

    zot = ZoteroClient(
        api_key=creds["api_key"],
        user_id=creds["user_id"],
        collection_name=config.ZOTERO_COLLECTION_NAME,
    )

    existing = zot.get_existing_arxiv_ids()
    logger.info("%d papers already in Zotero collection", len(existing))

    added = skipped = failed = 0
    for paper in papers:
        aid = paper["arxiv_id"]
        if aid in existing:
            logger.info("Skipping duplicate: %s", aid)
            skipped += 1
            continue
        try:
            key = zot.add_paper(paper)
            zot.attach_pdf(key, paper["pdf_url"], aid)
            added += 1
            logger.info("Added: %s → %s", aid, key)
        except Exception:
            logger.error("Failed to add %s", aid, exc_info=True)
            failed += 1

    print(
        f"\nZotero: {added} added, {skipped} skipped (duplicate), {failed} failed"
    )


# ------------------------------------------------------------------
# discord
# ------------------------------------------------------------------


def cmd_discord(args):
    """Generate Discord Components v2 JSON for relevant papers."""
    config.load_env()

    papers_path = config.DATA_DIR / "papers.json"
    with open(papers_path, encoding="utf-8") as fh:
        all_papers = json.load(fh)

    with open(args.relevance, encoding="utf-8") as fh:
        relevance = json.load(fh)

    by_id = {p["arxiv_id"]: p for p in all_papers}

    relevant: list = []
    for r in relevance:
        if not r.get("is_relevant"):
            continue
        aid = r["arxiv_id"]
        paper = by_id.get(aid)
        if paper is None:
            logger.warning("Relevant paper %s not in papers.json — skipping", aid)
            continue
        paper["relevance_theme"] = r.get("theme", "")
        paper["relevance_reason"] = r.get("reason", "")
        relevant.append(paper)

    _enrich_papers(relevant)

    messages = write_discord_components(relevant)
    output = config.DATA_DIR / "discord_components.json"
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(messages, fh, indent=2, ensure_ascii=False)

    logger.info("Discord components written to %s", output)
    print(f"\n{'=' * 60}")
    print(f"Generated {len(messages)} Discord message(s)")
    print(f"Output: {output}")
    print(f"{'=' * 60}")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="arXiv daily digest pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("fetch", help="Fetch today's papers from arXiv")
    sub.add_parser("judge", help="Judge fetched papers for relevance")

    proc = sub.add_parser("process", help="Process relevant papers")
    proc.add_argument(
        "--relevance",
        required=True,
        help="Path to relevance.json produced by the agent",
    )
    proc.add_argument(
        "--dry-run",
        action="store_true",
        help="Write digest but skip Zotero sync",
    )

    disc = sub.add_parser("discord", help="Generate Discord Components v2 JSON")
    disc.add_argument(
        "--relevance",
        required=True,
        help="Path to relevance.json produced by the agent",
    )

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "judge":
        cmd_judge(args)
    elif args.command == "process":
        cmd_process(args)
    elif args.command == "discord":
        cmd_discord(args)


if __name__ == "__main__":
    main()
