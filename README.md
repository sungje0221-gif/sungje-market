# Sungje Investment OS v0.94

## v0.94
- Rebuilt Market Heatmap
- Stock, sector rotation, and performance-matrix tabs
- Market breadth and relative-strength ranking
- Core/AI/Power/Korea/Metals comparison matrix

# Sungje Investment OS v7

This is the consolidated near-final build before Charles Schwab API approval and OAuth completion.

## Included

- Command Center with market score, AI score, risk, market overview, opportunities, sector rotation and Today's Playbook
- Global Refresh All Data button and last refreshed time
- Watchlist with positive values in blue and negative values in red
- Advanced charts: 1D, 5D, 1M, 3M, 6M, YTD, 1Y and 5Y
- MA20, MA50, MA100, MA200, Bollinger Bands, Volume, RSI and MACD
- 52-week range, period returns, volume ratio and support/resistance
- Resilient fundamental-data fallbacks and a Fundamental Score
- Index, sector, ETF, AI-theme and personal-watchlist heat maps
- Manual portfolio and Schwab-connected portfolio views
- Portfolio AI Advisor
- Buy Planner
- Earnings Radar
- News & Briefing
- Trading Journal
- Schwab OAuth connection page
- Schwab-first quote adapter with automatic Yahoo Finance fallback

## Schwab behavior

Before Schwab approval and OAuth connection:
- Quotes and fundamentals use Yahoo Finance.
- Schwab portfolio pages remain disconnected.

After Schwab approval and OAuth connection:
- Account balances and positions come from Schwab.
- The quote adapter attempts Schwab Market Data first, then falls back to Yahoo Finance.
- A later update may be required if Schwab changes endpoint permissions or streaming requirements.

## Streamlit deployment

Upload this project to GitHub, set `app.py` as the entry point, then add:

```toml
[schwab]
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
redirect_uri = "YOUR_CALLBACK_URL"
```

to Streamlit Cloud Secrets after Schwab approves the app.

Never commit real Schwab credentials or tokens to GitHub.

## Investment OS 1.0 — Part 1A

This build starts the Investment OS 1.0 redesign:

- New grouped navigation sidebar
- New OS 1.0 visual system and responsive layout
- Rebuilt Command Center hierarchy
- Personalized opportunity list including SKHY and VXF
- Safer dashboard fallbacks when market-data calls fail

## v0.92 Command Center Upgrade

- Compact terminal-style market header
- Six live signal cards with one-month sparklines
- BUY / HOLD / AVOID / WATCH playbook
- Personal watchlist radar for VOO, VXF, GOOGL, CEG, SKHY, KORU, QQQM and SMH
- Market regime indicator and redesigned AI decision context
- Responsive desktop/tablet layout
