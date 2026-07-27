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
