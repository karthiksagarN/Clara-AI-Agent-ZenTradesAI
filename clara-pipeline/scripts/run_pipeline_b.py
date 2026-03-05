"""
Pipeline B: Onboarding Call → Updated Agent (v2)
Processes an onboarding transcript, patches v1 memo, generates v2 agent spec.
"""

import sys
import argparse
from pathlib import Path

from utils import (
    setup_logging, generate_account_id, ensure_account_dirs,
    save_json, save_text, load_json, load_text, get_timestamp,
    OUTPUT_DIR
)
from transcribe import transcribe_audio
from extract import extract_from_onboarding
from generate_agent import generate_agent_spec
from patch import apply_structured_delta, generate_changelog_json, generate_changelog_markdown
from validate import validate_memo, validate_agent_spec

logger = setup_logging("pipeline_b")


def find_v1_memo(account_id: str) -> Path:
    """Find the v1 memo for a given account."""
    v1_path = OUTPUT_DIR / "accounts" / account_id / "v1" / "memo.json"
    if v1_path.exists():
        return v1_path
    raise FileNotFoundError(f"No v1 memo found for account {account_id} at {v1_path}")


def run_pipeline_b(
    input_path: Path,
    account_id: str = None,
    company_name: str = None,
    skip_transcription: bool = False
) -> dict:
    """
    Run Pipeline B: Onboarding Call → v2 outputs.

    Args:
        input_path: Path to onboarding audio or transcript
        account_id: Account ID to update (if known)
        company_name: Company name (to derive account_id if not given)
        skip_transcription: Treat input as transcript directly

    Returns:
        dict with paths to v2 outputs
    """
    logger.info(f"=" * 60)
    logger.info(f"PIPELINE B: Starting for {input_path.name}")
    logger.info(f"=" * 60)

    # Step 1: Get transcript
    if input_path.suffix == ".txt" or skip_transcription:
        logger.info("Step 1: Using provided transcript")
        transcript = load_text(input_path)
    else:
        logger.info("Step 1: Transcribing audio with Whisper...")
        transcript = transcribe_audio(input_path)

    # Step 2: Find v1 memo
    if not account_id and company_name:
        account_id = generate_account_id(company_name)

    if not account_id:
        # Try to find account from available v1 outputs
        accounts_dir = OUTPUT_DIR / "accounts"
        if accounts_dir.exists():
            available = [d.name for d in accounts_dir.iterdir() if d.is_dir()]
            if len(available) == 1:
                account_id = available[0]
                logger.info(f"Auto-detected account: {account_id}")
            else:
                logger.error(f"Multiple accounts found: {available}. Specify --account-id or --company")
                sys.exit(1)
        else:
            logger.error("No v1 outputs found. Run Pipeline A first.")
            sys.exit(1)

    logger.info(f"Step 2: Loading v1 memo for account {account_id}...")
    v1_memo_path = find_v1_memo(account_id)
    v1_memo = load_json(v1_memo_path)
    logger.info(f"Loaded v1 memo: {v1_memo.get('company_name')}")

    # Step 3: Extract deltas from onboarding transcript
    logger.info("Step 3: Extracting deltas from onboarding transcript...")
    delta = extract_from_onboarding(transcript, v1_memo)

    # Step 4: Apply delta to produce v2 memo
    logger.info("Step 4: Applying deltas to produce v2 memo...")
    v2_memo, changes = apply_structured_delta(v1_memo, delta)

    # Step 5: Validate v2 memo
    logger.info("Step 5: Validating v2 memo...")
    is_valid, errors = validate_memo(v2_memo)
    for err in errors:
        logger.warning(f"Validation: {err}")

    # Step 6: Generate v2 Agent Spec
    logger.info("Step 6: Generating v2 Retell Agent Spec...")
    agent_spec = generate_agent_spec(v2_memo)

    # Step 7: Validate agent spec
    logger.info("Step 7: Validating v2 agent spec...")
    is_valid_spec, spec_errors = validate_agent_spec(agent_spec)
    for err in spec_errors:
        logger.warning(f"Spec validation: {err}")

    # Step 8: Save all outputs
    logger.info("Step 8: Saving v2 outputs...")
    v2_dir = ensure_account_dirs(account_id, "v2")

    save_text(transcript, v2_dir / "transcript.txt")
    save_json(v2_memo, v2_dir / "memo.json")
    save_json(agent_spec, v2_dir / "agent_spec.json")

    # Save delta for reference
    save_json(delta, v2_dir / "delta.json")

    # Generate and save changelogs
    changelog_json = generate_changelog_json(account_id, changes, v1_memo, v2_memo)
    changelog_md = generate_changelog_markdown(account_id, changes, v1_memo, v2_memo)

    save_json(changelog_json, v2_dir / "changelog.json")

    from utils import CHANGELOG_DIR
    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    save_text(changelog_md, CHANGELOG_DIR / f"{account_id}_changes.md")

    logger.info(f"✅ Pipeline B complete for {v2_memo.get('company_name')}")
    logger.info(f"   Account ID: {account_id}")
    logger.info(f"   Changes applied: {len(changes)}")
    logger.info(f"   Output dir: {v2_dir}")

    return {
        "account_id": account_id,
        "company_name": v2_memo.get("company_name"),
        "v2_dir": str(v2_dir),
        "memo_path": str(v2_dir / "memo.json"),
        "agent_spec_path": str(v2_dir / "agent_spec.json"),
        "changelog_path": str(v2_dir / "changelog.json"),
        "changes_count": len(changes),
        "validation_warnings": errors + spec_errors
    }


def main():
    parser = argparse.ArgumentParser(description="Pipeline B: Onboarding → v2 Agent")
    parser.add_argument("input", type=str, help="Path to onboarding audio or transcript")
    parser.add_argument("--account-id", "-a", type=str, help="Account ID to update")
    parser.add_argument("--company", "-c", type=str, help="Company name (to find account)")
    parser.add_argument("--skip-transcription", action="store_true",
                        help="Treat input as transcript text file")

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        logger.error(f"Input not found: {input_path}")
        sys.exit(1)

    result = run_pipeline_b(input_path, args.account_id, args.company, args.skip_transcription)
    print(f"\nPipeline B Results:")
    print(f"  Account ID: {result['account_id']}")
    print(f"  Company: {result['company_name']}")
    print(f"  Changes: {result['changes_count']}")
    print(f"  Outputs: {result['v2_dir']}")


if __name__ == "__main__":
    main()
