import requests
import json
import time
import sys

papers = [
    # Theme A
    "2603.20233", "2603.21523", "2603.22003", "2603.22169", "2603.21013", "2603.22280",
    # Theme B
    "2603.20664", "2603.20669", "2603.20679", "2603.20711"
]

results = []
for arxiv_id in papers:
    try:
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        # Parse XML manually
        xml = resp.text
        
        # Extract title
        title_start = xml.find('<title>') + 7
        title_end = xml.find('</title>', title_start)
        title = xml[title_start:title_end].strip()
        if title.startswith('arXiv:'):
            # Find next title tag
            title_start = xml.find('<title>', title_end) + 7
            title_end = xml.find('</title>', title_start)
            title = xml[title_start:title_end].strip()
        
        # Extract summary
        summary_start = xml.find('<summary>') + 9
        summary_end = xml.find('</summary>', summary_start)
        summary = xml[summary_start:summary_end].strip()
        
        # Extract authors
        authors = []
        author_idx = 0
        while True:
            name_start = xml.find('<name>', author_idx)
            if name_start == -1:
                break
            name_start += 6
            name_end = xml.find('</name>', name_start)
            authors.append(xml[name_start:name_end].strip())
            author_idx = name_end + 7
        
        results.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors[:3],  # First 3 authors
            "summary": summary[:500] + "..." if len(summary) > 500 else summary
        })
        time.sleep(0.5)
    except Exception as e:
        print(f"Error fetching {arxiv_id}: {e}", file=sys.stderr)
        results.append({"arxiv_id": arxiv_id, "error": str(e)})

print(json.dumps(results, indent=2))
