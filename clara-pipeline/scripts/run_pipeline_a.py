"""
Pipeline A: Demo Call → Preliminary Agent (v1)
Processes a demo call transcript and generates v1 account memo + agent spec.
"""

import sys
import argparse
from pathlib import Path

from utils import (
    setup_logging, generate_account_id, ensure_account_dirs,
    save_json, save_text, load_text, get_timestamp,
    RECORDINGS_DIR, OUTPUT_DIR
)
from transcribe import transcribe_audio
from extract import extract_from_demo
from generate_agent import generate_agent_spec
from validate import validate_memo, validate_agent_spec

logger = setup_logging("pipeline_a")


def run_pipeline_a(
    input_path: Path,
    company_name_hint: str = None,
    skip_transcription: bool = False
) -> dict:
    """
    Run Pipeline A: Demo Call → v1 outputs.

    Args:
        input_path: Path to audio file or transcript .txt
        company_name_hint: Optional hint for company name (used if extraction fails)
        skip_transcription: If True, treat input as transcript directly

    Returns:
        dict with account_id, v1_dir, memo, agent_spec paths
    """
    logger.info(f"=" * 60)
    logger.info(f"PIPELINE A: Starting for {input_path.name}")
    logger.info(f"=" * 60)

    # Step 1: Get transcript
    if input_path.suffix == ".txt" or skip_transcription:
        logger.info("Step 1: Using provided transcript")
        transcript = load_text(input_path)
    else:
        logger.info("Step 1: Transcribing audio with Whisper...")
        transcript = transcribe_audio(input_path)

    # Step 2: Extract account memo from transcript
    logger.info("Step 2: Extracting account memo from demo transcript...")
    memo = extract_from_demo(transcript)

    # Ensure company_name exists
    if not memo.get("company_name") and company_name_hint:
        memo["company_name"] = company_name_hint
        logger.warning(f"Company name not extracted, using hint: {company_name_hint}")

    if not memo.get("company_name"):
        memo["company_name"] = input_path.stem.replace("_", " ").replace("-", " ").title()
        logger.warning(f"Company name not extracted, derived from filename: {memo['company_name']}")

    # Generate account_id
    account_id = generate_account_id(memo["company_name"])
    memo["account_id"] = account_id
    memo["version"] = "v1"
    memo["created_at"] = get_timestamp()
    memo["updated_at"] = None
    memo["source_transcript"] = input_path.name

    # Step 3: Validate memo
    logger.info("Step 3: Validating extracted memo...")
    is_valid, errors = validate_memo(memo)
    if not is_valid:
        logger.error(f"Memo validation failed: {errors}")
        logger.warning("Proceeding with warnings — review memo manually")
    for err in errors:
        logger.warning(f"Validation: {err}")

    # Step 4: Generate Retell Agent Spec
    logger.info("Step 4: Generating Retell Agent Spec...")
    agent_spec = generate_agent_spec(memo)

    # Step 5: Validate agent spec
    logger.info("Step 5: Validating agent spec...")
    is_valid_spec, spec_errors = validate_agent_spec(agent_spec)
    for err in spec_errors:
        logger.warning(f"Spec validation: {err}")

    # Step 6: Save all outputs
    logger.info("Step 6: Saving outputs...")
    v1_dir = ensure_account_dirs(account_id, "v1")

    save_text(transcript, v1_dir / "transcript.txt")
    save_json(memo, v1_dir / "memo.json")
    save_json(agent_spec, v1_dir / "agent_spec.json")

    logger.info(f"✅ Pipeline A complete for {memo['company_name']}")
    logger.info(f"   Account ID: {account_id}")
    logger.info(f"   Output dir: {v1_dir}")
    logger.info(f"   Memo fields populated: {sum(1 for v in memo.values() if v is not None)}/{len(memo)}")

    return {
        "account_id": account_id,
        "company_name": memo["company_name"],
        "v1_dir": str(v1_dir),
        "memo_path": str(v1_dir / "memo.json"),
        "agent_spec_path": str(v1_dir / "agent_spec.json"),
        "transcript_path": str(v1_dir / "transcript.txt"),
        "validation_warnings": errors + spec_errors
    }


def main():
    parser = argparse.ArgumentParser(description="Pipeline A: Demo Call → v1 Agent")
    parser.add_argument("input", type=str, help="Path to audio file or transcript")
    parser.add_argument("--company", "-c", type=str, help="Company name hint")
    parser.add_argument("--skip-transcription", action="store_true",
                        help="Treat input as transcript text file")

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        logger.error(f"Input not found: {input_path}")
        sys.exit(1)

    result = run_pipeline_a(input_path, args.company, args.skip_transcription)
    print(f"\nPipeline A Results:")
    print(f"  Account ID: {result['account_id']}")
    print(f"  Company: {result['company_name']}")
    print(f"  Outputs: {result['v1_dir']}")


if __name__ == "__main__":
    main()
