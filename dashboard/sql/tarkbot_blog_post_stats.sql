-- Per-post blog figures for scripts/blog_performance.py, totalled in Postgres.
-- Applied to the shared Supabase project through the management API; re-run this
-- file to change it. All time: the script divides by each post's age itself.
--
-- One row per /blog/<slug> path:
--   first_view        earliest view, the fallback age when posts.ts has no date
--   views             every view row, visitor known or not
--   visitors          distinct visitors who opened the post
--   reached_download  of those, how many viewed the home page (where the download
--                     button is) after first opening this post
--   clicked_download  of those, how many also clicked download after first opening it
--
-- ponytail: a visitor who reads three posts and then downloads counts as a
-- conversion for all three. Fine for ranking; switch to first-post or last-post
-- credit if the numbers ever get big enough to care which post did it.
create or replace function public.tarkbot_blog_post_stats()
returns json
language sql
stable
security definer
set search_path to 'public'
as $$
  with v as (
    select visitor_id, ts, rtrim(lower(split_part(path, '?', 1)), '/') as p
    from "Tarkbot_analytics_events"
  ),
  firsts as (
    select p, visitor_id, min(ts) as t0
    from v
    where p like '/blog/%' and visitor_id is not null
    group by p, visitor_id
  ),
  per_visitor as (
    select f.p, f.visitor_id,
           exists (select 1 from v h where h.visitor_id = f.visitor_id and h.p = '' and h.ts > f.t0) as reached,
           exists (select 1 from v h where h.visitor_id = f.visitor_id and h.p = '' and h.ts > f.t0)
             and exists (select 1 from "Tarkbot_downloads" d where d.visitor_id = f.visitor_id and d.ts > f.t0) as clicked
    from firsts f
  )
  select coalesce(json_agg(x order by x.path), '[]'::json)
  from (
    select v.p as path,
           min(v.ts) as first_view,
           count(*)::int as views,
           (select count(*) from per_visitor pv where pv.p = v.p)::int as visitors,
           (select count(*) from per_visitor pv where pv.p = v.p and pv.reached)::int as reached_download,
           (select count(*) from per_visitor pv where pv.p = v.p and pv.clicked)::int as clicked_download
    from v
    where v.p like '/blog/%'
    group by v.p
  ) x;
$$;

-- Service key only, same as tarkbot_blog_stats: the project is shared with other
-- products, and a security definer function would otherwise hand these numbers to
-- anyone holding the public anon key.
revoke all on function public.tarkbot_blog_post_stats() from public, anon, authenticated;
grant execute on function public.tarkbot_blog_post_stats() to service_role;
