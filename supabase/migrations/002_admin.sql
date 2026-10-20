-- Resume Screening AI — admin approval + admin panel
-- Run in the Supabase SQL editor AFTER 001_init.sql.

-- ============ profiles (one row per auth user: role + approval status) ============
create table public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  email        text,
  role         text not null default 'user'    check (role in ('user','admin')),
  status       text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  reviewed_at  timestamptz,
  reviewed_by  uuid references auth.users(id) on delete set null
);
create index profiles_status_idx on public.profiles(status, created_at desc);
create trigger trg_profiles_updated before update on public.profiles
  for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;
-- Defense in depth: a user may read only their own profile; only the backend (service role) writes.
create policy profiles_self_read on public.profiles for select using (id = auth.uid());

-- ============ New sign-ups get a pending profile automatically ============
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email) values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Keep the stored email in sync if a user changes it.
create or replace function public.handle_user_email_change()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.profiles set email = new.email where id = new.id;
  return new;
end $$;

create trigger on_auth_user_email_changed
  after update of email on auth.users
  for each row when (old.email is distinct from new.email)
  execute function public.handle_user_email_change();

-- ============ Backfill users that existed before this migration ============
-- Existing users already had access, so they are approved.
insert into public.profiles (id, email, status, reviewed_at)
select u.id, u.email, 'approved', now()
from auth.users u
on conflict (id) do nothing;

-- ============ First admin ============
update public.profiles
   set role = 'admin', status = 'approved', reviewed_at = now()
 where lower(email) = lower('official.pranavsinhrajput@gmail.com');

-- ============ Admin listing: profiles + last sign-in + per-user resume counts ============
create or replace function public.admin_list_users(p_status text default null)
returns table (
  id              uuid,
  email           text,
  role            text,
  status          text,
  created_at      timestamptz,
  reviewed_at     timestamptz,
  last_sign_in_at timestamptz,
  resume_count    bigint,
  done_count      bigint
)
language sql
stable
security definer
set search_path = public
as $$
  select p.id, p.email, p.role, p.status, p.created_at, p.reviewed_at, u.last_sign_in_at,
         coalesce(rc.total, 0) as resume_count,
         coalesce(rc.done, 0)  as done_count
  from public.profiles p
  left join auth.users u on u.id = p.id
  left join (
    select owner_id, count(*) as total, count(*) filter (where status = 'done') as done
    from public.resumes
    group by owner_id
  ) rc on rc.owner_id = p.id
  where p_status is null or p.status = p_status
  order by p.created_at desc;
$$;

revoke all on function public.admin_list_users(text) from public, anon, authenticated;
grant execute on function public.admin_list_users(text) to service_role;
revoke all on function public.handle_new_user() from public, anon, authenticated;
revoke all on function public.handle_user_email_change() from public, anon, authenticated;
