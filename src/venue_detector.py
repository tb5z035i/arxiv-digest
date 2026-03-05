"""Venue detection from arXiv metadata and project page HTML."""

import re
from typing import Optional

CONFERENCES = {
    "ICRA": "IEEE International Conference on Robotics and Automation (ICRA)",
    "IROS": "IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)",
    "RSS": "Robotics: Science and Systems (RSS)",
    "CoRL": "Conference on Robot Learning (CoRL)",
    "Humanoids": "IEEE-RAS International Conference on Humanoid Robots",
    "CASE": "IEEE International Conference on Automation Science and Engineering (CASE)",
    "NeurIPS": "Conference on Neural Information Processing Systems (NeurIPS)",
    "ICML": "International Conference on Machine Learning (ICML)",
    "ICLR": "International Conference on Learning Representations (ICLR)",
    "AAAI": "AAAI Conference on Artificial Intelligence (AAAI)",
    "IJCAI": "International Joint Conference on Artificial Intelligence (IJCAI)",
    "AISTATS": "International Conference on Artificial Intelligence and Statistics (AISTATS)",
    "UAI": "Conference on Uncertainty in Artificial Intelligence (UAI)",
    "COLM": "Conference on Language Modeling (COLM)",
    "CVPR": "IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
    "ICCV": "IEEE International Conference on Computer Vision (ICCV)",
    "ECCV": "European Conference on Computer Vision (ECCV)",
    "WACV": "IEEE Winter Conference on Applications of Computer Vision (WACV)",
    "BMVC": "British Machine Vision Conference (BMVC)",
    "ACCV": "Asian Conference on Computer Vision (ACCV)",
    "3DV": "International Conference on 3D Vision (3DV)",
    "ACL": "Annual Meeting of the Association for Computational Linguistics (ACL)",
    "EMNLP": "Conference on Empirical Methods in Natural Language Processing (EMNLP)",
    "NAACL": "North American Chapter of the ACL (NAACL)",
    "SIGGRAPH": "ACM SIGGRAPH",
    "CHI": "ACM Conference on Human Factors in Computing Systems (CHI)",
    "COLT": "Conference on Learning Theory (COLT)",
    "KDD": "ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD)",
}

JOURNALS = {
    "T-RO": "IEEE Transactions on Robotics",
    "TRO": "IEEE Transactions on Robotics",
    "RA-L": "IEEE Robotics and Automation Letters",
    "RAL": "IEEE Robotics and Automation Letters",
    "IJRR": "The International Journal of Robotics Research",
    "RAS": "Robotics and Autonomous Systems",
    "T-ASE": "IEEE Transactions on Automation Science and Engineering",
    "TASE": "IEEE Transactions on Automation Science and Engineering",
    "T-PAMI": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
    "TPAMI": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
    "IJCV": "International Journal of Computer Vision",
    "JMLR": "Journal of Machine Learning Research",
    "TMLR": "Transactions on Machine Learning Research",
}

# Patterns that indicate an accepted venue (in comments field)
_ACCEPTED_RE = re.compile(
    r"(?:accepted|published|to appear|appearing)\s+(?:at|to|by|in|as)\s+([^.;\n]+)",
    re.IGNORECASE,
)


def detect_venue(
    journal_ref: Optional[str] = None,
    comments: Optional[str] = None,
) -> dict:
    """Detect venue from arXiv metadata fields.

    Returns {"venue": str|None, "venue_type": "conference"|"journal"|"preprint"}.
    """
    if journal_ref:
        result = _match_venue(journal_ref)
        if result:
            return result

    if comments:
        m = _ACCEPTED_RE.search(comments)
        if m:
            venue_text = m.group(1).strip()
            result = _match_venue(venue_text)
            if result:
                return result
            return {"venue": venue_text, "venue_type": _guess_type(venue_text)}

        result = _match_venue(comments)
        if result:
            return result

    return {"venue": None, "venue_type": "preprint"}


def detect_venue_from_html(html: str) -> Optional[dict]:
    """Best-effort venue detection from project page HTML."""
    text = re.sub(r"<[^>]+>", " ", html)

    m = _ACCEPTED_RE.search(text)
    if m:
        venue_text = m.group(1).strip()
        result = _match_venue(venue_text)
        if result:
            return result

    return _match_venue(text)


def _match_venue(text: str) -> Optional[dict]:
    for abbrev, full_name in CONFERENCES.items():
        if re.search(r"\b" + re.escape(abbrev) + r"\b", text):
            return {"venue": full_name, "venue_type": "conference"}

    for abbrev, full_name in JOURNALS.items():
        if re.search(r"\b" + re.escape(abbrev) + r"\b", text):
            return {"venue": full_name, "venue_type": "journal"}

    generic_journal = [
        r"IEEE Transactions on [A-Z][a-zA-Z\s]+",
        r"IEEE Robotics and Automation Letters",
        r"The International Journal of Robotics Research",
        r"International Journal of Computer Vision",
        r"Journal of Machine Learning Research",
        r"Nature\s+[A-Z][a-zA-Z]+",
        r"Science\s+[A-Z][a-zA-Z]+",
    ]
    for pat in generic_journal:
        m = re.search(pat, text)
        if m:
            return {"venue": m.group(0), "venue_type": "journal"}

    return None


def _guess_type(venue_text: str) -> str:
    low = venue_text.lower()
    if any(kw in low for kw in ("journal", "transaction", "letter", "magazine")):
        return "journal"
    return "conference"
