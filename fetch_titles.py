import requests
import json
import time

papers = [
    ("2603.20233", "A"), ("2603.21523", "A"), ("2603.22003", "A"), 
    ("2603.22169", "A"), ("2603.21013", "A"), ("2603.22280", "A"),
    ("2603.20664", "B"), ("2603.20669", "B"), ("2603.20679", "B"), ("2603.20711", "B")
]

results = {"A": [], "B": []}

for arxiv_id, theme in papers:
    try:
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        resp = requests.get(url, timeout=30)
        
        # Better parsing - find entry title specifically
        xml = resp.text
        entry_start = xml.find('<entry>')
        entry_xml = xml[entry_start:]
        
        title_start = entry_xml.find('<title>') + 7
        title_end = entry_xml.find('</title>', title_start)
        title = entry_xml[title_start:title_end].strip().replace('\n', ' ')
        
        summary_start = entry_xml.find('<summary>') + 9
        summary_end = entry_xml.find('</summary>', summary_start)
        summary = entry_xml[summary_start:summary_end].strip().replace('\n', ' ')
        
        # Get authors from entry section only
        authors = []
        author_xml = entry_xml
        while '<name>' in author_xml:
            name_start = author_xml.find('<name>') + 6
            name_end = author_xml.find('</name>', name_start)
            if name_end == -1:
                break
            authors.append(author_xml[name_start:name_end].strip())
            author_xml = author_xml[name_end+7:]
        
        results[theme].append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors[:3],
            "summary": summary[:400] + "..." if len(summary) > 400 else summary
        })
        time.sleep(0.3)
    except Exception as e:
        print(f"Error: {arxiv_id} - {e}")

print(json.dumps(results, indent=2))
