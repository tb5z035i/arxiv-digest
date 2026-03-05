"""Markdown digest writer for relevant arXiv papers."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import config


def write_digest(
    papers: list,
    output_path: Optional[str] = None,
) -> str:
    """Render *papers* as a structured markdown digest.

    Returns the path the digest was written to.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")

    if output_path is None:
        output_path = str(config.DIGESTS_DIR / f"{date_str}.md")

    lines = [
        f"# arXiv Digest — {date_str}",
        "",
        f"**{len(papers)} relevant paper(s) found.**",
        "",
    ]

    for i, paper in enumerate(papers, 1):
        lines.append("---")
        lines.append("")
        lines.append(f"### {i}. {paper['title']}")
        lines.append("")

        arxiv_id = paper.get("arxiv_id", "")
        arxiv_url = paper.get("arxiv_url", f"https://arxiv.org/abs/{arxiv_id}")
        lines.append(f"- **arXiv**: [{arxiv_id}]({arxiv_url})")

        pp = paper.get("project_page")
        if pp:
            lines.append(f"- **Project Page**: [{pp}]({pp})")

        venue = paper.get("venue")
        if venue:
            lines.append(f"- **Venue**: {venue}")
        else:
            lines.append("- **Venue**: arXiv preprint")

        atype = paper.get("announce_type", "new")
        lines.append(f"- **Announce Type**: {atype}")

        lines.append("")
        lines.append(f"**Abstract**: {paper.get('abstract', 'N/A')}")
        lines.append("")

        reason = paper.get("relevance_reason", "")
        theme = paper.get("relevance_theme", "")
        if reason:
            tag = f" [{theme}]" if theme else ""
            lines.append(f"**Why Relevant{tag}**: {reason}")
            lines.append("")

    content = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path
