"""Fetch daily arXiv announcements via RSS Atom feed, enriched with API metadata.

Two-stage pipeline:
  1. RSS feed  → paper IDs, titles, announce types  (new/cross/replace)
  2. Search API → clean abstracts, comments, journal_ref, DOI, PDF links
"""

import re
import time
import logging
from typing import Optional

import feedparser
import requests

import config

logger = logging.getLogger(__name__)

_ANNOUNCE_RE = re.compile(r"Announce Type:\s*(\S+)", re.IGNORECASE)
_ABSTRACT_RE = re.compile(r"Abstract:\s*(.*)", re.DOTALL)
_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")


def fetch_papers(
    categories: Optional[list] = None,
    include_types: Optional[set] = None,
) -> list:
    """Fetch today's papers from arXiv RSS and enrich via API.

    Returns a list of paper dicts ready for JSON serialisation.
    """
    if categories is None:
        categories = config.CATEGORIES
    if include_types is None:
        include_types = {"new", "cross"}

    papers = _fetch_rss(categories)

    papers = [p for p in papers if p["announce_type"] in include_types]
    logger.info("%d papers after type filter (%s)", len(papers), include_types)

    if papers:
        _enrich_via_api(papers)

    return papers


# ------------------------------------------------------------------
# RSS
# ------------------------------------------------------------------


def _fetch_rss(categories: list) -> list:
    cats = "+".join(categories)
    url = f"{config.ARXIV_RSS_BASE}/{cats}"
    logger.info("Fetching RSS: %s", url)

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)

    if feed.bozo and not feed.entries:
        raise RuntimeError(f"RSS parse error: {feed.bozo_exception}")

    seen: dict = {}
    for entry in feed.entries:
        paper = _parse_rss_entry(entry)
        if paper and paper["arxiv_id"] not in seen:
            seen[paper["arxiv_id"]] = paper

    logger.info("Parsed %d unique papers from RSS", len(seen))
    return list(seen.values())


def _parse_rss_entry(entry) -> Optional[dict]:
    try:
        raw_id = entry.get("id", "")
        arxiv_id = _extract_id(raw_id)
        if not arxiv_id:
            return None

        summary = entry.get("summary", "")
        announce_type = _extract_announce_type(entry, summary)
        abstract = _extract_abstract(summary)

        authors: list = []
        if hasattr(entry, "authors"):
            authors = [a.get("name", "") for a in entry.authors if a.get("name")]
        elif hasattr(entry, "author") and entry.author:
            authors = [a.strip() for a in entry.author.split(",") if a.strip()]

        categories = [
            t.get("term", "") for t in getattr(entry, "tags", []) if t.get("term")
        ]

        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        for link in entry.get("links", []):
            href = link.get("href", "")
            if link.get("rel") == "alternate" and href:
                arxiv_url = href
            if link.get("type") == "application/pdf" and href:
                pdf_url = href

        return {
            "arxiv_id": arxiv_id,
            "title": _clean(entry.get("title", "")),
            "abstract": abstract,
            "authors": authors,
            "categories": categories,
            "primary_category": categories[0] if categories else "",
            "announce_type": announce_type,
            "arxiv_url": arxiv_url,
            "pdf_url": pdf_url,
            "published": entry.get("published", ""),
            "updated": entry.get("updated", ""),
            "comments": None,
            "journal_ref": None,
            "doi": None,
        }
    except Exception:
        logger.debug("Failed to parse RSS entry", exc_info=True)
        return None


# ------------------------------------------------------------------
# API enrichment
# ------------------------------------------------------------------

_API_BATCH = 200
_API_DELAY = 3  # seconds between requests (arXiv ToS)


def _enrich_via_api(papers: list) -> None:
    """Mutate *papers* in-place with API metadata."""
    idx = {p["arxiv_id"]: p for p in papers}
    ids = list(idx.keys())

    for start in range(0, len(ids), _API_BATCH):
        batch = ids[start : start + _API_BATCH]
        id_list = ",".join(batch)
        url = f"{config.ARXIV_API_BASE}?id_list={id_list}&max_results={len(batch)}"
        logger.info(
            "API enrichment batch %d: %d papers",
            start // _API_BATCH + 1,
            len(batch),
        )

        try:
            resp = requests.get(url, timeout=90)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            for entry in feed.entries:
                aid = _extract_id(entry.get("id", ""))
                if aid and aid in idx:
                    p = idx[aid]
                    if entry.get("summary"):
                        p["abstract"] = _clean(entry.summary)
                    p["comments"] = getattr(entry, "arxiv_comment", None)
                    p["journal_ref"] = getattr(entry, "arxiv_journal_ref", None)
                    p["doi"] = getattr(entry, "arxiv_doi", None)
                    if hasattr(entry, "authors") and entry.authors:
                        p["authors"] = [
                            a.get("name", "") for a in entry.authors if a.get("name")
                        ]
                    pcat = getattr(entry, "arxiv_primary_category", None)
                    if pcat:
                        p["primary_category"] = pcat.get("term", p["primary_category"])
                    for link in entry.get("links", []):
                        if link.get("type") == "application/pdf":
                            p["pdf_url"] = link.get("href", p["pdf_url"])
        except Exception:
            logger.warning("API enrichment failed for batch", exc_info=True)

        if start + _API_BATCH < len(ids):
            time.sleep(_API_DELAY)


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _extract_id(raw: str) -> Optional[str]:
    m = _ARXIV_ID_RE.search(raw)
    return m.group(1) if m else None


def _extract_announce_type(entry, summary: str) -> str:
    atype = getattr(entry, "arxiv_announce_type", None)
    if atype:
        return atype.strip().lower()
    m = _ANNOUNCE_RE.search(summary)
    return m.group(1).strip().lower() if m else "new"


def _extract_abstract(summary: str) -> str:
    m = _ABSTRACT_RE.search(summary)
    return _clean(m.group(1)) if m else _clean(summary)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
