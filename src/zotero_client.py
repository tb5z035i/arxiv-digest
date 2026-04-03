"""Zotero API client — create items, deduplicate, attach PDFs.

Uses the *pyzotero* library for robust handling of the Zotero Web API
including the multi-step file upload protocol.
"""

import os
import re
import logging
import tempfile

import requests
from pyzotero import zotero

logger = logging.getLogger(__name__)


class ZoteroClient:
    """Thin wrapper around pyzotero scoped to a single collection."""

    def __init__(self, api_key: str, user_id: str, collection_name: str = "automated"):
        self.zot = zotero.Zotero(user_id, "user", api_key)
        self.collection_key = self._resolve_collection(collection_name)

    # ------------------------------------------------------------------
    # collection helpers
    # ------------------------------------------------------------------

    def _resolve_collection(self, name: str) -> str:
        """Find collection by *name*; create it if missing."""
        for c in self.zot.collections():
            if c["data"]["name"].lower() == name.lower():
                logger.info(
                    "Using existing collection '%s' (%s)", name, c["data"]["key"]
                )
                return c["data"]["key"]

        logger.info("Collection '%s' not found — creating it", name)
        payload = [{"name": name}]
        resp = self.zot.create_collections(payload)
        key = _extract_key(resp)
        logger.info("Created collection '%s' (%s)", name, key)
        return key

    # ------------------------------------------------------------------
    # deduplication
    # ------------------------------------------------------------------

    def get_existing_arxiv_ids(self) -> set:
        """Return the set of arXiv IDs already present in the collection."""
        ids: set = set()
        try:
            items = self.zot.everything(
                self.zot.collection_items_top(self.collection_key, limit=100)
            )
        except Exception:
            logger.warning("Could not fetch collection items for dedup", exc_info=True)
            return ids

        for item in items:
            extra = item.get("data", {}).get("extra", "")
            # More flexible regex to match arXiv IDs
            m = re.search(r"arXiv[:\s]*(\d{4}\.\d{4,})", extra, re.IGNORECASE)
            if m:
                ids.add(m.group(1))
        return ids

    # ------------------------------------------------------------------
    # item creation
    # ------------------------------------------------------------------

    def add_paper(self, paper: dict) -> str:
        """Create a Zotero library item and return its key."""
        venue_type = paper.get("venue_type", "preprint")
        if venue_type == "journal":
            item_type = "journalArticle"
        elif venue_type == "conference":
            item_type = "conferencePaper"
        else:
            item_type = "preprint"

        creators = _build_creators(paper.get("authors", []))

        item: dict = {
            "itemType": item_type,
            "title": paper["title"],
            "creators": creators,
            "abstractNote": paper.get("abstract", ""),
            "url": paper.get("arxiv_url", f"https://arxiv.org/abs/{paper['arxiv_id']}"),
            "extra": f"arXiv: {paper['arxiv_id']}",
            "collections": [self.collection_key],
            "tags": [{"tag": "arxiv-digest", "type": 1}],
        }

        venue = paper.get("venue")
        if venue:
            if item_type == "journalArticle":
                item["publicationTitle"] = venue
            elif item_type == "conferencePaper":
                item["conferenceName"] = venue
                item["proceedingsTitle"] = venue

        if paper.get("doi"):
            item["DOI"] = paper["doi"]

        resp = self.zot.create_items([item])
        return _extract_key(resp)

    # ------------------------------------------------------------------
    # PDF attachment
    # ------------------------------------------------------------------

    def attach_pdf(self, item_key: str, pdf_url: str, arxiv_id: str) -> bool:
        """Download an arXiv PDF and attach it to *item_key*.

        Falls back to a linked-URL attachment when file upload fails.
        """
        if self._try_file_upload(item_key, pdf_url, arxiv_id):
            return True
        return self._linked_url_fallback(item_key, pdf_url, arxiv_id)

    def _try_file_upload(self, item_key: str, pdf_url: str, arxiv_id: str) -> bool:
        try:
            pdf = requests.get(pdf_url, timeout=120)
            pdf.raise_for_status()
        except Exception:
            logger.warning("PDF download failed: %s", pdf_url, exc_info=True)
            return False

        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix=f"{arxiv_id}_", delete=False
            ) as f:
                f.write(pdf.content)
                tmp = f.name
            self.zot.attachment_simple([tmp], item_key)
            return True
        except Exception:
            logger.warning("File upload failed for %s", arxiv_id, exc_info=True)
            return False
        finally:
            if tmp and os.path.exists(tmp):
                os.unlink(tmp)

    def _linked_url_fallback(
        self, item_key: str, pdf_url: str, arxiv_id: str
    ) -> bool:
        try:
            attachment = [
                {
                    "itemType": "attachment",
                    "parentItem": item_key,
                    "linkMode": "linked_url",
                    "title": f"{arxiv_id}.pdf",
                    "url": pdf_url,
                    "contentType": "application/pdf",
                    "tags": [],
                    "relations": {},
                }
            ]
            self.zot.create_items(attachment)
            return True
        except Exception:
            logger.error(
                "Linked-URL fallback also failed for %s", arxiv_id, exc_info=True
            )
            return False


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _extract_key(resp) -> str:
    """Pull the first item key from a Zotero write response."""
    if isinstance(resp, dict):
        success = resp.get("success", {})
        if success:
            return str(list(success.values())[0])
        successful = resp.get("successful", {})
        if successful:
            first = list(successful.values())[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("key") or first.get("data", {}).get("key", "")
    raise RuntimeError(f"Unexpected Zotero write response: {resp}")


def _build_creators(authors: list) -> list:
    creators = []
    for name in authors:
        parts = name.strip().rsplit(" ", 1)
        if len(parts) == 2:
            creators.append(
                {"creatorType": "author", "firstName": parts[0], "lastName": parts[1]}
            )
        elif parts:
            creators.append({"creatorType": "author", "name": parts[0]})
    return creators
