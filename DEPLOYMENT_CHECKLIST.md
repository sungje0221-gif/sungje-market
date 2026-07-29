# v3.15 Deployment Checklist
1. Run `SUPABASE_SETUP.sql` in the Supabase SQL Editor.
2. Confirm Streamlit secrets contain `[supabase]` with `url`, `key`, and a private `profile_id`.
3. Optional: add `portfolio_table = "portfolio_positions"`.
4. Deploy the project root and verify sidebar version is v3.15.
5. Open Portfolio > CSV Import, import positions, then verify Manual Portfolio shows `Cloud Sync · Supabase`.
6. Open the app in another browser/device using the same deployment; positions should reload from Supabase.
