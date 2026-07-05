from dotenv import load_dotenv
load_dotenv()

from app import ai_diagnosis, fingerprint, db

sample_log = """
=== Job: build ===
Collecting nonexistentpackage123==1.0.0
ERROR: Could not find a version that satisfies the requirement nonexistentpackage123==1.0.0
ERROR: No matching distribution found for nonexistentpackage123==1.0.0
Process completed with exit code 1.
"""

diagnosis, tokens = ai_diagnosis.diagnose(sample_log)
signature = ai_diagnosis.extract_error_signature(sample_log)
embedding = fingerprint.embed(signature)

record = {
    "repo_full_name": "test/repo",
    "workflow_run_id": 888888,
    "branch": "main",
    "commit_sha": "def456",
    "commit_message": "test commit v2",
    "error_summary": diagnosis.root_cause,
    "diagnosis": diagnosis.fix_suggestion,
    "fix_category": diagnosis.fix_category,
    "confidence": diagnosis.confidence,
    "embedding": embedding,
    "is_recurring": False,
    "tokens_used": tokens,
    "estimated_cost_usd": ai_diagnosis.estimate_cost_usd(tokens),
    "estimated_minutes_saved": 15,
}

result = db.insert_failure(record)
print("Inserted:", result["id"])