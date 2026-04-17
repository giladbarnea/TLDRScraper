create or replace function public.patch_daily_article(
  target_date date,
  article_url text,
  article_patch jsonb,
  expected_updated_at text
)
returns table (
  conflict boolean,
  payload jsonb,
  updated_at text
)
language plpgsql
as $$
declare
  current_payload jsonb;
  current_updated_at text;
  current_updated_at_timestamp timestamptz;
  expected_updated_at_timestamp timestamptz;
  article_index integer;
  patch_key text;
  patch_value jsonb;
  patched_payload jsonb;
  next_updated_at text;
begin
  expected_updated_at_timestamp := expected_updated_at::timestamptz;
  select
    daily_cache.payload,
    to_char(
      coalesce((daily_cache.payload->>'storage_updated_at')::timestamptz, daily_cache.cached_at) at time zone 'UTC',
      'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"'
    ),
    coalesce((daily_cache.payload->>'storage_updated_at')::timestamptz, daily_cache.cached_at)
  into current_payload, current_updated_at, current_updated_at_timestamp
  from daily_cache
  where daily_cache.date = target_date;

  if current_payload is null then
    raise exception 'daily_cache row not found for date %', target_date;
  end if;

  if current_updated_at_timestamp <> expected_updated_at_timestamp then
    return query
      select true, current_payload, current_updated_at;
    return;
  end if;

  select (article_entry.ordinality - 1)::integer
  into article_index
  from jsonb_array_elements(current_payload->'articles') with ordinality as article_entry(article, ordinality)
  where article_entry.article->>'url' = article_url
  limit 1;

  if article_index is null then
    raise exception 'article not found for url %', article_url;
  end if;

  patched_payload := current_payload;
  for patch_key, patch_value in select key, value from jsonb_each(article_patch)
  loop
    patched_payload := jsonb_set(
      patched_payload,
      array['articles', article_index::text, patch_key],
      patch_value,
      true
    );
  end loop;

  next_updated_at := to_char(
    now() at time zone 'UTC',
    'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"'
  );
  patched_payload := jsonb_set(
    patched_payload,
    '{storage_updated_at}',
    to_jsonb(next_updated_at),
    true
  );

  update daily_cache
  set payload = patched_payload
  where
    daily_cache.date = target_date
    and coalesce((daily_cache.payload->>'storage_updated_at')::timestamptz, daily_cache.cached_at)
      = expected_updated_at_timestamp;

  if found then
    return query
      select false, patched_payload, next_updated_at;
    return;
  end if;

  select
    daily_cache.payload,
    to_char(
      coalesce((daily_cache.payload->>'storage_updated_at')::timestamptz, daily_cache.cached_at) at time zone 'UTC',
      'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"'
    )
  into current_payload, current_updated_at
  from daily_cache
  where daily_cache.date = target_date;

  return query
    select true, current_payload, current_updated_at;
end;
$$;
