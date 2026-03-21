#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Missing virtualenv at $ROOT/.venv" >&2
  exit 1
fi

source .venv/bin/activate

python src/main.py fetch

if [[ ! -f data/relevance.json ]]; then
  echo "Missing data/relevance.json" >&2
  echo "The agent must create relevance.json after judging fetched papers." >&2
  exit 2
fi

python src/main.py process --relevance data/relevance.json
