import os
import json
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
