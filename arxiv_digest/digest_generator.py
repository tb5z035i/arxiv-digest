"""
Generate a structured Markdown digest of relevant papers.

Groups papers by announce type (New → Cross → Replace → Replace-Cross),
and renders each paper with title, links, venue, abstract, and relevance info.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .rss_fetcher import ArxivPaper

logger = logging.getLogger(__name__)

# Display order and section headings for announce types
_SECTION_ORDER = [
    ("new", "🆕 New Submissions"),
    ("cross", "🔀 Cross-Listings"),
    ("replace", "🔄 Replacements"),
    ("replace-cross", "🔁 Replace-Cross"),
]


def _render_paper(paper: ArxivPaper, index: int) -> str:
    """Render a single paper as a Markdown block."""
    lines: list[str] = []
    lines.append(f"### {index}. {paper.title}")
    lines.append("")

    # arXiv link (always present)
    lines.append(f"- **arXiv**: [{paper.arxiv_id}]({paper.arxiv_url})")

    # Project page (optional)
    if paper.project_url:
        lines.append(f"- **Project Page**: [{paper.project_url}]({paper.project_url})")

    # Venue
    venue_display = paper.venue if paper.venue else "Preprint (arXiv)"
    lines.append(f"- **Venue**: {venue_display}")

    # Announce type
    lines.append(f"- **Announce Type**: {paper.announce_type}")

    # Authors
    if paper.authors:
        authors_str = ", ".join(paper.authors)
        lines.append(f"- **Authors**: {authors_str}")

    lines.append("")

    # Abstract
    lines.append(f"**Abstract**: {paper.abstract}")
    lines.append("")

    # Why relevant
    if paper.relevance_reason:
        lines.append(f"**Why Relevant**: {paper.relevance_reason}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def generate_digest(papers: list[ArxivPaper], date_str: str | None = None) -> str:
    """
    Generate a complete Markdown digest string for the given papers.

    Args:
        papers: List of relevant ArxivPaper objects (already scored and enriched).
        date_str: Optional date string (YYYY-MM-DD). Defaults to today (UTC).

    Returns:
        The full Markdown digest as a string.
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Group papers by announce type
    groups: dict[str, list[ArxivPaper]] = defaultdict(list)
    for paper in papers:
        groups[paper.announce_type].append(paper)

    # --- Header ---
    lines: list[str] = []
    lines.append(f"# 📄 Daily arxiv Research Digest — {date_str}")
    lines.append("")
    lines.append(f"**Total relevant papers**: {len(papers)}")
    lines.append("")

    # Category breakdown
    type_counts = {atype: len(groups.get(atype, [])) for atype, _ in _SECTION_ORDER}
    type_summary = " | ".join(
        f"{label.split(' ', 1)[1]}: {type_counts.get(atype, 0)}"
        for atype, label in _SECTION_ORDER
        if type_counts.get(atype, 0) > 0
    )
    if type_summary:
        lines.append(f"**Breakdown**: {type_summary}")
        lines.append("")

    # Interest match summary
    interest_counts: dict[str, int] = defaultdict(int)
    for paper in papers:
        for interest in paper.matched_interests:
            interest_counts[interest] += 1
    if interest_counts:
        lines.append("**Matched Interests**:")
        for interest, count in sorted(interest_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {interest}: {count} papers")
        lines.append("")

    lines.append("---")
    lines.append("")

    # --- Sections by announce type ---
    global_index = 1
    for atype, heading in _SECTION_ORDER:
        section_papers = groups.get(atype, [])
        if not section_papers:
            continue

        lines.append(f"## {heading} ({len(section_papers)})")
        lines.append("")

        for paper in section_papers:
            lines.append(_render_paper(paper, global_index))
            global_index += 1

    return "\n".join(lines)


def write_digest(papers: list[ArxivPaper], date_str: str | None = None) -> Path:
    """
    Generate the digest and write it to the output directory.

    Returns the path to the written file.
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    content = generate_digest(papers, date_str)
    output_path = config.OUTPUT_DIR / f"digest_{date_str}.md"
    output_path.write_text(content, encoding="utf-8")

    logger.info("Digest written to %s (%d papers, %d bytes)", output_path, len(papers), len(content))
    return output_path
