"""
Zotero API client for adding papers and uploading PDFs.

Handles:
- Deduplication: checks local state + Zotero tags to avoid adding duplicates
- Item creation: creates items with correct types (preprint / conferencePaper / journalArticle)
- PDF upload: downloads arxiv PDFs and uploads them to Zotero file storage
"""

import hashlib
import json
import logging
import os
import re
import tempfile
import time
import uuid
from pathlib import Path

import requests

from . import config
from .rss_fetcher import ArxivPaper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _zotero_headers(write_token: str | None = None) -> dict:
    """Return standard Zotero API headers."""
    h = {
        "Zotero-API-Key": config.ZOTERO_API_KEY,
        "Zotero-API-Version": "3",
        "Content-Type": "application/json",
    }
    if write_token:
        h["Zotero-Write-Token"] = write_token
    return h


def _parse_author_name(name: str) -> dict:
    """
    Parse a full name into firstName / lastName for Zotero.

    Handles: "First Last", "First Middle Last", "Last, First"
    """
    name = name.strip()
    if not name:
        return {"creatorType": "author", "firstName": "", "lastName": ""}

    # Handle "Last, First" format
    if "," in name:
        parts = name.split(",", 1)
        return {
            "creatorType": "author",
            "firstName": parts[1].strip(),
            "lastName": parts[0].strip(),
        }

    # Handle LaTeX accent commands (common in arxiv): \'{e} → e, etc.
    name = re.sub(r"\\['\"`^~]?\{?(\w)\}?", r"\1", name)
    name = re.sub(r"\{([^}]*)\}", r"\1", name)

    parts = name.split()
    if len(parts) == 1:
        return {"creatorType": "author", "firstName": "", "lastName": parts[0]}
    return {
        "creatorType": "author",
        "firstName": " ".join(parts[:-1]),
        "lastName": parts[-1],
    }


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def load_processed_ids() -> dict[str, str]:
    """Load the mapping of arxiv_id → zotero_key from local state."""
    path = config.PROCESSED_IDS_FILE
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load processed IDs: %s", e)
    return {}


def save_processed_ids(mapping: dict[str, str]) -> None:
    """Save the mapping of arxiv_id → zotero_key to local state."""
    config.STATE_DIR.mkdir(exist_ok=True)
    config.PROCESSED_IDS_FILE.write_text(
        json.dumps(mapping, indent=2),
        encoding="utf-8",
    )


