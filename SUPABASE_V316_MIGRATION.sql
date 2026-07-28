-- Run this once in Supabase SQL Editor for Investment OS v3.16.
alter table public.portfolio_positions add column if not exists sector text not null default 'Unknown';
alter table public.portfolio_positions add column if not exists industry text not null default 'Unknown';

create table if not exists public.portfolio_settings (
  profile_id text primary key,
  cash numeric not null default 0,
  buying_power numeric not null default 0,
  target_cash_pct numeric not null default 20,
  updated_at timestamptz not null default now()
);
alter table public.portfolio_settings enable row level security;
drop policy if exists "portfolio settings read" on public.portfolio_settings;
drop policy if exists "portfolio settings insert" on public.portfolio_settings;
drop policy if exists "portfolio settings update" on public.portfolio_settings;
drop policy if exists "portfolio settings delete" on public.portfolio_settings;
create policy "portfolio settings read" on public.portfolio_settings for select using (true);
create policy "portfolio settings insert" on public.portfolio_settings for insert with check (true);
create policy "portfolio settings update" on public.portfolio_settings for update using (true) with check (true);
create policy "portfolio settings delete" on public.portfolio_settings for delete using (true);
