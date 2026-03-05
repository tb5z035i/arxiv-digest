"""Project page URL discovery from paper abstract / comments."""

import re
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_EXCLUDE_DOMAINS = {
    "arxiv.org",
    "ar5iv.org",
    "doi.org",
    "scholar.google.com",
    "semanticscholar.org",
    "researchgate.net",
    "academia.edu",
    "twitter.com",
    "x.com",
    "youtube.com",
    "linkedin.com",
    "facebook.com",
    "creativecommons.org",
    "openreview.net",
}

_PROJECT_INDICATORS = [
    "github.io",
    "gitlab.io",
    "sites.google.com",
    "google.com/view",
    "/project",
    "/paper",
    "/research",
]


def find_project_page(
    abstract: str,
    comments: Optional[str] = None,
) -> Optional[str]:
    """Extract project / code page URL from paper text.

    Returns the best candidate URL or None.
    """
    text = abstract
    if comments:
        text += "\n" + comments

    urls = _extract_urls(text)
    urls = [u for u in urls if not _is_excluded(u)]

    for url in urls:
        if _is_project_page(url):
            return url

    return urls[0] if urls else None


def fetch_project_page_html(url: str, timeout: int = 8) -> Optional[str]:
    """Fetch HTML of a project page. Returns None on any failure."""
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "ArXiv-Digest/1.0"},
            allow_redirects=True,
        )
        if resp.status_code == 200 and "text/html" in resp.headers.get(
            "content-type", ""
        ):
            return resp.text
    except Exception as exc:
        logger.debug("Could not fetch project page %s: %s", url, exc)
    return None


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _extract_urls(text: str) -> list:
    raw = re.findall(r"https?://[^\s<>\")\]]+", text)
    cleaned = []
    for url in raw:
        url = re.sub(r"[.,;:!?]+$", "", url)
        while url.endswith(")") and url.count("(") < url.count(")"):
            url = url[:-1]
        while url.endswith("}") and url.count("{") < url.count("}"):
            url = url[:-1]
        cleaned.append(url)
    return cleaned


def _is_excluded(url: str) -> bool:
    low = url.lower()
    return any(d in low for d in _EXCLUDE_DOMAINS)


def _is_project_page(url: str) -> bool:
    low = url.lower()
    return any(ind in low for ind in _PROJECT_INDICATORS)
