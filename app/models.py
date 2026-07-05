from pydantic import BaseModel
from typing import Optional


class Diagnosis(BaseModel):
    root_cause: str
    fix_category: str          # one of: env_var_missing, dependency_mismatch, lint_format, flaky_test, unknown
    fix_suggestion: str
    confidence: float          # 0.0 - 1.0
    safe_to_auto_fix: bool
    proposed_patch: Optional[str] = None   # unified diff or file content, only if safe_to_auto_fix
    file_path: str | None = None
    new_file_content: str | None = None


class WebhookPayload(BaseModel):
    repo_full_name: str
    workflow_run_id: int
    branch: str
    commit_sha: str
    commit_message: str
    pr_number: Optional[int] = None
