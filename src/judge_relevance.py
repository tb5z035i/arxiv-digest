#!/usr/bin/env python3
"""Judge paper relevance using LLM API.

Tries multiple providers in order:
1. ANTHROPIC_API_KEY env var (direct Anthropic API)
2. FOXCODE_API_KEY env var (foxcode-claude proxy)
3. OPENAI_API_KEY env var (OpenAI API)
4. Fallback: mark all papers as "needs manual review"
"""

import json
import logging
import http.client
import os
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

THEMES = """
Theme A: NL → Atomic Capability Planning / Execution
Theme B: Edge-Efficient Robot Learning Inference
"""

SYSTEM_PROMPT = f"""You are a research paper relevance judge. Evaluate if papers match these themes:

{THEMES}

Respond with JSON only:
{{"is_relevant": true/false, "theme": "A/B/Both/None", "reason": "brief explanation"}}"""


def _get_api_config() -> Optional[Dict]:
    """Get available API config from environment."""
    # Try Anthropic direct
    if os.getenv("ANTHROPIC_API_KEY"):
        return {
            "provider": "anthropic",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "base_url": os.getenv("ANTHROPIC_BASE_URL", "api.anthropic.com"),
            "model": "claude-3-5-sonnet-20241022"
        }
    
    # Try foxcode-claude proxy
    if os.getenv("FOXCODE_API_KEY"):
        return {
            "provider": "anthropic",
            "api_key": os.getenv("FOXCODE_API_KEY"),
            "base_url": "code.newcli.com/claude/ultra",
            "model": "claude-opus-4-6"
        }
    
    # Try OpenAI
    if os.getenv("OPENAI_API_KEY"):
        return {
            "provider": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": "api.openai.com",
            "model": "gpt-4o-mini"
        }
    
    return None


def _call_llm(prompt: str, config: Dict, timeout: int = 60) -> Optional[str]:
    """Call LLM API for completion."""
    provider = config["provider"]
    api_key = config["api_key"]
    base_url = config["base_url"]
    model = config["model"]
    
    try:
        if provider == "anthropic":
            conn = http.client.HTTPSConnection(base_url, timeout=timeout)
            
            payload = json.dumps({
                "model": model,
                "max_tokens": 500,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}]
            })
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            conn.request("POST", "/v1/messages", body=payload, headers=headers)
        else:  # openai
            conn = http.client.HTTPSConnection(base_url, timeout=timeout)
            
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.1
            })
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            conn.request("POST", "/v1/chat/completions", body=payload, headers=headers)
        
        response = conn.getresponse()
        
        if response.status != 200:
            logger.error(f"API error: {response.status} {response.reason}")
            return None
        
        data = json.loads(response.read().decode())
        
        if provider == "anthropic":
            return data.get("content", [{}])[0].get("text", "")
        else:
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return None
    finally:
        conn.close()


def _judge_single_paper(paper: dict, config: Optional[Dict] = None) -> dict:
    """Judge a single paper."""
    arxiv_id = paper["arxiv_id"]
    
    # Fallback if no API available
    if not config:
        return {
            "arxiv_id": arxiv_id,
            "is_relevant": True,  # Include all papers for manual review
            "theme": "Needs Review",
            "reason": "No API key configured - manual review needed"
        }
    
    prompt = f"""Paper to evaluate:
Title: {paper['title']}
Abstract: {paper['abstract']}

Respond with JSON only in this exact format:
{{"is_relevant": true/false, "theme": "A/B/Both/None", "reason": "brief explanation"}}"""

    response = _call_llm(prompt, config)
    
    if not response:
        return {
            "arxiv_id": arxiv_id,
            "is_relevant": True,
            "theme": "Needs Review",
            "reason": "API call failed - manual review needed"
        }
    
    try:
        # Extract JSON from response
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()
        
        result = json.loads(text)
        result["arxiv_id"] = arxiv_id
        return result
        
    except (json.JSONDecodeError, IndexError) as e:
        logger.error(f"Failed to parse result for {arxiv_id}: {e}")
        return {
            "arxiv_id": arxiv_id,
            "is_relevant": True,
            "theme": "Needs Review",
            "reason": f"Parse error - manual review needed"
        }


def judge_papers_sequential(papers: List[Dict]) -> List[Dict]:
    """Judge papers sequentially using available LLM API."""
    config = _get_api_config()
    results = []
    
    if not config:
        logger.warning("No LLM API key configured. Marking all papers for manual review.")
    
    for i, paper in enumerate(papers, 1):
        logger.info(f"Judging {i}/{len(papers)}: {paper['arxiv_id']}")
        
        result = _judge_single_paper(paper, config)
        results.append(result)
        
        # Small delay to avoid rate limits
        if config:
            time.sleep(0.3)
    
    return results
