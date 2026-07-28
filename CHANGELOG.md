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
