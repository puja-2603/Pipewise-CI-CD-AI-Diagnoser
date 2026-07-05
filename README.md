# CI/CD AI Failure Diagnoser (with Recurrence Detection + Auto-Fix PRs)

An AI-powered assistant that watches your GitHub Actions pipeline, diagnoses
failures in plain English, detects when a failure is a **repeat** of a past
issue, and automatically opens a **fix PR** for well-understood, low-risk
failure types.

This is not just "send logs to an LLM and post a comment." The two things
that make it different from typical clones:

1. **Failure fingerprinting** — every failure is embedded and compared
   against past failures. If it's 80%+ similar to something seen before,
   we tell you it's recurring ("this is the 4th time this test has
   flaked this month") instead of treating every failure as brand new.
2. **Tiered auto-remediation** — most failures just get a diagnosis
   comment. But for a small set of high-confidence, safe fix categories
   (missing env var reference, pinned dependency mismatch, lint/format
   failure), the system opens an actual PR with the fix, not just a
   suggestion.

It also tracks a running **cost vs. time-saved** estimate so you can put a
number on the tool's value.

---

## Architecture

```
GitHub Actions (your repo)
        │  workflow_run: failure
        ▼
FastAPI backend (Render/Railway free tier)
        │
        ├── GitHub API  → fetch failed job logs
        ├── Groq API    → LLM diagnosis (root cause + fix category)
        ├── Embeddings  → fingerprint + similarity search (recurrence check)
        ├── Supabase    → store failures, fingerprints, fix history, cost log
        └── GitHub API  → post PR comment  OR  open auto-fix PR
```

## Stack (all free tier)

| Piece | Tool |
|---|---|
| Backend | FastAPI (Python) |
| LLM | Groq API (free, fast — Llama 3.3 70B) |
| Embeddings | Groq/local `sentence-transformers` (free, no API cost) |
| Database | Supabase (free Postgres + pgvector) |
| Hosting | Render or Railway free web service |
| CI trigger | GitHub Actions `workflow_run` event |
| Fix delivery | GitHub REST API (PR comments + auto-fix PRs) |

## Project layout

```
ci-ai-diagnoser/
├── app/
│   ├── main.py          # FastAPI app + webhook endpoint
│   ├── github_client.py # fetch logs, post comments, open PRs
│   ├── ai_diagnosis.py  # Groq prompt + structured diagnosis
│   ├── fingerprint.py   # embeddings + similarity search
│   ├── db.py            # Supabase client + queries
│   └── models.py        # Pydantic schemas
├── supabase_schema.sql  # run this in Supabase SQL editor
├── .github/workflows/
│   └── example-caller.yml  # add this to repos you want monitored
├── requirements.txt
├── .env.example
└── README.md
```

## Setup steps

1. **Supabase**: create a free project, run `supabase_schema.sql` in the SQL editor, enable the `pgvector` extension.
2. **Groq**: create a free API key at console.groq.com.
3. **GitHub**: create a Personal Access Token (repo scope) so the backend can read logs and open PRs.
4. **Deploy backend**: push this folder to its own GitHub repo, connect it to Render/Railway, set the env vars from `.env.example`.
5. **Register the webhook**: in each repo you want monitored, go to Settings → Webhooks → Add webhook → payload URL = your deployed `/webhook` endpoint, event = "Workflow runs".
6. Push a commit that fails CI and watch the PR comment (or auto-fix PR) appear.

## Resume-ready description

> Built and deployed an AI-powered CI/CD diagnostic system that fingerprints
> pipeline failures using embeddings to detect recurring issues, and
> automatically opens fix PRs for high-confidence failure categories —
> reducing manual triage for repeat failures and tracking estimated
> engineering hours saved.
