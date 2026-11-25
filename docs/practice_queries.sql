-- 1. Open jobs per source and company
select j.source, c.name as company, count(*) as open_jobs
from jobs j join companies c on c.id = j.company_id
where j.status = 'open'
group by j.source, c.name
order by open_jobs desc;

-- 2. Ten most recently first-seen open intern/entry jobs
select j.id, c.name as company, j.title, j.location_raw, j.first_seen_at
from jobs j join companies c on c.id = j.company_id
where j.status = 'open' and j.level in ('intern', 'entry')
order by j.first_seen_at desc, j.id desc
limit 10;

-- 3. Open jobs not seen for 3 days (empty after a clean run, except the Remote OK rolling feed)
select id, source, board, title, last_seen_at
from jobs
where status = 'open' and last_seen_at < now() - interval '3 days';

-- 4. Ranked keyword search; should use jobs_fts_idx
explain analyze
select id, title, ts_rank(fts, q) as score
from jobs, websearch_to_tsquery('english', 'python backend intern') q
where fts @@ q and status = 'open'
order by score desc
limit 10;

-- 5. What each ingest run did
select started_at, source, board, fetched, new_jobs, changed_jobs, closed_jobs, error
from ingest_runs
order by started_at desc, board;
