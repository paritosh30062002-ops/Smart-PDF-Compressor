-- Smart PDF Compressor: run this once in Supabase  ->  SQL Editor  ->  New query  ->  Run
-- Stores only small records (who, plan, counts). PDFs themselves are never stored.

create table if not exists public.profiles (
    email            text primary key,
    name             text,
    phone            text,
    provider         text default 'email',          -- 'google' or 'email'
    plan             text not null default 'free',  -- free | pro_1k | pro_3k | pro_unlimited
    plan_started_at  timestamptz,
    plan_expires_at  timestamptz,
    created_at       timestamptz not null default now(),
    last_login_at    timestamptz
);

create table if not exists public.usage_events (
    id            bigint generated always as identity primary key,
    email         text not null references public.profiles(email) on delete cascade,
    files_count   integer not null default 0,   -- uploaded ZIP/PDF files in the job
    pdf_count     integer not null default 0,   -- PDFs compressed in the job
    bytes_before  bigint  not null default 0,
    bytes_after   bigint  not null default 0,
    created_at    timestamptz not null default now()
);
create index if not exists usage_events_email_time on public.usage_events (email, created_at);

create table if not exists public.upgrade_requests (
    id          bigint generated always as identity primary key,
    email       text not null references public.profiles(email) on delete cascade,
    plan        text not null,
    note        text default '',
    status      text not null default 'pending',  -- pending | approved | rejected
    created_at  timestamptz not null default now()
);

-- Lock the tables: only the server (service_role key, kept in Streamlit Secrets) can read/write.
alter table public.profiles         enable row level security;
alter table public.usage_events     enable row level security;
alter table public.upgrade_requests enable row level security;
