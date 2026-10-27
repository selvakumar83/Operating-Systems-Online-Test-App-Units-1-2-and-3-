-- Run this in Supabase SQL Editor before deploying, if centralized results are required.
create table if not exists public.os_online_test_results (
    id bigint generated always as identity primary key,
    student_name text not null,
    srn text not null,
    test_scope text not null,
    score integer not null,
    total_questions integer not null,
    percentage numeric(5,2) not null,
    started_at timestamptz not null,
    submitted_at timestamptz not null,
    elapsed_seconds integer not null default 0,
    auto_submitted boolean not null default false,
    answers_json jsonb not null default '{}'::jsonb,
    review_json jsonb not null default '[]'::jsonb
);

create index if not exists os_online_test_results_srn_idx
    on public.os_online_test_results (srn);
create index if not exists os_online_test_results_submitted_at_idx
    on public.os_online_test_results (submitted_at desc);

-- The app uses the service-role key only on the Streamlit server, never in the browser.
-- Row-level security remains enabled; do not publish the service-role key or put it in source files.
alter table public.os_online_test_results enable row level security;
