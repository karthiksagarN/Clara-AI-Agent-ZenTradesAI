"""
Patch system for applying onboarding deltas to v1 memos.
Produces v2 memos and detailed changelogs.
"""

import sys
import copy
import json
import argparse
from pathlib import Path
from datetime import datetime

from utils import (
    setup_logging, load_json, save_json, save_text, get_timestamp,
    CHANGELOG_DIR
)

logger = setup_logging("patch")


def deep_merge(base: dict, updates: dict, path: str = "") -> tuple[dict, list]:
    """
    Deep merge updates into base dict.
    Returns (merged_dict, list_of_changes).

    Onboarding data always wins over demo data.
    """
    merged = copy.deepcopy(base)
    changes = []

    for key, new_value in updates.items():
        current_path = f"{path}.{key}" if path else key

        if key in merged:
            old_value = merged[key]

            # Skip if values are identical
            if old_value == new_value:
                continue

            # Both are dicts — recurse
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                merged[key], sub_changes = deep_merge(old_value, new_value, current_path)
                changes.extend(sub_changes)
            else:
                # Overwrite with onboarding data
                merged[key] = new_value
                changes.append({
                    "field": current_path,
                    "action": "modified",
                    "old_value": old_value,
                    "new_value": new_value,
                    "reason": "onboarding_override"
                })
        else:
            # New field from onboarding
            merged[key] = new_value
            changes.append({
                "field": current_path,
                "action": "added",
                "old_value": None,
                "new_value": new_value,
                "reason": "new_from_onboarding"
            })

    return merged, changes


def apply_structured_delta(v1_memo: dict, delta: dict) -> tuple[dict, list]:
    """
    Apply a structured delta (from onboarding extraction) to a v1 memo.

    The delta format contains:
    - changes: fields that have new values
    - new_fields: fields that were null in v1 and now have values
    - questions_or_unknowns: remaining unknowns

    Returns:
        (v2_memo, list_of_change_entries)
    """
    v2 = copy.deepcopy(v1_memo)
    all_changes = []

    # Apply changes (fields that were modified)
    changes = delta.get("changes", {})
    for field, change_info in changes.items():
        new_value = change_info.get("new_value", change_info.get("value"))
        reason = change_info.get("reason", "updated_during_onboarding")

        old_value = v2.get(field)

        # Handle nested fields (e.g., business_hours.start)
        if "." in field:
            parts = field.split(".")
            target = v2
            for part in parts[:-1]:
                if part not in target or target[part] is None:
                    target[part] = {}
                target = target[part]
            old_value = target.get(parts[-1])
            target[parts[-1]] = new_value
        else:
            v2[field] = new_value

        all_changes.append({
            "field": field,
            "action": "modified",
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason
        })

    # Apply new fields
    new_fields = delta.get("new_fields", {})
    for field, field_info in new_fields.items():
        new_value = field_info.get("value", field_info.get("new_value"))
        reason = field_info.get("reason", "newly_provided_in_onboarding")

        if "." in field:
            parts = field.split(".")
            target = v2
            for part in parts[:-1]:
                if part not in target or target[part] is None:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = new_value
        else:
            v2[field] = new_value

        all_changes.append({
            "field": field,
            "action": "added",
            "old_value": None,
            "new_value": new_value,
            "reason": reason
        })

    # Update questions/unknowns
    if delta.get("questions_or_unknowns"):
        v2["questions_or_unknowns"] = delta["questions_or_unknowns"]
        all_changes.append({
            "field": "questions_or_unknowns",
            "action": "updated",
            "old_value": v1_memo.get("questions_or_unknowns"),
            "new_value": delta["questions_or_unknowns"],
            "reason": "updated_remaining_unknowns"
        })

    # Update version and timestamps
    v2["version"] = "v2"
    v2["updated_at"] = get_timestamp()

    if delta.get("onboarding_notes"):
        existing_notes = v2.get("notes", "") or ""
        v2["notes"] = f"{existing_notes}\n\n[Onboarding Notes]: {delta['onboarding_notes']}".strip()

    return v2, all_changes


