import os
import httpx

GITHUB_API = "https://api.github.com"
TOKEN = os.environ["GITHUB_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

async def fetch_failed_job_logs(repo_full_name: str, run_id: int) -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        jobs_resp = await client.get(
            f"{GITHUB_API}/repos/{repo_full_name}/actions/runs/{run_id}/jobs"
        )
        jobs_resp.raise_for_status()
        jobs = jobs_resp.json()["jobs"]

        failed_jobs = [j for j in jobs if j["conclusion"] == "failure"]
        if not failed_jobs:
            return ""

        all_logs = []
        for job in failed_jobs:
            # Don't auto-follow here — we need to inspect the redirect first
            log_resp = await client.get(
                f"{GITHUB_API}/repos/{repo_full_name}/actions/jobs/{job['id']}/logs",
                follow_redirects=False,
            )
            if log_resp.status_code in (302, 301) and "location" in log_resp.headers:
                blob_url = log_resp.headers["location"]
                # Fetch the redirect target WITHOUT our GitHub auth headers
                async with httpx.AsyncClient(timeout=30) as blob_client:
                    blob_resp = await blob_client.get(blob_url)
                    if blob_resp.status_code == 200:
                        all_logs.append(f"=== Job: {job['name']} ===\n{blob_resp.text}")
            elif log_resp.status_code == 200:
                # Some GitHub Enterprise setups return logs directly, no redirect
                all_logs.append(f"=== Job: {job['name']} ===\n{log_resp.text}")

        combined = "\n\n".join(all_logs)
        return combined[-12000:]


async def post_pr_comment(repo_full_name: str, commit_sha: str, body: str, pr_number: int | None):
    """Post the diagnosis as a comment on the PR if we have one, else on the commit."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        if pr_number:
            url = f"{GITHUB_API}/repos/{repo_full_name}/issues/{pr_number}/comments"
        else:
            url = f"{GITHUB_API}/repos/{repo_full_name}/commits/{commit_sha}/comments"
        resp = await client.post(url, json={"body": body})
        resp.raise_for_status()
        return resp.json()


async def open_auto_fix_pr(
    repo_full_name: str, base_branch: str, file_path: str, new_content: str, fix_summary: str
) -> str:
    """
    Opens a small PR that replaces a single file's content with `new_content`.
    Kept intentionally simple/safe: single-file, human-reviewable changes only.
    Returns the PR URL.
    """
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        # 1. Get base branch ref
        ref_resp = await client.get(
            f"{GITHUB_API}/repos/{repo_full_name}/git/ref/heads/{base_branch}"
        )
        ref_resp.raise_for_status()
        base_sha = ref_resp.json()["object"]["sha"]

        # 2. Create a new branch
        fix_branch = f"ai-fix/{file_path.replace('/', '-')}-{base_sha[:7]}"
        await client.post(
            f"{GITHUB_API}/repos/{repo_full_name}/git/refs",
            json={"ref": f"refs/heads/{fix_branch}", "sha": base_sha},
        )

        # 3. Get current file sha (needed to update it)
        file_resp = await client.get(
            f"{GITHUB_API}/repos/{repo_full_name}/contents/{file_path}",
            params={"ref": fix_branch},
        )
        file_sha = file_resp.json()["sha"] if file_resp.status_code == 200 else None

        # 4. Commit the fix
        import base64
        content_b64 = base64.b64encode(new_content.encode()).decode()
        commit_payload = {
            "message": f"fix: AI-suggested fix — {fix_summary}",
            "content": content_b64,
            "branch": fix_branch,
        }
        if file_sha:
            commit_payload["sha"] = file_sha

        await client.put(
            f"{GITHUB_API}/repos/{repo_full_name}/contents/{file_path}",
            json=commit_payload,
        )

        # 5. Open the PR
        pr_resp = await client.post(
            f"{GITHUB_API}/repos/{repo_full_name}/pulls",
            json={
                "title": f"[AI Fix] {fix_summary}",
                "head": fix_branch,
                "base": base_branch,
                "body": (
                    "This PR was opened automatically by the CI/CD AI Diagnoser.\n\n"
                    f"**Fix summary:** {fix_summary}\n\n"
                    "Please review before merging — this is a suggested fix, not a guaranteed one."
                ),
            },
        )
        pr_resp.raise_for_status()
        return pr_resp.json()["html_url"]
