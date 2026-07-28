# Investment OS v3.14

This build fixes Charles Schwab Positions CSV imports whose first line is an account report title rather than the actual column header.

## v3.15 Portfolio setup
Run `SUPABASE_SETUP.sql` once in Supabase SQL Editor. Add optional `portfolio_table = "portfolio_positions"` under `[supabase]` in Streamlit secrets. The same `profile_id` used by Watchlist is used for Portfolio cloud sync.
