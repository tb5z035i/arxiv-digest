"""Project configuration and environment loading."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DIGESTS_DIR = PROJECT_ROOT / "digests"
SECRET_DIR = PROJECT_ROOT / ".secret"

CATEGORIES = ["cs.RO", "cs.CV", "cs.AI", "cs.LG"]
ZOTERO_COLLECTION_NAME = "arxiv-digest"

ARXIV_RSS_BASE = "https://rss.arxiv.org/atom"
ARXIV_API_BASE = "https://export.arxiv.org/api/query"


def load_env():
    """Load credentials from .secret/zotero.env and ensure output dirs exist."""
    env_file = SECRET_DIR / "zotero.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    DATA_DIR.mkdir(exist_ok=True)
    DIGESTS_DIR.mkdir(exist_ok=True)


def get_zotero_credentials() -> dict:
    """Return Zotero API credentials from environment."""
    api_key = os.environ.get("ZOTERO_API_KEY")
    user_id = os.environ.get("ZOTERO_USER_ID")
    if not api_key or not user_id:
        raise EnvironmentError(
            "ZOTERO_API_KEY and ZOTERO_USER_ID must be set. "
            "Place them in .secret/zotero.env"
        )
    return {"api_key": api_key, "user_id": user_id}
