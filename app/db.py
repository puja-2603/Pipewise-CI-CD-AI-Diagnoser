import os
from supabase import create_client, Client

_client: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


def get_recent_failures(repo_full_name: str, limit: int = 200) -> list[dict]:
    """Pull recent failures + embeddings for this repo to compare against."""
    resp = (
        _client.table("failures")
        .select("id, embedding, error_summary, occurrence_count")
        .eq("repo_full_name", repo_full_name)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data


def insert_failure(record: dict) -> dict:
    resp = _client.table("failures").insert(record).execute()
    return resp.data[0]


def increment_occurrence(failure_id: str):
    # Bump the occurrence_count on the original failure this one matches
    _client.rpc("increment_occurrence_count", {"row_id": failure_id}).execute()


def mark_auto_fix(failure_id: str, pr_url: str):
    _client.table("failures").update(
        {"auto_fix_attempted": True, "auto_fix_pr_url": pr_url}
    ).eq("id", failure_id).execute()
