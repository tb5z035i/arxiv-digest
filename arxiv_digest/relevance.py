"""
Keyword-based relevance scoring for arxiv papers.

Scores each paper against the configured research interest profiles
by matching keywords in the title and abstract.  Returns the score,
matched interest names, and a human-readable explanation of why the
paper is relevant.
"""

import logging
import re

from .config import (
    CATEGORY_BONUS,
    INTEREST_PROFILES,
    MAX_RESULTS,
    RELEVANCE_THRESHOLD,
    TITLE_MULTIPLIER,
)
from .rss_fetcher import ArxivPaper

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Lower-case and collapse whitespace for matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def score_paper(paper: ArxivPaper) -> tuple[float, list[str], str]:
    """
    Score a paper's relevance to the configured research interests.

    Returns:
        (score, matched_interest_names, relevance_reason)
    """
    title_norm = _normalize(paper.title)
    abstract_norm = _normalize(paper.abstract)
    full_text = title_norm + " " + abstract_norm

    total_score = 0.0
    matched_interests: list[str] = []
    reason_parts: list[str] = []

    for profile in INTEREST_PROFILES:
        profile_score = 0.0
        profile_hits: list[str] = []

        for keyword, weight in profile["keywords"]:
            kw_lower = keyword.lower()

            # Check title (boosted)
            title_count = _count_matches(title_norm, kw_lower)
            # Check abstract
            abstract_count = _count_matches(abstract_norm, kw_lower)

            if title_count > 0 or abstract_count > 0:
                hit_score = weight * (
                    title_count * TITLE_MULTIPLIER + abstract_count
                )
                profile_score += hit_score
                location = []
                if title_count:
                    location.append("title")
                if abstract_count:
                    location.append("abstract")
                profile_hits.append(f'"{keyword}" ({"+".join(location)})')

        if profile_hits:
            matched_interests.append(profile["name"])
            reason_parts.append(
                f'**{profile["name"]}**: matched {", ".join(profile_hits[:5])}'
                + (f" (+{len(profile_hits) - 5} more)" if len(profile_hits) > 5 else "")
            )

        total_score += profile_score

    # Category bonus
    for cat in paper.categories:
        bonus = CATEGORY_BONUS.get(cat, 0.0)
        if bonus > 0:
            total_score += bonus

    relevance_reason = "; ".join(reason_parts) if reason_parts else ""
    return total_score, matched_interests, relevance_reason


def _count_matches(text: str, keyword: str) -> int:
    """Count non-overlapping occurrences of keyword in text (word-boundary aware)."""
    # Use word boundaries for short keywords to avoid false matches
    if len(keyword) <= 4:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return len(re.findall(pattern, text))
    return text.count(keyword)


def filter_relevant(papers: list[ArxivPaper]) -> list[ArxivPaper]:
    """
    Score all papers and return those above the relevance threshold.

    Papers are sorted by relevance score (descending) and capped at MAX_RESULTS.
    Each returned paper has its relevance_score, matched_interests, and
    relevance_reason fields populated.
    """
    relevant = []

    for paper in papers:
        score, interests, reason = score_paper(paper)
        paper.relevance_score = score
        paper.matched_interests = interests
        paper.relevance_reason = reason

        if score >= RELEVANCE_THRESHOLD:
            relevant.append(paper)

    # Sort by score descending
    relevant.sort(key=lambda p: p.relevance_score, reverse=True)

    # Cap at max results
    if len(relevant) > MAX_RESULTS:
        logger.warning(
            "Capping results from %d to %d (MAX_RESULTS)",
            len(relevant),
            MAX_RESULTS,
        )
        relevant = relevant[:MAX_RESULTS]

    logger.info(
        "Relevance filter: %d / %d papers matched (threshold=%.1f)",
        len(relevant),
        len(papers),
        RELEVANCE_THRESHOLD,
    )
    return relevant
