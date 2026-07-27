# Sungje Investment OS v2.03

## Watchlist Pro

- Supabase cloud sync across PC and mobile
- Local JSON fallback when Supabase is not configured or temporarily unavailable
- Pin, tag, target/buy price, stop price, memo/investment thesis
- BUY ZONE and STOP ALERT status
- Search, filter, sorting and advanced chart

## Supabase setup

1. Create a free Supabase project.
2. Open SQL Editor and run `SUPABASE_SETUP.sql`.
3. In Streamlit Cloud, open App settings → Secrets.
4. Copy the `[supabase]` block from `.streamlit/secrets.toml.example` and enter your project URL and anon key.
5. Reboot the app. Existing local watchlist entries are uploaded automatically when the cloud table is empty.

Never commit the real `.streamlit/secrets.toml` file.
