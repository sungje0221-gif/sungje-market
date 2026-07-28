# v3.13 Flexible Charts

- Separated chart range and candle interval controls.
- Range choices: 1D, 5D, 1M, 3M, 6M, 1Y, 5Y.
- Candle choices change to valid intervals for the selected range.
- Defaults now use 1m for 1D, 5m for 5D, and 60m for 1M so short-range charts are not sparse.
- Uses actual Yahoo Finance OHLCV data only; no generated candles.
