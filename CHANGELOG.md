
## v3.18.3
- Restored click-to-open ticker details on the market heatmap.
- Added chart ranges: 1D, 5D, 1M, 3M, 6M, 1Y, 5Y.
- Added candle intervals from 1-minute through 1-day, constrained to Yahoo-supported range/interval combinations.
- Reused the full OHLCV advanced chart with volume and indicators.
- Preserved the corrected daily percentage calculation from v3.18.2.
# v3.18.1
- Clean distribution: removed Python bytecode/cache artifacts.
- Fixed outer heatmap caches to 20 seconds so live quote refresh is not held for 5 minutes.
- Kept static treemap behavior and compact ticker detail selector.

# v3.15 Portfolio Cloud & Health
- Added Supabase-backed portfolio_positions storage keyed by profile/account/ticker.
- Added total value, cost, P/L, today's P/L, risk and diversification summary.
- Added holdings and category allocation, concentration checks, best/worst position notes.
- Added position replacement/editing and deletion.
- CSV imports now save through the same cloud storage layer.

## v3.17 - Transactions & FIFO Realized P/L
- Added a Transactions tab to Portfolio.
- Added BUY/SELL entry with account, date, ticker, shares, price, fee, and notes.
- Added FIFO lot matching for realized profit and loss.
- Added opening-position cost-basis fallback for sells without complete buy history.
- Added transaction history, per-ticker realized P/L, win rate, and delete controls.
- Added optional synchronization with Manual Portfolio holdings.
- Added local transaction ledger at data/transactions.csv.

## v3.18 — Live Heatmap Fix
- Replaced daily-history percentage calculations with live previous-close quote fields.
- Added Schwab batch quote priority with Yahoo live fallback.
- Added market-cap tile sizing.
- Disabled treemap leaf zoom and added compact detail selection.

## v3.18.2
- Heatmap daily change now uses Yahoo chart metadata (`regularMarketPrice` / `chartPreviousClose`) from the same session.
- Schwab percentages are recalculated from current price and previous close instead of trusting a potentially mismatched percentage field.
- All treemaps are static to prevent a clicked tile from expanding to fill the chart.
- Removed runtime cache artifacts from the distribution ZIP.

## 3.18.5
- Heatmap tiles use market-cap Weight values.
- Replaced native Plotly selection with click-only events so clicking updates details without changing treemap layout.
