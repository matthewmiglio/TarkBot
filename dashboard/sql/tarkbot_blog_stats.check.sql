-- Self-check for tarkbot_blog_stats. Inserts fake visitors inside a transaction,
-- asserts the counts, then rolls back, so nothing is left in the tables.
-- Run it in the Supabase SQL editor; it raises an error if a count is wrong.
begin;

-- Fake rows are dated in the future so no real visitor can match them, and the
-- assertions compare against the counts from before the inserts.
create temp table before as select public.tarkbot_blog_stats(null) as s;

insert into "Tarkbot_analytics_events" (ts, path, visitor_id) values
  -- a: blog -> home -> download: counts at every step
  (now() + interval '1 day',  '/blog/scav-case-loot', 'check-a'),
  (now() + interval '1 day 1 minute', '/', 'check-a'),
  -- b: blog -> home, never downloads
  (now() + interval '1 day',  '/blog/scav-case-loot/', 'check-b'),
  (now() + interval '1 day 1 minute', '/', 'check-b'),
  -- c: home BEFORE the blog only: lands, but never reaches the download page after
  (now() + interval '1 day',  '/', 'check-c'),
  (now() + interval '1 day 1 minute', '/blog', 'check-c'),
  -- d: never touches the blog: not in the funnel at all
  (now() + interval '1 day',  '/', 'check-d');

insert into "Tarkbot_downloads" (ts, visitor_id) values
  (now() + interval '1 day 2 minutes', 'check-a'),
  (now() + interval '1 day 2 minutes', 'check-d');

do $$
declare
  b json := (select s from before);
  a json := public.tarkbot_blog_stats(null);
  d_landed int := (a->'funnel'->>'landed')::int - (b->'funnel'->>'landed')::int;
  d_reached int := (a->'funnel'->>'reached_download')::int - (b->'funnel'->>'reached_download')::int;
  d_clicked int := (a->'funnel'->>'clicked_download')::int - (b->'funnel'->>'clicked_download')::int;
  scav int := coalesce((select (x->>'views')::int from json_array_elements(a->'posts') x
                        where x->>'path' = '/blog/scav-case-loot'), 0)
            - coalesce((select (x->>'views')::int from json_array_elements(b->'posts') x
                        where x->>'path' = '/blog/scav-case-loot'), 0);
begin
  assert d_landed = 3, format('landed went up by %s, expected 3 (a, b, c)', d_landed);
  assert d_reached = 2, format('reached_download went up by %s, expected 2 (a, b)', d_reached);
  assert d_clicked = 1, format('clicked_download went up by %s, expected 1 (a)', d_clicked);
  assert scav = 2, format('scav post views went up by %s, expected 2 (trailing slash merged)', scav);
  raise notice 'tarkbot_blog_stats check passed';
end $$;

rollback;
