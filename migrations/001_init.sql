create extension if not exists vector;

create table companies (
  id   bigserial primary key,
  name text not null unique
);

create table jobs (
  id               bigserial primary key,
  source           text not null check (source in ('greenhouse','lever','remoteok')),
  board            text not null,              -- which board it came from; closing works per board
  source_job_id    text not null,
  company_id       bigint not null references companies(id),
  title            text not null,
  location_raw     text,
  country_code     text,                       -- rule-based, may be null
  is_remote        boolean,                    -- null = source did not say
  level            text not null default 'unknown'
                   check (level in ('intern','entry','mid','senior','unknown')),
  description_text text not null,
  apply_url        text not null,
  source_url       text not null,
  posted_at        timestamptz,
  content_hash     text not null,
  raw              jsonb not null,             -- original item, for debugging
  status           text not null default 'open' check (status in ('open','closed')),
  first_seen_at    timestamptz not null default now(),
  last_seen_at     timestamptz not null default now(),
  closed_at        timestamptz,
  embedding        vector(768),
  embedding_model  text,
  embedding_stale  boolean not null default true,
  fts tsvector generated always as (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description_text, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(location_raw, '')), 'C')
  ) stored,
  unique (source, source_job_id)
);

create index jobs_fts_idx       on jobs using gin (fts);
create index jobs_open_idx      on jobs (company_id) where status = 'open';
create index jobs_board_idx     on jobs (source, board) where status = 'open';
create index jobs_embedding_idx on jobs using hnsw (embedding vector_cosine_ops);

create table ingest_runs (
  id           bigserial primary key,
  source       text not null,
  board        text not null,
  started_at   timestamptz not null,
  finished_at  timestamptz,
  fetched      int not null default 0,
  new_jobs     int not null default 0,
  changed_jobs int not null default 0,
  closed_jobs  int not null default 0,
  error        text
);
