create or replace function public.patch_daily_payload(
  target_date date,
  payload_patch jsonb,
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

  patched_payload := current_payload;
  for patch_key, patch_value in select key, value from jsonb_each(payload_patch)
  loop
    patched_payload := jsonb_set(
      patched_payload,
      array[patch_key],
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
