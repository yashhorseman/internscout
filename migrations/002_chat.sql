create table sessions (
  id         uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  profile    jsonb not null default '{}'::jsonb
);

create table messages (
  id         bigserial primary key,
  session_id uuid not null references sessions(id) on delete cascade,
  role       text not null check (role in ('user','assistant','tool')),
  content    jsonb not null,
  created_at timestamptz not null default now()
);
create index messages_session_idx on messages (session_id, id);

create table feedback (
  id         bigserial primary key,
  session_id uuid not null references sessions(id) on delete cascade,
  job_id     bigint not null references jobs(id),
  signal     text not null check (signal in ('like','dislike','save')),
  created_at timestamptz not null default now(),
  unique (session_id, job_id, signal)
);

create table llm_calls (
  id            bigserial primary key,
  session_id    uuid references sessions(id) on delete set null,
  kind          text not null check (kind in ('chat','embed','verify')),
  model         text not null,
  input_tokens  int,
  output_tokens int,
  latency_ms    int not null,
  ok            boolean not null,
  error         text,
  created_at    timestamptz not null default now()
);

create table tool_calls (
  id         bigserial primary key,
  session_id uuid references sessions(id) on delete set null,
  name       text not null,
  args       jsonb not null,
  n_results  int,
  latency_ms int not null,
  ok         boolean not null,
  created_at timestamptz not null default now()
);
