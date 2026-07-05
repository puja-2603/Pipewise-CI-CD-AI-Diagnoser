-- Run this in the Supabase SQL editor.
-- Enables pgvector for embedding similarity search.

create extension if not exists vector;

create table if not exists failures (
    id uuid primary key default gen_random_uuid(),
    repo_full_name text not null,
    workflow_run_id bigint not null,
    branch text,
    commit_sha text,
    commit_message text,
    error_summary text,           -- short AI-generated summary (used for embedding)
    diagnosis text,                -- full AI diagnosis text
    fix_category text,             -- e.g. 'env_var_missing', 'dependency_mismatch', 'lint_format', 'unknown'
    confidence float,
    embedding vector(384),         -- sentence-transformers all-MiniLM-L6-v2 output size
    is_recurring boolean default false,
    similar_failure_id uuid references failures(id),
    occurrence_count int default 1,
    auto_fix_attempted boolean default false,
    auto_fix_pr_url text,
    tokens_used int,
    estimated_cost_usd numeric(10,6),
    estimated_minutes_saved int,
    created_at timestamptz default now()
);

-- Speeds up similarity search
create index if not exists failures_embedding_idx
    on failures using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create index if not exists failures_repo_idx on failures (repo_full_name);

-- Called whenever a new failure matches an existing fingerprint,
-- so we can show "this has happened N times" in the diagnosis comment.
create or replace function increment_occurrence_count(row_id uuid)
returns void as $$
begin
    update failures
    set occurrence_count = occurrence_count + 1
    where id = row_id;
end;
$$ language plpgsql;
