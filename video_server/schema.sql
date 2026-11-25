-- Video server database (Supabase / any Postgres 13+).
-- Paste into Supabase SQL editor once. See docs/video-plan.md §3.

create table invite_keys (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,                 -- who it belongs to
  key_hash      text not null unique,          -- sha256 hex of the invite key, never the key itself
  monthly_quota int  not null default 30,      -- raise per person here
  active        boolean not null default true, -- set false to revoke
  created_at    timestamptz not null default now()
);

create table video_jobs (
  id             uuid primary key default gen_random_uuid(),
  key_id         uuid not null references invite_keys(id),
  status         text not null default 'reserved'
                 check (status in ('reserved', 'done', 'failed')),
  prompt         text not null,
  status_url     text,      -- fal queue URLs returned on submit
  response_url   text,
  video_url      text,
  error          text,
  created_at     timestamptz not null default now(),
  finished_at    timestamptz
);

create index on video_jobs (key_id, created_at);

-- Supabase exposes tables over a public REST API. RLS on + no policies
-- = only the service key (used by the video server) can touch them.
alter table invite_keys enable row level security;
alter table video_jobs  enable row level security;

-- Clips this calendar month that still count (anything not failed).
create function clips_used(p_key_id uuid) returns int language sql stable as $$
  select count(*)::int from video_jobs
   where key_id = p_key_id and status <> 'failed'
     and created_at >= date_trunc('month', now());
$$;

-- Atomically check quota and reserve one clip slot. Returns the new job id.
-- Raises 'invalid_key' or 'quota_exceeded'.
create function reserve_clip(p_key_hash text, p_prompt text)
returns uuid language plpgsql as $$
declare k invite_keys; job uuid;
begin
  select * into k from invite_keys
   where key_hash = p_key_hash and active
   for update;                                   -- serialises concurrent requests per user
  if not found then raise exception 'invalid_key'; end if;
  if clips_used(k.id) >= k.monthly_quota then raise exception 'quota_exceeded'; end if;

  insert into video_jobs (key_id, prompt) values (k.id, p_prompt) returning id into job;
  return job;
end $$;

-- Quota badge: name, used, quota for one key (empty if key invalid).
create function quota_status(p_key_hash text)
returns table (name text, used int, quota int) language sql stable as $$
  select k.name, clips_used(k.id), k.monthly_quota
    from invite_keys k where k.key_hash = p_key_hash and k.active;
$$;

-- One job, only if it belongs to this key (empty otherwise).
create function get_job(p_key_hash text, p_job uuid)
returns setof video_jobs language sql stable as $$
  select j.* from video_jobs j join invite_keys k on k.id = j.key_id
   where j.id = p_job and k.key_hash = p_key_hash and k.active;
$$;
