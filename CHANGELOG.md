# v3.14 Schwab CSV Import Fix

- Detects the real Schwab header row below the account report title.
- Supports UTF-8/UTF-8-SIG/Windows-1252 CSV files.
- Removes empty rows, totals, and cash rows.
- Adds robust Symbol, Quantity, and Cost Basis mapping.
- Supports both per-share average cost and total cost basis conversion.
- Shows an import preview before saving.
