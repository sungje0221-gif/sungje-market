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
