"""
LLM-based extraction of structured account data from call transcripts.
Uses Ollama (local, zero-cost) for structured JSON extraction.
"""

import sys
import json
import argparse
import time
from pathlib import Path

import requests

from utils import (
    setup_logging, load_text, load_prompt, extract_json_from_text,
    save_json, OLLAMA_HOST, OLLAMA_MODEL
)

logger = setup_logging("extract")

# Maximum retries for Ollama API calls
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def call_ollama(prompt: str, system_prompt: str = "", model: str = None) -> str:
    """
    Call Ollama API with retry logic.

    Args:
        prompt: User prompt
        system_prompt: System instructions
        model: Model name (default from env)

    Returns:
        LLM response text
    """
    model = model or OLLAMA_MODEL
    url = f"{OLLAMA_HOST}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Low temp for consistent extraction
            "num_predict": 4096,
            "top_p": 0.9
        }
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Calling Ollama ({model}), attempt {attempt}/{MAX_RETRIES}")
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result["response"]
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {OLLAMA_HOST}. Is Ollama running?")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                raise
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama request timed out (attempt {attempt})")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                raise
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                raise


def extract_from_demo(transcript: str) -> dict:
    """
    Extract structured account memo from a demo call transcript.

    Uses the demo extraction prompt to produce a v1 Account Memo JSON.
    Only extracts explicitly stated information — never hallucinates.

    Args:
        transcript: Full demo call transcript text

    Returns:
        Account Memo JSON dict
    """
    system_prompt = load_prompt("demo_extraction.txt")
    user_prompt = f"""Here is the demo call transcript to extract information from:

---TRANSCRIPT START---
{transcript}
---TRANSCRIPT END---

Extract the structured account memo JSON based on the transcript above. 
Follow the extraction rules exactly. Only include information that is explicitly stated.
Return ONLY valid JSON, no other text."""

    logger.info("Extracting account memo from demo transcript...")
    response = call_ollama(user_prompt, system_prompt)

    try:
        memo = extract_json_from_text(response)
        logger.info(f"Extracted memo for: {memo.get('company_name', 'UNKNOWN')}")
        return memo
    except (ValueError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse extraction response: {e}")
        logger.debug(f"Raw response: {response[:500]}")
        raise


def extract_from_onboarding(transcript: str, v1_memo: dict) -> dict:
    """
    Extract delta/updates from an onboarding call transcript.

    Uses the onboarding extraction prompt to produce only the changes
    relative to the v1 memo.

    Args:
        transcript: Full onboarding call transcript text
        v1_memo: Existing v1 Account Memo JSON

    Returns:
        Delta dict containing only changed/new fields
    """
    system_prompt = load_prompt("onboarding_extraction.txt")
    user_prompt = f"""Here is the existing v1 account memo from the demo call:

---V1 MEMO---
{json.dumps(v1_memo, indent=2)}
---END V1 MEMO---

Here is the onboarding call transcript:

---TRANSCRIPT START---
{transcript}
---TRANSCRIPT END---

Extract ONLY the new or changed information from this onboarding transcript.
Compare against the v1 memo and return a delta JSON with only fields that are 
new, corrected, or refined. Do not repeat unchanged fields.
Return ONLY valid JSON, no other text."""

    logger.info("Extracting deltas from onboarding transcript...")
    response = call_ollama(user_prompt, system_prompt)

    try:
        delta = extract_json_from_text(response)
        logger.info(f"Extracted {len(delta)} delta fields from onboarding")
        return delta
    except (ValueError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse onboarding extraction: {e}")
        logger.debug(f"Raw response: {response[:500]}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Extract account data from transcript")
    parser.add_argument("transcript_path", type=str, help="Path to transcript file")
    parser.add_argument("--mode", "-m", choices=["demo", "onboarding"], default="demo",
                        help="Extraction mode")
    parser.add_argument("--v1-memo", type=str, help="Path to v1 memo (required for onboarding mode)")
    parser.add_argument("--output", "-o", type=str, help="Output JSON path")

    args = parser.parse_args()
    transcript_path = Path(args.transcript_path)

    if not transcript_path.exists():
        logger.error(f"Transcript not found: {transcript_path}")
        sys.exit(1)

    transcript = load_text(transcript_path)

    if args.mode == "demo":
        memo = extract_from_demo(transcript)
    else:
        if not args.v1_memo:
            logger.error("--v1-memo required for onboarding mode")
            sys.exit(1)
        from utils import load_json
        v1_memo = load_json(Path(args.v1_memo))
        memo = extract_from_onboarding(transcript, v1_memo)

    if args.output:
        save_json(memo, Path(args.output))
    else:
        print(json.dumps(memo, indent=2))


if __name__ == "__main__":
    main()
