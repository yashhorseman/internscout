-- Leave free space in each page. Then updating only last_seen_at (which no index
-- covers) can stay on the same page and skips rewriting any index entry.
alter table jobs set (fillfactor = 85);
