# Sungje Market Command Center 2.0

개인용 주식시장 웹앱입니다.

## 들어간 기능

- S&P 500, Nasdaq, Russell 2000, VIX, 미국 10년물, 달러, 유가, 금·은, KOSPI, USD/KRW
- 개인 Watchlist 등락 레이더와 간단한 신호
- 캔들/라인 차트, 이동평균, 종목 간 상대수익률 비교
- 보유수량·평균단가·계좌·테마 저장
- 테마별 비중, 집중도 경고, 추정 당일 손익
- Finnhub API 키 사용 시 실적 캘린더와 종목 뉴스
- SKHY와 한국 SK하이닉스 본주의 환산가·프리미엄 계산
- 실적 발표 후 3단계 분할매수 및 평균단가 계산

## Windows에서 바로 보는 방법

1. ZIP 압축을 풉니다.
2. 폴더 주소창에 `cmd`를 입력하고 Enter.
3. 아래를 차례로 입력합니다.

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

브라우저가 자동으로 열립니다. 다음부터는 `run_windows.bat`를 더블클릭하면 됩니다.

## 인터넷 주소로 만들어 어디서나 보는 방법

1. GitHub에서 새 저장소를 만듭니다.
2. ZIP 안의 파일을 저장소 최상단에 전부 올립니다. ZIP 자체를 올리는 것이 아닙니다.
3. Streamlit Community Cloud에서 **Create app**을 누릅니다.
4. 저장소와 `main` 브랜치를 선택합니다.
5. Main file path에 `app.py`를 입력하고 Deploy합니다.
6. 만들어진 `https://...streamlit.app` 주소를 PC, 태블릿, 휴대폰에서 엽니다.

### 휴대폰에서 앱처럼 사용

- Android Chrome: 오른쪽 위 `⋮` → **홈 화면에 추가** 또는 **앱 설치**
- iPhone/iPad Safari: 공유 버튼 → **홈 화면에 추가**

## Finnhub 뉴스/실적 기능

Finnhub 무료 API 키를 만든 뒤 Streamlit Cloud의 App settings → Secrets에 아래처럼 넣습니다.

```toml
FINNHUB_API_KEY = "본인의_키"
```

키가 없어도 시장, 차트, 포트폴리오, SKHY 패리티, 매수계획 기능은 작동합니다.

## SKHY 계산 주의

`SKHY 패리티` 화면의 **ADR 1주당 한국 본주 수**는 반드시 공식 전환 조건을 확인해 직접 입력해야 합니다. 기본값은 계산 예시일 뿐입니다.

## 데이터 주의

yfinance는 Yahoo Finance 공개 데이터를 불러오는 비공식 오픈소스 도구입니다. 무료 데이터는 지연·누락·티커 미지원이 있을 수 있습니다. 이 앱에는 주문 기능이 없습니다.
