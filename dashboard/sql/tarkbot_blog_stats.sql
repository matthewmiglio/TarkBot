-- Blog figures for the dashboard, totalled in Postgres so the page gets a few
-- numbers instead of every view row. Applied to the shared Supabase project
-- (rxwdtssnaymiebnhudix) through the management API; re-run this file to change it.
--
-- p_days: only count activity from the last p_days days. null = all time.
--
-- Funnel, counted per visitor (visitor_id is a localStorage uuid that outlives
-- the 30 minute session, so a visitor who reads a post today and downloads
-- tomorrow still counts):
--   landed            visited any /blog page in the window
--   reached_download  then viewed the home page, which holds the download button
--   clicked_download  then clicked download, after landing on the blog
create or replace function public.tarkbot_blog_stats(p_days int default null)
returns json
language sql
stable
security definer
set search_path to 'public'
as $$
  with v as (
    select visitor_id, ts,
           -- '/blog/Foo/?x=1' -> '/blog/foo', and the home page '/' -> ''
           rtrim(lower(split_part(path, '?', 1)), '/') as p
    from "Tarkbot_analytics_events"
    where p_days is null or ts >= now() - make_interval(days => p_days)
  ),
  landed as (
    select visitor_id, min(ts) as t0
    from v
    where visitor_id is not null and (p = '/blog' or p like '/blog/%')
    group by visitor_id
  ),
  reached as (
    select distinct l.visitor_id, l.t0
    from landed l
    join v on v.visitor_id = l.visitor_id and v.p = '' and v.ts > l.t0
  ),
  clicked as (
    select distinct r.visitor_id
    from reached r
    join "Tarkbot_downloads" d on d.visitor_id = r.visitor_id and d.ts > r.t0
  )
  select json_build_object(
    'posts', coalesce((
      select json_agg(x order by x.views desc, x.path)
      from (
        select p as path, count(*)::int as views, count(distinct visitor_id)::int as visitors
        from v
        where p like '/blog/%'
        group by p
      ) x
    ), '[]'::json),
    'funnel', json_build_object(
      'landed', (select count(*) from landed),
      'reached_download', (select count(*) from reached),
      'clicked_download', (select count(*) from clicked)
    )
  );
$$;

-- Service key only. The project is shared with other products, and a security
-- definer function would otherwise let anyone holding the public anon key read
-- these numbers past the tables' RLS.
revoke all on function public.tarkbot_blog_stats(int) from public, anon, authenticated;
grant execute on function public.tarkbot_blog_stats(int) to service_role;
