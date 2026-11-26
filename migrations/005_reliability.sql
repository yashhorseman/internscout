-- one row per API request that does real work; what /admin/stats is computed from
create table requests (
  id           bigserial primary key,
  request_id   text not null,
  route        text not null,
  status       int not null,
  latency_ms   int not null,
  session_id   uuid references sessions(id) on delete set null,
  outcome      text,              -- agent turns only
  repairs      int,
  claims_removed int,
  is_test      boolean not null default false,
  created_at   timestamptz not null default now()
);
create index requests_created_idx on requests (created_at);

alter table llm_calls add column request_id text;
alter table tool_calls add column request_id text;
alter table sessions add column is_test boolean not null default false;

-- a click on a card's Apply link, the nearest we have to "this was useful"
alter table feedback drop constraint feedback_signal_check;
alter table feedback add constraint feedback_signal_check
  check (signal in ('like', 'dislike', 'save', 'apply_click'));
