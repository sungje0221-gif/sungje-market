create table if not exists public.watchlist_items (
  profile_id text not null,
  ticker text not null,
  pinned boolean not null default false,
  target_price numeric,
  stop_price numeric,
  tag text not null default 'Watch',
  memo text not null default '',
  updated_at timestamptz not null default now(),
  primary key (profile_id, ticker)
);

alter table public.watchlist_items enable row level security;

-- This app uses a private, hard-to-guess profile_id with the anon key.
-- For a personal app, these policies permit REST access through that key.
create policy "watchlist read" on public.watchlist_items for select using (true);
create policy "watchlist insert" on public.watchlist_items for insert with check (true);
create policy "watchlist update" on public.watchlist_items for update using (true) with check (true);
create policy "watchlist delete" on public.watchlist_items for delete using (true);

create table if not exists public.portfolio_positions (
  profile_id text not null,
  account text not null default 'Taxable',
  ticker text not null,
  shares numeric not null,
  avg_cost numeric not null default 0,
  category text not null default 'Other',
  updated_at timestamptz not null default now(),
  primary key (profile_id, account, ticker)
);
alter table public.portfolio_positions enable row level security;
create policy "portfolio read" on public.portfolio_positions for select using (true);
create policy "portfolio insert" on public.portfolio_positions for insert with check (true);
create policy "portfolio update" on public.portfolio_positions for update using (true) with check (true);
create policy "portfolio delete" on public.portfolio_positions for delete using (true);

-- v3.16 Portfolio management migration
alter table public.portfolio_positions add column if not exists sector text not null default 'Unknown';
alter table public.portfolio_positions add column if not exists industry text not null default 'Unknown';

-- Schwab OAuth token storage. Local files don't survive a Streamlit Cloud
-- container restart, so the connection token lives here instead -- one row
-- per profile_id, holding the whole token payload (access/refresh token,
-- expiry, etc.) as jsonb.
create table if not exists public.schwab_tokens (
  profile_id text primary key,
  token jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.schwab_tokens enable row level security;
create policy "schwab_tokens read" on public.schwab_tokens for select using (true);
create policy "schwab_tokens insert" on public.schwab_tokens for insert with check (true);
create policy "schwab_tokens update" on public.schwab_tokens for update using (true) with check (true);
create policy "schwab_tokens delete" on public.schwab_tokens for delete using (true);

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