def generate_changelog_json(account_id: str, changes: list, v1_memo: dict, v2_memo: dict) -> dict:
    """Generate a structured changelog JSON."""
    return {
        "account_id": account_id,
        "company_name": v2_memo.get("company_name", v1_memo.get("company_name")),
        "version_from": "v1",
        "version_to": "v2",
        "timestamp": get_timestamp(),
        "total_changes": len(changes),
        "changes": changes,
        "summary": {
            "fields_modified": len([c for c in changes if c["action"] == "modified"]),
            "fields_added": len([c for c in changes if c["action"] == "added"]),
            "fields_updated": len([c for c in changes if c["action"] == "updated"]),
        }
    }


def generate_changelog_markdown(account_id: str, changes: list, v1_memo: dict, v2_memo: dict) -> str:
    """Generate a human-readable changelog in Markdown."""
    company = v2_memo.get("company_name", account_id)
    md = f"# Changelog: {company}\n\n"
    md += f"**Account ID:** {account_id}\n"
    md += f"**Version:** v1 → v2\n"
    md += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    md += f"**Total Changes:** {len(changes)}\n\n"
    md += "---\n\n"

    # Group by action
    modifications = [c for c in changes if c["action"] == "modified"]
    additions = [c for c in changes if c["action"] == "added"]
    updates = [c for c in changes if c["action"] == "updated"]

    if modifications:
        md += "## Modified Fields\n\n"
        for c in modifications:
            md += f"### `{c['field']}`\n"
            md += f"- **Old:** {json.dumps(c['old_value'], default=str)}\n"
            md += f"- **New:** {json.dumps(c['new_value'], default=str)}\n"
            md += f"- **Reason:** {c['reason']}\n\n"

    if additions:
        md += "## New Fields (Added from Onboarding)\n\n"
        for c in additions:
            md += f"### `{c['field']}`\n"
            md += f"- **Value:** {json.dumps(c['new_value'], default=str)}\n"
            md += f"- **Reason:** {c['reason']}\n\n"

    if updates:
        md += "## Updated Fields\n\n"
        for c in updates:
            md += f"### `{c['field']}`\n"
            md += f"- **Old:** {json.dumps(c['old_value'], default=str)}\n"
            md += f"- **New:** {json.dumps(c['new_value'], default=str)}\n"
            md += f"- **Reason:** {c['reason']}\n\n"

    return md


def patch_memo(v1_path: Path, delta_path: Path, output_dir: Path, account_id: str) -> tuple[dict, dict]:
    """
    Full patch operation: load v1 + delta → produce v2 + changelog.

    Returns:
        (v2_memo, changelog_json)
    """
    v1_memo = load_json(v1_path)
    delta = load_json(delta_path)

    # Apply delta
    v2_memo, changes = apply_structured_delta(v1_memo, delta)

    # Generate changelogs
    changelog_json = generate_changelog_json(account_id, changes, v1_memo, v2_memo)
    changelog_md = generate_changelog_markdown(account_id, changes, v1_memo, v2_memo)

    # Save outputs
    save_json(v2_memo, output_dir / "memo.json")
    save_json(changelog_json, output_dir / "changelog.json")

    # Save markdown changelog
    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    save_text(changelog_md, CHANGELOG_DIR / f"{account_id}_changes.md")

    logger.info(f"Patched {account_id}: {len(changes)} changes applied")
    return v2_memo, changelog_json


def main():
    parser = argparse.ArgumentParser(description="Patch v1 memo with onboarding deltas")
    parser.add_argument("v1_memo", type=str, help="Path to v1 memo JSON")
    parser.add_argument("delta", type=str, help="Path to delta JSON from onboarding extraction")
    parser.add_argument("--account-id", "-a", required=True, help="Account ID")
    parser.add_argument("--output-dir", "-o", required=True, help="Output directory for v2 files")

    args = parser.parse_args()

    v2_memo, changelog = patch_memo(
        Path(args.v1_memo),
        Path(args.delta),
        Path(args.output_dir),
        args.account_id
    )

    print(f"\nPatch complete. {changelog['total_changes']} changes applied.")
    print(f"v2 memo: {args.output_dir}/memo.json")
    print(f"Changelog: {args.output_dir}/changelog.json")


if __name__ == "__main__":
    main()
