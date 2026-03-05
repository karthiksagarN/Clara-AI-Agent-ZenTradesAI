"""
Generate an HTML diff viewer that shows v1 → v2 changes for all accounts.
Bonus feature for the assignment.
"""

import json
import sys
from pathlib import Path

from utils import setup_logging, OUTPUT_DIR, load_json

logger = setup_logging("diff_viewer")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clara Pipeline — v1 → v2 Diff Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 2rem; }
        h1 { color: #58a6ff; margin-bottom: 0.5rem; }
        .subtitle { color: #8b949e; margin-bottom: 2rem; }
        .account-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 2rem; overflow: hidden; }
        .account-header { padding: 1rem 1.5rem; background: #21262d; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
        .account-header h2 { color: #f0f6fc; font-size: 1.2rem; }
        .badge { padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
        .badge-changes { background: #1f6feb33; color: #58a6ff; }
        .badge-added { background: #23863633; color: #3fb950; }
        .badge-modified { background: #9e6a0333; color: #d29922; }
        .changes-list { padding: 1rem 1.5rem; }
        .change-item { padding: 0.75rem; margin-bottom: 0.5rem; border-radius: 6px; border-left: 3px solid; }
        .change-added { border-color: #3fb950; background: #23863610; }
        .change-modified { border-color: #d29922; background: #9e6a0310; }
        .change-updated { border-color: #58a6ff; background: #1f6feb10; }
        .field-name { font-weight: 600; color: #f0f6fc; font-family: monospace; }
        .change-values { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 0.5rem; }
        .old-value, .new-value { padding: 0.5rem; border-radius: 4px; font-family: monospace; font-size: 0.85rem; white-space: pre-wrap; word-break: break-all; }
        .old-value { background: #da363310; border: 1px solid #da363340; }
        .new-value { background: #3fb95010; border: 1px solid #3fb95040; }
        .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: #8b949e; margin-bottom: 0.25rem; }
        .reason { color: #8b949e; font-size: 0.85rem; margin-top: 0.5rem; font-style: italic; }
        .summary-bar { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
        .summary-stat { background: #161b22; border: 1px solid #30363d; padding: 1rem 1.5rem; border-radius: 8px; text-align: center; }
        .summary-stat .number { font-size: 2rem; font-weight: 700; color: #58a6ff; }
        .summary-stat .label { margin-top: 0.25rem; }
        .no-data { text-align: center; padding: 3rem; color: #8b949e; }
        .toggle { cursor: pointer; user-select: none; }
        .collapse { max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }
        .collapse.open { max-height: 5000px; }
    </style>
</head>
<body>
    <h1>🔄 Clara Pipeline — Diff Viewer</h1>
    <p class="subtitle">Visual comparison of v1 (Demo) → v2 (Onboarding) changes</p>

    <div class="summary-bar">
        <div class="summary-stat">
            <div class="number" id="total-accounts">0</div>
            <div class="label">Accounts</div>
        </div>
        <div class="summary-stat">
            <div class="number" id="total-changes">0</div>
            <div class="label">Total Changes</div>
        </div>
        <div class="summary-stat">
            <div class="number" id="total-added">0</div>
            <div class="label">Fields Added</div>
        </div>
        <div class="summary-stat">
            <div class="number" id="total-modified">0</div>
            <div class="label">Fields Modified</div>
        </div>
    </div>

    <div id="accounts-container"></div>

    <script>
    // Changelog data injected by the generator
    const CHANGELOGS = __CHANGELOG_DATA__;

    function renderChanges() {
        const container = document.getElementById('accounts-container');
        let totalChanges = 0, totalAdded = 0, totalModified = 0;

        if (CHANGELOGS.length === 0) {
            container.innerHTML = '<div class="no-data">No v1 → v2 diffs found. Run both pipelines first.</div>';
            return;
        }

        document.getElementById('total-accounts').textContent = CHANGELOGS.length;

        CHANGELOGS.forEach((cl, idx) => {
            totalChanges += cl.total_changes || 0;
            const added = (cl.changes || []).filter(c => c.action === 'added').length;
            const modified = (cl.changes || []).filter(c => c.action === 'modified').length;
            totalAdded += added;
            totalModified += modified;

            let html = `
            <div class="account-card">
                <div class="account-header toggle" onclick="document.getElementById('changes-${idx}').classList.toggle('open')">
                    <h2>${cl.company_name || cl.account_id}</h2>
                    <div>
                        <span class="badge badge-changes">${cl.total_changes || 0} changes</span>
                        <span class="badge badge-added">${added} added</span>
                        <span class="badge badge-modified">${modified} modified</span>
                    </div>
                </div>
                <div class="changes-list collapse open" id="changes-${idx}">`;

            (cl.changes || []).forEach(change => {
                const cssClass = `change-${change.action}`;
                html += `
                    <div class="change-item ${cssClass}">
                        <div class="field-name">${change.field}</div>
                        <div class="change-values">
                            <div>
                                <div class="label">Old (v1)</div>
                                <div class="old-value">${JSON.stringify(change.old_value, null, 2) || 'null'}</div>
                            </div>
                            <div>
                                <div class="label">New (v2)</div>
                                <div class="new-value">${JSON.stringify(change.new_value, null, 2) || 'null'}</div>
                            </div>
                        </div>
                        <div class="reason">Reason: ${change.reason || 'N/A'}</div>
                    </div>`;
            });

            html += '</div></div>';
            container.innerHTML += html;
        });

        document.getElementById('total-changes').textContent = totalChanges;
        document.getElementById('total-added').textContent = totalAdded;
        document.getElementById('total-modified').textContent = totalModified;
    }

    renderChanges();
    </script>
</body>
</html>"""


def generate_diff_viewer():
    """Scan all accounts for changelogs and generate the HTML diff viewer."""
    accounts_dir = OUTPUT_DIR / "accounts"
    changelogs = []

    if accounts_dir.exists():
        for account_dir in sorted(accounts_dir.iterdir()):
            if not account_dir.is_dir():
                continue
            changelog_path = account_dir / "v2" / "changelog.json"
            if changelog_path.exists():
                try:
                    cl = load_json(changelog_path)
                    changelogs.append(cl)
                except Exception as e:
                    logger.error(f"Failed to load {changelog_path}: {e}")

    # Inject data into template
    html = HTML_TEMPLATE.replace("__CHANGELOG_DATA__", json.dumps(changelogs, indent=2, default=str))

    output_path = OUTPUT_DIR / "diff_viewer.html"
    with open(output_path, "w") as f:
        f.write(html)

    logger.info(f"Diff viewer generated: {output_path}")
    logger.info(f"Accounts with diffs: {len(changelogs)}")
    print(f"\nDiff viewer: {output_path}")
    print(f"Open in browser: file://{output_path.absolute()}")


if __name__ == "__main__":
    generate_diff_viewer()
