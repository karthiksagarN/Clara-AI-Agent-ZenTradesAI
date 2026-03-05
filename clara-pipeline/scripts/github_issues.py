"""
GitHub Issues integration for tracking account processing.
Creates issues for Pipeline A, updates/closes for Pipeline B.
"""

import os
import sys
import argparse
import json
from pathlib import Path

import requests

from utils import setup_logging

logger = setup_logging("github_issues")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_API = "https://api.github.com"


def _headers():
    if not GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not set — issue tracking disabled")
        return None
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }


def create_issue(account_id: str, company_name: str, version: str, details: dict = None) -> dict:
    """Create a GitHub Issue for account tracking."""
    headers = _headers()
    if not headers or not GITHUB_REPO:
        logger.info(f"[DRY RUN] Would create issue: [{version}] {company_name} ({account_id})")
        return {"number": 0, "html_url": "dry-run"}

    title = f"[{version.upper()}] {company_name} — Agent Configuration"
    body = f"""## Account Processing: {company_name}

**Account ID:** `{account_id}`
**Version:** {version}
**Status:** {'Preliminary (Demo)' if version == 'v1' else 'Updated (Onboarding)'}

### Details
```json
{json.dumps(details or {}, indent=2)}
```

### Checklist
- [{'x' if version == 'v1' else ' '}] Demo call processed (v1)
- [{'x' if version == 'v2' else ' '}] Onboarding call processed (v2)
- [ ] Agent reviewed and approved
- [ ] Agent deployed to Retell
"""

    labels = ["clara-agent", version]
    if version == "v2":
        labels.append("onboarding-complete")

    try:
        response = requests.post(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/issues",
            headers=headers,
            json={"title": title, "body": body, "labels": labels}
        )
        response.raise_for_status()
        issue = response.json()
        logger.info(f"Created issue #{issue['number']}: {issue['html_url']}")
        return issue
    except Exception as e:
        logger.error(f"Failed to create issue: {e}")
        return {"number": 0, "error": str(e)}


def find_issue(account_id: str) -> dict:
    """Find an existing issue for an account."""
    headers = _headers()
    if not headers or not GITHUB_REPO:
        return None

    try:
        response = requests.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/issues",
            headers=headers,
            params={"state": "open", "labels": "clara-agent"}
        )
        response.raise_for_status()
        issues = response.json()

        for issue in issues:
            if account_id in issue.get("body", ""):
                return issue
        return None
    except Exception as e:
        logger.error(f"Failed to search issues: {e}")
        return None


def update_issue(issue_number: int, account_id: str, company_name: str, changes_count: int) -> dict:
    """Update an existing issue with v2 info."""
    headers = _headers()
    if not headers or not GITHUB_REPO:
        logger.info(f"[DRY RUN] Would update issue #{issue_number} with v2 status")
        return {"number": issue_number}

    comment = f"""## Onboarding Update Applied ✅

**{changes_count} changes** applied from onboarding call.

Updated to **v2**. See `outputs/accounts/{account_id}/v2/` for details.
See `changelog/{account_id}_changes.md` for full changelog.
"""

    try:
        # Add comment
        requests.post(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{issue_number}/comments",
            headers=headers,
            json={"body": comment}
        )

        # Update labels
        requests.post(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/issues/{issue_number}/labels",
            headers=headers,
            json={"labels": ["v2", "onboarding-complete"]}
        )

        logger.info(f"Updated issue #{issue_number}")
        return {"number": issue_number}
    except Exception as e:
        logger.error(f"Failed to update issue: {e}")
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Manage GitHub Issues for account tracking")
    parser.add_argument("action", choices=["create", "update", "find"])
    parser.add_argument("--account-id", "-a", required=True)
    parser.add_argument("--company", "-c", type=str, default="Unknown")
    parser.add_argument("--version", "-v", type=str, default="v1")
    parser.add_argument("--issue-number", "-n", type=int)
    parser.add_argument("--changes", type=int, default=0)

    args = parser.parse_args()

    if args.action == "create":
        result = create_issue(args.account_id, args.company, args.version)
        print(json.dumps(result, indent=2))
    elif args.action == "find":
        issue = find_issue(args.account_id)
        print(json.dumps(issue, indent=2) if issue else "No issue found")
    elif args.action == "update":
        if not args.issue_number:
            issue = find_issue(args.account_id)
            args.issue_number = issue["number"] if issue else 0
        result = update_issue(args.issue_number, args.account_id, args.company, args.changes)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
