## v3.09 — Hybrid Watchlist

- Added a dense Daily Movers table above the cards.
- Default sorting is Biggest losers, with gainers/largest move/pinned/ticker options.
- Added Table + Cards, Table only, and Cards only views.
- Reduced card width to five cards per desktop row.
- Tightened card typography and spacing while preserving detail buttons.
- Existing detail chart/edit/fundamental workflow is unchanged.

## v3.08 — Naver Finance Korea data
- Replaced PyKRX with Naver Finance realtime domestic endpoints for KOSPI, KOSDAQ, Samsung Electronics, and SK hynix.
- Reduced Korea quote cache to 60 seconds.
- Kept fail-closed behavior: no Yahoo fallback and no stale substitution.
- Removed the PyKRX dependency.

# Changelog

## v2.05
- Heatmap 종목 클릭 시 상세 패널 표시
- 현재가, 등락률, 시가총액, P/E, 52주 범위, 거래량 표시
- 6개월 가격 차트와 기본 펀더멘털 표시
- Yahoo Finance / TradingView 바로가기
- Heatmap에서 Watchlist 바로 추가
- 클릭 시 한 종목만 확대되던 동작 개선

# Changelog

## v2.03
- Watchlist Snapshot의 Ticker, Price, Day 값을 당일 등락 방향에 따라 색상 표시
- 상승: 빨강 / 하락: 파랑 / 보합: 회색
- 접힌 Investment Card 제목에도 방향 아이콘 표시

## v2.02

- Added always-visible Watchlist Snapshot with price, daily change, AI signal, score, RSI, target, stop, earnings, tag, and memo.
- Added price and daily change directly to each collapsed investment-card title.
- Rebuilt Watchlist as Watchlist Pro.
- Added Supabase cloud synchronization with local JSON fallback.
- Added ticker pinning, tags, target/buy price, stop price and memo/thesis.
- Added BUY ZONE and STOP ALERT states.
- Added search, tag filtering and multiple sorting modes.
- Added automatic migration from the old ticker-only watchlist format.
- Added Supabase SQL setup script and secrets template.


## v2.05
- Watchlist colors now follow U.S. market convention: green up, red down.
- Earnings Radar now reads the Supabase-backed Watchlist Pro records.
- Added robust earnings-date fallbacks for newer yfinance response formats.
- News now uses Yahoo Finance Search first and yfinance as a fallback.
- News and earnings failures now show useful status messages instead of silently returning empty data.

## v2.07
- Added a dedicated US futures panel for S&P 500, Nasdaq 100, Dow and Russell 2000 futures.
- Added VIX and an automatic Risk-On / Risk-Off / Mixed market pulse.
- Added always-visible macro cards for DXY, US 10Y, gold, silver and WTI oil.
- Added a Korea panel for KOSPI, KOSDAQ, USD/KRW, EWY, KORU and SKHY.
- Added responsive morning-dashboard cards and manual-refresh support.

## v3.00 Step 1
- Reduced desktop sidebar width from 270px to 190px and tightened navigation spacing.
- Removed the always-visible sidebar status card and shortened the refresh control.
- Added batched Yahoo Finance quote loading to reduce network round-trips.
- Command Center now reads the user's saved watchlist instead of a hard-coded list.
- Command Center market and sector quotes now load in batches.
- Heatmap now loads all symbols in one batch and uses equal tile sizes.
- Fundamentals are fetched only after selecting a heatmap symbol.
- Updated app branding to v3.00.

## v3.01
- Reduced desktop sidebar width to 168px and tightened navigation spacing.
- Merged AI Advisor and AI Lab into a single AI Center.
- Added AI Center tabs for watchlist-driven radar, single-stock analysis, and comparison.
- Simplified Command Center signal cards from six to four.
- Changed action plan and personal radar to rank the user's saved watchlist dynamically.
- Reduced dashboard card heights for faster scanning and less scrolling.


## v3.04
- Redesigned Today’s Priority cards into a denser two-column layout with larger typography and mini sparklines.
- Added Silver to Macro & Commodities.
- Replaced EWY/KORU/SKHY in Korea Market with Samsung Electronics (005930) and SK hynix (000660).


## v3.07 — Korean market source correction
- Replaced Yahoo Finance for KOSPI, KOSDAQ, Samsung Electronics, and SK hynix with PyKRX/KRX daily closes.
- Added the KRX closing date to the Korea panel.
- Removed stale-data fallback: if KRX is unavailable, the panel shows an em dash instead of a Yahoo value.
- USD/KRW remains sourced separately from Yahoo Finance.