def sync_processed_ids_from_zotero(local_ids: dict[str, str]) -> dict[str, str]:
    """
    Query Zotero for all items tagged with our tag and merge with local state.

    This handles the case where local state was lost.
    """
    url = f"{config.ZOTERO_API_BASE}/collections/{config.ZOTERO_COLLECTION_KEY}/items"
    params = {
        "tag": config.ZOTERO_TAG,
        "limit": 100,
        "start": 0,
        "itemType": "-attachment",  # exclude attachments
    }
    merged = dict(local_ids)

    while True:
        try:
            resp = requests.get(url, params=params, headers=_zotero_headers(), timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Zotero sync failed: %s", e)
            break

        items = resp.json()
        if not items:
            break

        for item in items:
            data = item.get("data", {})
            extra = data.get("extra", "")
            # Extract arxiv ID from extra field: "arXiv: 2603.03380"
            m = re.search(r"arXiv:\s*([\d.]+)", extra)
            if m:
                aid = m.group(1)
                if aid not in merged:
                    merged[aid] = data.get("key", "")

        # Pagination
        total = int(resp.headers.get("Total-Results", 0))
        params["start"] += len(items)
        if params["start"] >= total:
            break

    logger.info("Synced processed IDs: %d total (%d from Zotero)", len(merged), len(merged) - len(local_ids))
    return merged


# ---------------------------------------------------------------------------
# Item Creation
# ---------------------------------------------------------------------------


def _build_item_data(paper: ArxivPaper) -> dict:
    """Build the Zotero item JSON for a paper."""
    creators = [_parse_author_name(name) for name in paper.authors]
    if not creators:
        creators = [{"creatorType": "author", "firstName": "", "lastName": "Unknown"}]

    tags = [{"tag": config.ZOTERO_TAG, "type": 1}]
    collections = [config.ZOTERO_COLLECTION_KEY]
    extra = f"arXiv: {paper.arxiv_id}"

    # Determine item type based on venue_type
    if paper.venue_type == "conference":
        item = {
            "itemType": "conferencePaper",
            "title": paper.title,
            "creators": creators,
            "abstractNote": paper.abstract,
            "url": paper.arxiv_url,
            "extra": extra,
            "tags": tags,
            "collections": collections,
            "conferenceName": paper.venue or "",
            "proceedingsTitle": paper.venue or "",
            "date": paper.pub_date,
        }
    elif paper.venue_type == "journal":
        item = {
            "itemType": "journalArticle",
            "title": paper.title,
            "creators": creators,
            "abstractNote": paper.abstract,
            "url": paper.arxiv_url,
            "extra": extra,
            "tags": tags,
            "collections": collections,
            "publicationTitle": paper.venue or "",
            "date": paper.pub_date,
        }
    else:
        item = {
            "itemType": "preprint",
            "title": paper.title,
            "creators": creators,
            "abstractNote": paper.abstract,
            "url": paper.arxiv_url,
            "extra": extra,
            "tags": tags,
            "collections": collections,
            "repository": "arXiv",
            "archiveID": paper.arxiv_id,
            "date": paper.pub_date,
        }

    # Add DOI if available
    if paper.doi:
        item["DOI"] = paper.doi

    return item


def create_items(papers: list[ArxivPaper]) -> dict[str, str]:
    """
    Create Zotero items for a list of papers.

    Returns a mapping of arxiv_id → zotero_item_key for created items.
    Papers are batched (up to 50 per request as required by Zotero API).
    """
    if not papers:
        return {}

    url = f"{config.ZOTERO_API_BASE}/items"
    created: dict[str, str] = {}
    batch_size = 50

    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        items_data = [_build_item_data(p) for p in batch]

        try:
            resp = requests.post(
                url,
                json=items_data,
                headers=_zotero_headers(write_token=str(uuid.uuid4())),
                timeout=60,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("Zotero item creation failed for batch %d: %s", i, e)
            if hasattr(e, "response") and e.response is not None:
                logger.error("Response: %s", e.response.text[:500])
            continue

        result = resp.json()

        # The response contains "success", "unchanged", "failed" dicts
        # "success" maps index → item key
        success = result.get("success", {})
        failed = result.get("failed", {})

        for idx_str, item_key in success.items():
            idx = int(idx_str)
            if idx < len(batch):
                paper = batch[idx]
                created[paper.arxiv_id] = item_key
                logger.debug("Created Zotero item %s for %s", item_key, paper.arxiv_id)

        if failed:
            for idx_str, error in failed.items():
                idx = int(idx_str)
                title = batch[idx].title[:50] if idx < len(batch) else "?"
                logger.error("Failed to create item '%s': %s", title, error)

        logger.info(
            "Zotero batch %d–%d: %d created, %d failed",
            i + 1,
            min(i + batch_size, len(papers)),
            len(success),
            len(failed),
        )

        # Small delay between batches
        if i + batch_size < len(papers):
            time.sleep(1)

    return created


# ---------------------------------------------------------------------------
# PDF Upload
# ---------------------------------------------------------------------------


def _download_pdf(arxiv_id: str, dest: Path) -> bool:
    """Download a PDF from arxiv to a local path."""
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    try:
        resp = requests.get(url, timeout=60, stream=True, headers={"User-Agent": "arxiv-digest/1.0"})
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        logger.error("PDF download failed for %s: %s", arxiv_id, e)
        return False


def _upload_pdf_to_zotero(parent_key: str, arxiv_id: str, pdf_path: Path) -> bool:
    """
    Upload a PDF file to Zotero as a child attachment of the given parent item.

    Follows the Zotero file upload protocol:
    1. Create child attachment item
    2. Get upload authorization
    3. Upload file to S3
    4. Register upload
    """
    pdf_bytes = pdf_path.read_bytes()
    md5 = hashlib.md5(pdf_bytes).hexdigest()
    filesize = len(pdf_bytes)
    mtime = int(time.time() * 1000)
    filename = f"{arxiv_id}.pdf"

    # Step 1: Create child attachment item
    attachment_data = [
        {
            "itemType": "attachment",
            "parentItem": parent_key,
            "linkMode": "imported_url",
            "title": f"arXiv PDF ({arxiv_id})",
            "url": f"https://arxiv.org/pdf/{arxiv_id}",
            "contentType": "application/pdf",
            "filename": filename,
            "tags": [],
            "relations": {},
            "md5": None,
            "mtime": None,
        }
    ]

    try:
        resp = requests.post(
            f"{config.ZOTERO_API_BASE}/items",
            json=attachment_data,
            headers=_zotero_headers(write_token=str(uuid.uuid4())),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to create attachment item for %s: %s", arxiv_id, e)
        return False

    result = resp.json()
    success = result.get("success", {})
    if "0" not in success:
        logger.error("Attachment creation returned no success for %s: %s", arxiv_id, result.get("failed", {}))
        return False

    attachment_key = success["0"]

    # Step 2: Get upload authorization
    auth_url = f"{config.ZOTERO_API_BASE}/items/{attachment_key}/file"
    auth_headers = {
        "Zotero-API-Key": config.ZOTERO_API_KEY,
        "Zotero-API-Version": "3",
        "Content-Type": "application/x-www-form-urlencoded",
        "If-None-Match": "*",
    }
    auth_body = f"md5={md5}&filename={filename}&filesize={filesize}&mtime={mtime}"

    try:
        resp = requests.post(auth_url, data=auth_body, headers=auth_headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Upload authorization failed for %s: %s", arxiv_id, e)
        return False

    auth_result = resp.json()

    # Check if file already exists
    if auth_result.get("exists") == 1:
        logger.info("PDF already exists in Zotero for %s", arxiv_id)
        return True

    # Step 3: Upload file to S3
    upload_url = auth_result.get("url")
    content_type = auth_result.get("contentType")
    prefix = auth_result.get("prefix", "").encode("utf-8")
    suffix = auth_result.get("suffix", "").encode("utf-8")
    upload_key = auth_result.get("uploadKey")

    if not upload_url or not upload_key:
        logger.error("Invalid upload authorization response for %s: %s", arxiv_id, auth_result)
        return False

    upload_body = prefix + pdf_bytes + suffix

    try:
        resp = requests.post(
            upload_url,
            data=upload_body,
            headers={"Content-Type": content_type},
            timeout=120,
        )
        if resp.status_code not in (200, 201):
            logger.error("S3 upload failed for %s: %d %s", arxiv_id, resp.status_code, resp.text[:200])
            return False
    except requests.RequestException as e:
        logger.error("S3 upload request failed for %s: %s", arxiv_id, e)
        return False

    # Step 4: Register upload
    register_body = f"upload={upload_key}"
    try:
        resp = requests.post(
            auth_url,
            data=register_body,
            headers=auth_headers,
            timeout=30,
        )
        if resp.status_code != 204:
            logger.error("Upload registration failed for %s: %d %s", arxiv_id, resp.status_code, resp.text[:200])
            return False
    except requests.RequestException as e:
        logger.error("Upload registration request failed for %s: %s", arxiv_id, e)
        return False

    logger.info("PDF uploaded successfully for %s (%.1f KB)", arxiv_id, filesize / 1024)
    return True


def upload_pdfs(
    papers: list[ArxivPaper],
    item_keys: dict[str, str],
    delay: float = 2.0,
) -> int:
    """
    Download and upload PDFs for created Zotero items.

    Args:
        papers: List of papers that were added to Zotero.
        item_keys: Mapping of arxiv_id → zotero_item_key.
        delay: Seconds to wait between uploads (rate limiting).

    Returns:
        Number of PDFs successfully uploaded.
    """
    uploaded = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        for paper in papers:
            parent_key = item_keys.get(paper.arxiv_id)
            if not parent_key:
                continue

            pdf_path = Path(tmpdir) / f"{paper.arxiv_id}.pdf"
            logger.info("Downloading PDF for %s...", paper.arxiv_id)

            if not _download_pdf(paper.arxiv_id, pdf_path):
                continue

            if _upload_pdf_to_zotero(parent_key, paper.arxiv_id, pdf_path):
                uploaded += 1

            # Rate limit
            time.sleep(delay)

    logger.info("PDF upload complete: %d / %d uploaded", uploaded, len(item_keys))
    return uploaded


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------


def add_papers_to_zotero(papers: list[ArxivPaper]) -> tuple[int, int]:
    """
    Add relevant papers to Zotero with deduplication and PDF uploads.

    Returns:
        (items_created, pdfs_uploaded)
    """
    if not papers:
        return 0, 0

    # 1. Load and sync processed IDs
    processed = load_processed_ids()
    processed = sync_processed_ids_from_zotero(processed)

    # 2. Filter out already-processed papers
    new_papers = [p for p in papers if p.arxiv_id not in processed]
    if not new_papers:
        logger.info("All %d papers already in Zotero — nothing to add", len(papers))
        save_processed_ids(processed)
        return 0, 0

    logger.info(
        "Adding %d new papers to Zotero (%d already processed)",
        len(new_papers),
        len(papers) - len(new_papers),
    )

    # 3. Create items
    created_keys = create_items(new_papers)

    # 4. Update processed IDs
    processed.update(created_keys)
    save_processed_ids(processed)

    # 5. Upload PDFs
    papers_with_keys = [p for p in new_papers if p.arxiv_id in created_keys]
    pdfs_uploaded = upload_pdfs(papers_with_keys, created_keys)

    return len(created_keys), pdfs_uploaded
