"""
Batch runner: Processes all demo and onboarding recordings/transcripts.
Runs Pipeline A on all demo files, then Pipeline B on all onboarding files.
"""

import sys
import json
import time
import argparse
from pathlib import Path

from utils import (
    setup_logging, find_recordings, find_transcripts, save_json,
    get_timestamp, RECORDINGS_DIR, OUTPUT_DIR
)
from run_pipeline_a import run_pipeline_a
from run_pipeline_b import run_pipeline_b

logger = setup_logging("run_all")

# Mapping of recording filenames to company names
# Update this when you have all 5 pairs
ACCOUNT_MAPPING = {
    # Demo files → company name
    "bens_electric_demo": "Ben's Electric Solutions",
    # Add more as recordings become available:
    # "company2_demo": "Company 2 Name",
    # "company3_demo": "Company 3 Name",
    # "company4_demo": "Company 4 Name",
    # "company5_demo": "Company 5 Name",
}

# Mapping of onboarding files to their corresponding demo account
ONBOARDING_MAPPING = {
    # Onboarding filename stem → company name (must match demo)
    "bens_electric_onboarding": "Ben's Electric Solutions",
    # Add more:
    # "company2_onboarding": "Company 2 Name",
}


def get_company_name(filename: str) -> str:
    """Try to get company name from filename mapping or derive it."""
    stem = Path(filename).stem.lower().replace(" ", "_").replace("-", "_")

    # Check mapping
    for key, name in {**ACCOUNT_MAPPING, **ONBOARDING_MAPPING}.items():
        if key in stem or stem in key:
            return name

    # Derive from filename
    return stem.replace("_demo", "").replace("_onboarding", "").replace("_", " ").title()


def run_all(demo_dir: Path = None, onboarding_dir: Path = None, transcripts_only: bool = False):
    """
    Run both pipelines on all available files.

    Args:
        demo_dir: Directory containing demo recordings/transcripts
        onboarding_dir: Directory containing onboarding recordings/transcripts
        transcripts_only: If True, only process .txt files
    """
    demo_dir = demo_dir or RECORDINGS_DIR / "demo"
    onboarding_dir = onboarding_dir or RECORDINGS_DIR / "onboarding"

    results = {
        "run_timestamp": get_timestamp(),
        "pipeline_a_results": [],
        "pipeline_b_results": [],
        "summary": {}
    }

    # --- Pipeline A: Demo Files ---
    logger.info("=" * 70)
    logger.info("PHASE 1: Running Pipeline A on all demo files")
    logger.info("=" * 70)

    demo_files = []
    if transcripts_only:
        demo_files = find_transcripts(demo_dir)
    else:
        demo_files = find_recordings(demo_dir) + find_transcripts(demo_dir)
        # Remove duplicates (prefer transcript if both exist)
        seen_stems = set()
        dedup_files = []
        for f in sorted(demo_files, key=lambda x: x.suffix != ".txt"):
            if f.stem not in seen_stems:
                seen_stems.add(f.stem)
                dedup_files.append(f)
        demo_files = dedup_files

    if not demo_files:
        logger.warning(f"No demo files found in {demo_dir}")
        logger.info("Please add demo recordings (.m4a, .mp3, .wav) or transcripts (.txt)")
    else:
        logger.info(f"Found {len(demo_files)} demo files: {[f.name for f in demo_files]}")

    for i, demo_file in enumerate(demo_files, 1):
        logger.info(f"\n--- Demo {i}/{len(demo_files)}: {demo_file.name} ---")
        company = get_company_name(demo_file.name)
        try:
            result = run_pipeline_a(
                demo_file,
                company_name_hint=company,
                skip_transcription=(demo_file.suffix == ".txt")
            )
            results["pipeline_a_results"].append({
                "status": "success",
                "file": demo_file.name,
                **result
            })
        except Exception as e:
            logger.error(f"Pipeline A failed for {demo_file.name}: {e}")
            results["pipeline_a_results"].append({
                "status": "error",
                "file": demo_file.name,
                "error": str(e)
            })
        time.sleep(1)  # Brief pause between LLM calls

    # --- Pipeline B: Onboarding Files ---
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2: Running Pipeline B on all onboarding files")
    logger.info("=" * 70)

    onboarding_files = []
    if transcripts_only:
        onboarding_files = find_transcripts(onboarding_dir)
    else:
        onboarding_files = find_recordings(onboarding_dir) + find_transcripts(onboarding_dir)
        seen_stems = set()
        dedup_files = []
        for f in sorted(onboarding_files, key=lambda x: x.suffix != ".txt"):
            if f.stem not in seen_stems:
                seen_stems.add(f.stem)
                dedup_files.append(f)
        onboarding_files = dedup_files

    if not onboarding_files:
        logger.warning(f"No onboarding files found in {onboarding_dir}")
        logger.info("Please add onboarding recordings or transcripts")
    else:
        logger.info(f"Found {len(onboarding_files)} onboarding files")

    for i, onb_file in enumerate(onboarding_files, 1):
        logger.info(f"\n--- Onboarding {i}/{len(onboarding_files)}: {onb_file.name} ---")
        company = get_company_name(onb_file.name)
        try:
            result = run_pipeline_b(
                onb_file,
                company_name=company,
                skip_transcription=(onb_file.suffix == ".txt")
            )
            results["pipeline_b_results"].append({
                "status": "success",
                "file": onb_file.name,
                **result
            })
        except Exception as e:
            logger.error(f"Pipeline B failed for {onb_file.name}: {e}")
            results["pipeline_b_results"].append({
                "status": "error",
                "file": onb_file.name,
                "error": str(e)
            })
        time.sleep(1)

    # --- Summary ---
    a_success = sum(1 for r in results["pipeline_a_results"] if r["status"] == "success")
    a_total = len(results["pipeline_a_results"])
    b_success = sum(1 for r in results["pipeline_b_results"] if r["status"] == "success")
    b_total = len(results["pipeline_b_results"])

    results["summary"] = {
        "pipeline_a": {"success": a_success, "total": a_total, "failed": a_total - a_success},
        "pipeline_b": {"success": b_success, "total": b_total, "failed": b_total - b_success},
        "total_processed": a_total + b_total,
        "total_success": a_success + b_success,
    }

    # Save summary report
    save_json(results, OUTPUT_DIR / "summary_report.json")

    logger.info("\n" + "=" * 70)
    logger.info("BATCH RUN COMPLETE")
    logger.info(f"Pipeline A: {a_success}/{a_total} succeeded")
    logger.info(f"Pipeline B: {b_success}/{b_total} succeeded")
    logger.info(f"Summary saved: {OUTPUT_DIR / 'summary_report.json'}")
    logger.info("=" * 70)

    return results


def main():
    parser = argparse.ArgumentParser(description="Run all pipelines on all recordings")
    parser.add_argument("--demo-dir", type=str, help="Directory with demo files")
    parser.add_argument("--onboarding-dir", type=str, help="Directory with onboarding files")
    parser.add_argument("--transcripts-only", action="store_true",
                        help="Only process .txt transcript files (skip audio)")

    args = parser.parse_args()
    demo_dir = Path(args.demo_dir) if args.demo_dir else None
    onb_dir = Path(args.onboarding_dir) if args.onboarding_dir else None

    results = run_all(demo_dir, onb_dir, args.transcripts_only)

    # Print summary
    print("\n" + json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    main()
