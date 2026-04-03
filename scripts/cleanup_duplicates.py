#!/usr/bin/env python3
"""Remove duplicate arXiv entries from Zotero collection."""

import sys
sys.path.insert(0, '/Users/tianbeiwen/.openclaw/workspace/arxiv-digest/src')

from zotero_client import ZoteroClient
import config

config.load_env()
creds = config.get_zotero_credentials()
zot = ZoteroClient(creds['api_key'], creds['user_id'], 'arxiv-digest')

print(f"Collection key: {zot.collection_key}")

# Get all items
items = zot.zot.everything(zot.zot.collection_items_top(zot.collection_key))
print(f"Total items: {len(items)}")

# Group by arXiv ID
arxiv_to_items = {}
for item in items:
    extra = item.get('data', {}).get('extra', '')
    # Match arXiv ID - flexible regex
    import re
    m = re.search(r'arXiv[:\s]*(\d{4}\.\d{4,})', extra, re.IGNORECASE)
    if m:
        arxiv_id = m.group(1)
        if arxiv_id not in arxiv_to_items:
            arxiv_to_items[arxiv_id] = []
        arxiv_to_items[arxiv_id].append(item)

# Find duplicates
duplicates = {k: v for k, v in arxiv_to_items.items() if len(v) > 1}
print(f"\nDuplicates found: {len(duplicates)}")

deleted = 0
for arxiv_id, items_list in duplicates.items():
    print(f"\n{arxiv_id}: {len(items_list)} copies")
    # Keep the first one, delete the rest
    for item in items_list[1:]:
        item_key = item['data']['key']
        print(f"  Deleting: {item_key}")
        try:
            zot.zot.delete_item(item)
            deleted += 1
        except Exception as e:
            print(f"    Error: {e}")

print(f"\nDeleted {deleted} duplicate items")
