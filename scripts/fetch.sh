#!/bin/bash
# Fetch arXiv papers for cs.RO category
cd /Users/tianbeiwen/.openclaw/workspace/arxiv-digest
source .venv/bin/activate
python src/main.py fetch
