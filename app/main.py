import os
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv

load_dotenv()
from app.models import WebhookPayload
from app import github_client, ai_diagnosis, fingerprint, db

app = FastAPI(title="CI/CD AI Diagnoser")

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload_body: bytes, signature_header: str | None):
    if not signature_header or not WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Missing signature or secret not configured")
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    verify_signature(body, request.headers.get("X-Hub-Signature-256"))

    payload = await request.json()

    # We only care about completed, failed workflow runs
    if payload.get("action") != "completed":
        return {"skipped": "not a completed action"}

    run = payload.get("workflow_run", {})
    if run.get("conclusion") != "failure":
        return {"skipped": "not a failure"}

    repo_full_name = payload["repository"]["full_name"]
    run_id = run["id"]
    branch = run["head_branch"]
    commit_sha = run["head_sha"]
    commit_message = run.get("head_commit", {}).get("message", "")
    pr_number = run.get("pull_requests", [{}])[0].get("number") if run.get("pull_requests") else None

    # Schedule the slow work to run AFTER this response is sent
    background_tasks.add_task(
        process_failure, repo_full_name, run_id, branch, commit_sha, commit_message, pr_number
    )

    # Respond to GitHub immediately — this is what stops the timeout
    return {"status": "accepted"}


async def process_failure(
    repo_full_name: str,
    run_id: int,
    branch: str,
    commit_sha: str,
    commit_message: str,
    pr_number: int | None,
):
    # everything below this line is UNCHANGED from your current code
    logs = await github_client.fetch_failed_job_logs(repo_full_name, run_id)
    if not logs:
        return {"skipped": "no logs found for failed jobs"}

    diagnosis, tokens_used = ai_diagnosis.diagnose(logs)
    cost = ai_diagnosis.estimate_cost_usd(tokens_used)

    error_signature = ai_diagnosis.extract_error_signature(logs)
    embedding = fingerprint.embed(error_signature)
    past_failures = db.get_recent_failures(repo_full_name)
    match, similarity = fingerprint.find_most_similar(embedding, past_failures)

    is_recurring = match is not None
    if is_recurring:
        db.increment_occurrence(match["id"])

    record = {
        "repo_full_name": repo_full_name,
        "workflow_run_id": run_id,
        "branch": branch,
        "commit_sha": commit_sha,
        "commit_message": commit_message,
        "error_summary": diagnosis.root_cause,
        "diagnosis": diagnosis.fix_suggestion,
        "fix_category": diagnosis.fix_category,
        "confidence": diagnosis.confidence,
        "embedding": embedding,
        "is_recurring": is_recurring,
        "similar_failure_id": match["id"] if match else None,
        "tokens_used": tokens_used,
        "estimated_cost_usd": cost,
        "estimated_minutes_saved": 30 if is_recurring else 15,
    }
    stored = db.insert_failure(record)

    recurrence_note = ""
    if is_recurring:
        occurrence = match.get("occurrence_count", 1) + 1
        recurrence_note = (
            f"\n\n**Recurring issue detected** — this looks like the same root cause "
            f"as a previous failure (similarity: {similarity:.0%}). "
            f"This is occurrence #{occurrence} for this pattern.\n"
        )

    comment_body = (
        f"### AI Diagnosis\n\n"
        f"**Root cause:** {diagnosis.root_cause}\n\n"
        f"**Suggested fix:** {diagnosis.fix_suggestion}\n\n"
        f"**Confidence:** {diagnosis.confidence:.0%}"
        f"{recurrence_note}\n"
        f"_Diagnosis cost: ~${cost:.4f} · Estimated time saved: "
        f"{record['estimated_minutes_saved']} min_"
    )

    auto_fix_threshold = float(os.environ.get("AUTO_FIX_CONFIDENCE_THRESHOLD", 0.85))

        if (
            diagnosis.safe_to_auto_fix
            and diagnosis.confidence >= auto_fix_threshold
            and diagnosis.file_path
            and diagnosis.new_file_content
            and diagnosis.fix_category in ("env_var_missing", "dependency_mismatch", "lint_format")
        ):
            try:
                pr_url = await github_client.open_auto_fix_pr(
                    repo_full_name,
                    base_branch=branch,
                    file_path=diagnosis.file_path,
                    new_content=diagnosis.new_file_content,
                    fix_summary=diagnosis.fix_suggestion,
                )
                db.mark_auto_fix(stored["id"], pr_url)
                comment_body += f"\n\n_An automated fix PR was opened: {pr_url}_"
            except Exception as e:
                comment_body += (
                    "\n\n_Attempted an automated fix, but PR creation failed "
                    f"({type(e).__name__}) — please fix manually._"
                )

    await github_client.post_pr_comment(repo_full_name, commit_sha, comment_body, pr_number)

    return {
        "status": "diagnosed",
        "is_recurring": is_recurring,
        "fix_category": diagnosis.fix_category,
        "confidence": diagnosis.confidence,
    }