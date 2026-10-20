-- Resume Screening AI — initial schema
-- Run in the Supabase SQL editor (its search_path includes the `extensions` schema).

-- ============ Extensions ============
create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto with schema extensions;  -- gen_random_uuid is built in on PG13+, harmless

-- ============ Helper: updated_at trigger ============
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- ============ resumes (one row per PDF; each user's library = all rows with their owner_id) ============
create table public.resumes (
  id                     uuid primary key default gen_random_uuid(),
  owner_id               uuid not null references auth.users(id) on delete cascade,
  original_filename      text not null,
  file_path              text not null,            -- Storage path: {owner_id}/{id}.pdf
  file_size_bytes        integer not null,
  file_hash              text not null,            -- SHA-256 hex of file bytes
  page_count             integer,
  status                 text not null default 'pending'
                           check (status in ('pending','processing','done','failed')),
  error_message          text,
  processing_started_at  timestamptz,
  -- extracted / structured fields
  candidate_name         text,
  email                  text,
  phone                  text,
  location               text,
  links                  jsonb not null default '{}'::jsonb,   -- {linkedin, github, portfolio}
  headline               text,
  summary                text,
  skills                 text[] not null default '{}',         -- NORMALIZED (lowercase, alias-mapped)
  education              jsonb not null default '[]'::jsonb,
  certifications         text[] not null default '{}',
  projects               jsonb not null default '[]'::jsonb,
  total_experience_months integer,                              -- computed in code; 0 for freshers; non-null when done
  parse_warnings         text[] not null default '{}',
  raw_text               text,                                  -- extracted text (kept to allow re-processing without re-upload)
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),
  unique (owner_id, file_hash)                                  -- dedupe per user library
);
create index resumes_owner_status_idx    on public.resumes(owner_id, status);
create index resumes_owner_created_idx   on public.resumes(owner_id, created_at desc);
create index resumes_pending_idx         on public.resumes(created_at) where status = 'pending';
create index resumes_skills_gin_idx      on public.resumes using gin (skills);
create trigger trg_resumes_updated before update on public.resumes
  for each row execute function public.set_updated_at();

-- ============ experiences (one row per job) ============
create table public.experiences (
  id              uuid primary key default gen_random_uuid(),
  resume_id       uuid not null references public.resumes(id) on delete cascade,
  owner_id        uuid not null references auth.users(id) on delete cascade,
  position        integer not null,                 -- order as it appears in the resume
  company         text,
  title           text,
  employment_type text not null default 'unknown'
                    check (employment_type in ('full_time','part_time','internship','contract','freelance','unknown')),
  start_date      text,                             -- 'YYYY-MM' or 'YYYY' as extracted
  end_date        text,
  is_current      boolean not null default false,
  location        text,
  description     text
);
create index experiences_resume_idx on public.experiences(resume_id);

-- ============ resume_chunks (embeddings) ============
create table public.resume_chunks (
  id          uuid primary key default gen_random_uuid(),
  resume_id   uuid not null references public.resumes(id) on delete cascade,
  owner_id    uuid not null references auth.users(id) on delete cascade,     -- denormalized for single-query isolation
  chunk_index integer not null,
  section     text not null check (section in ('summary','experience','project','education','certification','raw')),
  content     text not null,
  embedding   vector(384) not null
);
create index resume_chunks_resume_idx on public.resume_chunks(resume_id);
create index resume_chunks_owner_idx  on public.resume_chunks(owner_id);
create index resume_chunks_embedding_idx
  on public.resume_chunks using hnsw (embedding vector_cosine_ops);

-- ============ Row Level Security (defense in depth; backend uses service role) ============
alter table public.resumes       enable row level security;
alter table public.experiences   enable row level security;
alter table public.resume_chunks enable row level security;

create policy resumes_owner       on public.resumes       for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy experiences_owner   on public.experiences   for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy resume_chunks_owner on public.resume_chunks for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- ============ Storage bucket (private, 1 MB per file) ============
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('resumes', 'resumes', false, 1048576, array['application/pdf'])
on conflict (id) do nothing;
-- No storage.objects policies are created: only the backend (service role) touches the bucket.

-- ============ Function: atomically claim the next pending resume ============
create or replace function public.claim_next_resume()
returns setof public.resumes
language plpgsql
set search_path = public
as $$
declare v_id uuid;
begin
  select id into v_id
  from public.resumes
  where status = 'pending'
  order by created_at
  for update skip locked
  limit 1;

  if v_id is null then
    return;
  end if;

  return query
    update public.resumes
       set status = 'processing', processing_started_at = now(), error_message = null
     where id = v_id
    returning *;
end $$;

-- ============ Function: hybrid retrieval (filters + vector similarity) over one user's library ============
create or replace function public.search_resumes(
  p_owner_id                uuid,
  p_query_embedding         vector(384),
  p_min_experience_months   integer default null,
  p_max_experience_months   integer default null,
  p_required_skills         text[]  default null,
  p_location                text    default null,
  p_limit                   integer default 15
)
returns table (resume_id uuid, score double precision)
language sql
stable
set search_path = public, extensions
as $$
  select c.resume_id,
         max(1 - (c.embedding <=> p_query_embedding))::double precision as score
  from public.resume_chunks c
  join public.resumes r on r.id = c.resume_id
  where c.owner_id = p_owner_id
    and r.owner_id = p_owner_id
    and r.status   = 'done'
    and (p_min_experience_months is null or r.total_experience_months >= p_min_experience_months)
    and (p_max_experience_months is null or r.total_experience_months <= p_max_experience_months)
    and (p_required_skills is null or cardinality(p_required_skills) = 0 or r.skills @> p_required_skills)
    and (p_location is null or r.location ilike '%' || p_location || '%')
  group by c.resume_id
  order by score desc
  limit p_limit;
$$;

-- ============ Function: top matching chunks per resume (for verification + snippets) ============
create or replace function public.get_top_chunks(
  p_owner_id        uuid,
  p_resume_ids      uuid[],
  p_query_embedding vector(384),
  p_per_resume      integer default 3
)
returns table (resume_id uuid, chunk_id uuid, section text, content text, score double precision)
language sql
stable
set search_path = public, extensions
as $$
  select t.resume_id, t.chunk_id, t.section, t.content, t.score
  from (
    select c.resume_id,
           c.id as chunk_id,
           c.section,
           c.content,
           (1 - (c.embedding <=> p_query_embedding))::double precision as score,
           row_number() over (partition by c.resume_id order by c.embedding <=> p_query_embedding) as rn
    from public.resume_chunks c
    where c.owner_id = p_owner_id
      and c.resume_id = any(p_resume_ids)
  ) t
  where t.rn <= p_per_resume
  order by t.resume_id, t.rn;
$$;

-- ============ Lock RPC functions to the service role ============
revoke all on function public.claim_next_resume()                                                  from public, anon, authenticated;
revoke all on function public.search_resumes(uuid, vector, integer, integer, text[], text, integer) from public, anon, authenticated;
revoke all on function public.get_top_chunks(uuid, uuid[], vector, integer)                         from public, anon, authenticated;
grant execute on function public.claim_next_resume()                                                to service_role;
grant execute on function public.search_resumes(uuid, vector, integer, integer, text[], text, integer) to service_role;
grant execute on function public.get_top_chunks(uuid, uuid[], vector, integer)                      to service_role;
