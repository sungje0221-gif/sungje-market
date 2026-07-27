# Sungje Investment OS v1.00

개인 투자 대시보드의 완결판입니다. Streamlit Cloud에서 실행하도록 구성되어 있습니다.

## 주요 기능

- Command Center: 주요 시장 지표와 개인 관심 종목 요약
- Markets / Heatmap: 지수, 섹터, 종목 상대강도 및 트리맵
- Watchlist: 관심 종목 추적
- Portfolio: Schwab 연결, 수동 포트폴리오, CSV 가져오기
- AI Advisor: 추세, 이동평균, RSI 기반 BUY / HOLD / WAIT / TRIM / SELL 신호
- Buy Planner: 분할매수 계획
- Earnings / News / Journal
- Settings: 개인 설정, 데이터 백업, 시스템 진단
- 모바일 반응형 화면

## 설치

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 배포

1. 이 폴더의 내용을 GitHub 저장소에 업로드합니다.
2. Streamlit Community Cloud에서 `app.py`를 메인 파일로 지정합니다.
3. Schwab을 사용할 경우 `.streamlit/secrets.toml.example`을 참고해 Secrets를 등록합니다.

## 개인 데이터

`data/` 폴더에 다음 파일이 저장됩니다.

- `portfolio.csv`
- `watchlist.json`
- `journal.csv`
- `settings.json`

Settings 페이지에서 개인 데이터 ZIP 백업을 내려받을 수 있습니다.

## 주의

이 앱의 신호는 규칙 기반 참고자료이며 투자 자문이 아닙니다. Yahoo Finance 데이터는 지연되거나 누락될 수 있습니다.
