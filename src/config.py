"""Project configuration and environment loading."""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DIGESTS_DIR = PROJECT_ROOT / "digests"
SECRET_DIR = PROJECT_ROOT / ".secret"

CATEGORIES = ["cs.RO"]
ZOTERO_COLLECTION_NAME = "arxiv-digest"

ARXIV_RSS_BASE = "https://rss.arxiv.org/atom"
ARXIV_API_BASE = "https://export.arxiv.org/api/query"


def _load_secret_env(filename: str):
    """Load environment variables from .secret/ filename."""
    env_file = SECRET_DIR / filename
    if not env_file.exists():
        return
    
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            os.environ.setdefault(key, value)


def _load_openclaw_config():
    """Load API keys from OpenClaw config file."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return
    
    try:
        with open(config_path, encoding="utf-8") as fh:
            config = json.load(fh)
        
        # Extract foxcode-claude provider config
        providers = config.get("models", {}).get("providers", {})
        foxcode = providers.get("foxcode-claude", {})
        
        if foxcode.get("apiKey"):
            os.environ.setdefault("FOXCODE_API_KEY", foxcode["apiKey"])
        if foxcode.get("baseUrl"):
            os.environ.setdefault("FOXCODE_BASE_URL", foxcode["baseUrl"])
            
    except (json.JSONDecodeError, OSError):
        pass  # Silently fail if config can't be read


def load_env():
    """Load credentials from .secret/ files and OpenClaw config."""
    # Load from OpenClaw config
    _load_openclaw_config()
    
    # Load from secret files
    _load_secret_env("anthropic.env")
    _load_secret_env("openai.env")
    _load_secret_env("zotero.env")
    
    # Ensure output dirs exist
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
