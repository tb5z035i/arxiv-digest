"""Markdown digest writer for relevant arXiv papers."""

import json
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


def _normalize_theme(theme: Optional[str]) -> str:
    if not theme:
        return ""
    t = str(theme).strip().lower()
    if t in {"a", "theme_a", "theme a"}:
        return "theme_a"
    if t in {"b", "theme_b", "theme b"}:
        return "theme_b"
    return t



def write_discord_components(
    papers: list,
    date_str: Optional[str] = None,
) -> list[dict]:
    """Generate Discord Components v2 payloads for the digest.

    Returns a list of component payloads, one per theme group.
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Group papers by normalized theme
    theme_a = [p for p in papers if _normalize_theme(p.get("relevance_theme")) == "theme_a"]
    theme_b = [p for p in papers if _normalize_theme(p.get("relevance_theme")) == "theme_b"]
    # Fallback: papers that don't match Theme A or B (e.g., "Needs Review")
    other = [p for p in papers if _normalize_theme(p.get("relevance_theme")) not in {"theme_a", "theme_b"}]

    messages = []

    # Theme A message
    if theme_a:
        blocks = [
            {
                "type": "text",
                "text": f"🔖 **arXiv Digest — {date_str}**\n**cs.RO — {len(papers)} relevant papers**",
            },
            {
                "type": "text",
                "text": f"**📋 Theme A — NL → Atomic Capability Planning / Execution ({len(theme_a)} papers)**",
            },
        ]
        for paper in theme_a:
            blocks.extend(_paper_to_blocks(paper))
        messages.append({"components": {"blocks": blocks, "reusable": False}})

    # Theme B message
    if theme_b:
        blocks = [
            {
                "type": "text",
                "text": f"**⚡ Theme B — Edge-Efficient Robot Learning Inference ({len(theme_b)} papers)**",
            },
        ]
        for paper in theme_b:
            blocks.extend(_paper_to_blocks(paper))
        messages.append({"components": {"blocks": blocks, "reusable": False}})

    # Other/Needs Review message
    if other:
        blocks = [
            {
                "type": "text",
                "text": f"**📝 Other / Needs Review ({len(other)} papers)**",
            },
        ]
        for paper in other:
            blocks.extend(_paper_to_blocks(paper))
        messages.append({"components": {"blocks": blocks, "reusable": False}})

    return messages


def _paper_to_blocks(paper: dict) -> list[dict]:
    """Convert a single paper to Discord component blocks."""
    arxiv_id = paper.get("arxiv_id", "")
    arxiv_url = paper.get("arxiv_url", f"https://arxiv.org/abs/{arxiv_id}")
    venue = paper.get("venue") or "arXiv preprint"
    pp = paper.get("project_page")
    reason = paper.get("relevance_reason", "")

    # Build nested content with unicode bullets and fullwidth spaces
    lines = [f"**•** {paper['title']}"]
    lines.append(f"　**•** [{arxiv_id}](<{arxiv_url}>) — {venue}")
    if pp:
        lines.append(f"　**•** 📎 <{pp}>")
    if reason:
        lines.append(f"　**•** {reason}")

    return [{"type": "text", "text": "\n".join(lines)}]
