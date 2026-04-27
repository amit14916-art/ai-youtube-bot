"""
Delete all FAILED GitHub Actions workflow runs for ai-youtube-bot.
Usage: python delete_failed_runs.py
"""
import requests

# ─── CONFIG ───────────────────────────────────────────────────────
GITHUB_TOKEN = input("GitHub Personal Access Token daalo: ").strip()
OWNER        = "amit14916-art"
REPO         = "ai-youtube-bot"
WORKFLOW     = "run_bot.yml"
# ──────────────────────────────────────────────────────────────────

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def get_failed_runs():
    runs = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{WORKFLOW}/runs",
            headers=headers,
            params={"status": "failure", "per_page": 100, "page": page}
        )
        data = resp.json()
        batch = data.get("workflow_runs", [])
        if not batch:
            break
        runs.extend(batch)
        page += 1
    return runs

print("\n🔍 Failed runs dhundh raha hoon...")
failed = get_failed_runs()
print(f"Found {len(failed)} failed runs\n")

deleted = 0
for run in failed:
    run_id  = run["id"]
    run_num = run["run_number"]
    resp = requests.delete(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{run_id}",
        headers=headers
    )
    if resp.status_code == 204:
        print(f"  ✅ Deleted Run #{run_num} (ID: {run_id})")
        deleted += 1
    else:
        print(f"  ❌ Failed to delete Run #{run_num}: {resp.status_code} {resp.text}")

print(f"\n🎉 Done! {deleted}/{len(failed)} failed runs deleted.")
