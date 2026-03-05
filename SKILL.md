---
name: arxiv-digest
description: >
  Fetch daily arXiv announcements (cs.RO, cs.CV, cs.AI, cs.LG), filter by
  research relevance, generate a structured markdown digest, and sync matched
  papers to a Zotero collection with arXiv PDFs attached.
---

# arXiv Daily Digest

## Quick reference

| Item | Value |
|------|-------|
| **Categories** | `cs.RO`, `cs.CV`, `cs.AI`, `cs.LG` |
| **Announce types** | `new` and `cross` only (`replace` / `replace-cross` are ignored) |
| **Zotero collection** | personal library → `arxiv-digest` (auto-created if absent) |
| **Credentials** | `.secret/zotero.env` (`ZOTERO_API_KEY`, `ZOTERO_USER_ID`) |
| **Digest output** | `digests/YYYY-MM-DD.md` |
| **Intermediate data** | `data/papers.json`, `data/relevance.json` |

---

## Invocation protocol

This is a **three-step** skill. Execute the steps in order.

### Step 1 — Fetch papers

```bash
cd /Users/tianbeiwen/Develop/arxiv-digest
source .venv/bin/activate
python src/main.py fetch
```

Fetches the arXiv RSS Atom feed for the four categories, enriches each
paper with metadata from the arXiv Search API, filters to `new` and
`cross` announcements, and writes the result to `data/papers.json`.

### Step 2 — Judge relevance

Read `data/papers.json`. For **every** paper, decide whether it is
relevant to the research interests defined below. Write the verdicts to
`data/relevance.json` in this exact format:

```json
[
  {
    "arxiv_id": "2603.01234",
    "is_relevant": true,
    "theme": "theme_a",
    "reason": "One-sentence explanation of why this paper is relevant"
  },
  {
    "arxiv_id": "2603.01235",
    "is_relevant": false,
    "theme": null,
    "reason": ""
  }
]
```

> **Important**: the file must contain an entry for every paper in
> `data/papers.json`, including irrelevant ones (set `is_relevant: false`).
> When there are many papers, you may batch your work, but do not skip any.

#### Research interests

**Theme A — NL → Atomic Capability Planning / Execution**

Given atomic capabilities (simple or expert) and a natural-language
command, algorithms that schedule, plan, and execute the atomic actions
to achieve high accuracy and efficiency.

Includes: LLM-based planners / agents, hierarchical policies / skills,
tool-use / skill composition, task planning, task-and-motion planning,
verification and safety for action execution.

**Theme B — Edge-Efficient Robot Learning Inference**

Proposals enabling fast, in-time inference of robot learning algorithms
(planning or action policy) on edge platforms, via platform-based
optimisation or special network design.

Includes: acceleration / compilation / runtime optimisations,
quantisation / distillation, latency-aware architecture design,
efficient VLA / VLM policy inference.

#### Filtering guidelines

- Target **balanced precision and recall**.
- A paper must clearly address one of the two themes to be marked
  relevant. Tangentially related work (e.g. general LLM reasoning
  without robotic application, generic model compression without
  edge / robotics context) should be marked **irrelevant**.
- Judge based on **both title and abstract**.

### Step 3 — Process, digest, and sync

```bash
source .venv/bin/activate   # if not already active
python src/main.py process --relevance data/relevance.json
```

This command:

1. Loads `papers.json` and `relevance.json`.
2. Enriches each relevant paper with **venue** information (arXiv
   metadata and, when needed, project-page HTML) and **project page**
   URL (extracted from abstract / comments).
3. Writes a structured markdown digest to `digests/YYYY-MM-DD.md`.
4. Adds each paper to Zotero (deduplicated by arXiv ID), with the
   correct item type (`conferencePaper` / `journalArticle` / `preprint`)
   and the arXiv PDF attached.

Append `--dry-run` to skip the Zotero sync (useful for testing).

After this step, **present the contents of `digests/YYYY-MM-DD.md`** to
the user as the daily report.

---

## Scheduling notes

- The arXiv RSS feed updates **daily around midnight US Eastern Time**
  (~13:00 GMT+8 during EST, ~12:00 GMT+8 during EDT).
- **No updates on Saturday or Sunday.** Monday's feed contains Friday's
  submissions. This skill should not be invoked on weekends.
- Invoke this skill once daily, after the RSS feed has updated.

---

## Setup

A Python virtual environment is used to isolate dependencies.

```bash
cd /Users/tianbeiwen/Develop/arxiv-digest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -i https://mirrors.ustc.edu.cn/pypi/web/simple
```

If the venv already exists, just activate it before running commands:

```bash
source /Users/tianbeiwen/Develop/arxiv-digest/.venv/bin/activate
```

Ensure `.secret/zotero.env` contains:

```
ZOTERO_API_KEY=<your key>
ZOTERO_USER_ID=<your user id>
```

---

## Attribution

Thank you to arXiv for use of its open access interoperability.
