import os
import json
import re
from groq import Groq
from app.models import Diagnosis

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are a senior DevOps engineer analyzing a failed CI/CD pipeline log.
Respond ONLY with a JSON object matching this schema, no preamble, no markdown fences:

{
  "root_cause": "one or two sentence plain-English explanation of what actually broke",
  "fix_category": "one of: env_var_missing, dependency_mismatch, lint_format, flaky_test, unknown",
  "fix_suggestion": "concrete, actionable fix a human would need to do",
  "confidence": 0.0 to 1.0,
  "safe_to_auto_fix": true or false,
  "proposed_patch": null or the full corrected content of ONE file, only if you are highly
     confident (>0.85) AND the fix is a simple, mechanical, single-file change
     (e.g. a version pin in requirements.txt/package.json, a missing key in a config file,
     an auto-formattable file). Never propose a patch for logic bugs, flaky tests,
     or anything requiring judgment.
"""


def diagnose(log_text: str) -> Diagnosis:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CI failure log:\n\n{log_text}"},
        ],
        temperature=0.2,
        max_tokens=1200,
    )
    raw = response.choices[0].message.content
    data = json.loads(raw)
    tokens_used = response.usage.total_tokens
    return Diagnosis(**data), tokens_used


def estimate_cost_usd(tokens_used: int) -> float:
    # Groq's Llama 3.3 70B pricing is roughly $0.59 / million input tokens,
    # $0.79 / million output tokens as of early 2026. We use a blended
    # approximate rate for simplicity — update if Groq's pricing changes.
    blended_rate_per_million = 0.70
    return round((tokens_used / 1_000_000) * blended_rate_per_million, 6)


def extract_error_signature(log_text: str, max_lines: int = 5) -> str:
    """
    Pull the most likely 'actual error' lines out of a raw log, so we have
    something STABLE to fingerprint/embed — unlike the LLM's root_cause
    text, which is reworded slightly every time it's generated and is
    therefore unreliable for similarity matching across separate runs.
    """
    error_pattern = re.compile(r"(error|exception|fail|traceback)", re.IGNORECASE)
    lines = log_text.splitlines()
    error_lines = [line.strip() for line in lines if error_pattern.search(line)]

    if not error_lines:
        # Fall back to the last few non-empty lines if no obvious error keyword found
        non_empty = [l.strip() for l in lines if l.strip()]
        error_lines = non_empty[-max_lines:]

    # Take the last N matches — usually the most specific/final error, not
    # earlier warnings — and strip volatile bits (timestamps, run-specific
    # paths/IDs) so identical error types match even across different runs.
    signature_lines = error_lines[-max_lines:]
    signature = " | ".join(signature_lines)
    signature = re.sub(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*", "", signature)  # timestamps
    signature = re.sub(r"\b[0-9a-f]{7,40}\b", "", signature)  # commit SHAs / hex IDs
    signature = re.sub(r"\s+", " ", signature).strip()
    return signature