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
