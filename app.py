from __future__ import annotations
import json, math, os
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

ROOT=Path(__file__).parent; DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
SETTINGS=DATA/'settings.json'; PORTFOLIO=DATA/'portfolio.csv'; PLAN=DATA/'trade_plan.csv'
st.set_page_config(page_title='Sungje Market Command Center',page_icon='📈',layout='wide')

DEFAULT={
 'watchlist':['SKHY','000660.KS','KORU','EWY','GOOGL','MSFT','META','AMZN','AAPL','AVGO','MU','VRT','ETN','ANET','ALAB','GLW','SMH','SPCX','RKLB','OKLO','SLV','XLV','ITA','SCHD','CEG','VST'],
 'market':{'S&P 500':'^GSPC','Nasdaq':'^IXIC','Russell 2000':'^RUT','VIX':'^VIX','US 10Y':'^TNX','Dollar':'DX-Y.NYB','WTI':'CL=F','Gold':'GC=F','Silver':'SI=F','Bitcoin':'BTC-USD','KOSPI':'^KS11','USD/KRW':'KRW=X'},
 'risk':{'max_position':12.0,'tranches':[30,35,35]},'skhy':{'ratio':0.5,'alert':10.0}
}
PF0=pd.DataFrame([
 ['VRT',7,0,'5022','AI Infrastructure'],['ANET',15,0,'5022','AI Networking'],['ETN',7,0,'5022','Power'],['TSLA',10,0,'5022','Tactical'],['AVGO',10,0,'5022','Semiconductor'],['OKLO',40,0,'5022','Nuclear'],['SCHD',150,0,'5022','Dividend'],['SLV',50,0,'5022','Metals'],['XLV',30,0,'5022','Healthcare'],['ITA',15,0,'5022','Defense'],['RKLB',30,0,'5022','Space'],['COST',4,0,'5022','Consumer'],['GOOGL',10,0,'5022','Mega Cap']],columns=['ticker','shares','avg_cost','account','group'])
PL0=pd.DataFrame([
 ['SKHY','대기','실적 확인 후 ADR/한국 본주 가격 조정 관찰','발표 다음 날부터 분할',30,35,35,'가이던스/HBM 수요 훼손',''],
 ['MSFT','관찰','실적 후 과매도 반등','발표 다음 날 정규장 약세',25,35,40,'AI CapEx 축소 또는 Azure 둔화','']],columns=['ticker','status','thesis','trigger','tranche_1_pct','tranche_2_pct','tranche_3_pct','invalidation','notes'])

def load_json(p,d):
    if not p.exists(): p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8'); return d
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return d

def load_csv(p,d):
    if not p.exists(): d.to_csv(p,index=False); return d.copy()
    try:return pd.read_csv(p)
    except:return d.copy()
S=load_json(SETTINGS,DEFAULT); PF=load_csv(PORTFOLIO,PF0); PL=load_csv(PLAN,PL0)

st.markdown('''<style>
.stApp{background:radial-gradient(circle at 10% 0%,rgba(38,98,255,.14),transparent 30%),radial-gradient(circle at 90% 5%,rgba(0,210,170,.09),transparent 25%),#0b1018}.block-container{max-width:1600px;padding-top:1.2rem}[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(28,38,54,.88),rgba(17,24,35,.88));border:1px solid rgba(255,255,255,.08);padding:14px;border-radius:15px}section[data-testid="stSidebar"]{background:#0e1520;border-right:1px solid rgba(255,255,255,.08)}div[data-testid="stDataFrame"]{border:1px solid rgba(255,255,255,.08);border-radius:14px;overflow:hidden}.muted{color:#99a6b8;font-size:.86rem}</style>''',unsafe_allow_html=True)

def clean(xs):
    out=[]
    for x in xs:
        x=str(x).strip().upper()
        if x and x not in out:out.append(x)
    return out

@st.cache_data(ttl=120,show_spinner=False)
def quotes(tickers):
    rows=[]
    for t in tickers:
        try:
            h=yf.Ticker(t).history(period='5d',interval='1d',auto_adjust=False)
            c=float(h.Close.iloc[-1]); p=float(h.Close.iloc[-2]) if len(h)>1 else c
            rows.append([t,c,c-p,(c/p-1)*100 if p else np.nan,'OK'])
        except:rows.append([t,np.nan,np.nan,np.nan,'No data'])
    return pd.DataFrame(rows,columns=['Ticker','Price','Change','Change %','Status'])

@st.cache_data(ttl=300,show_spinner=False)
def hist(t,p,i):
    try:return yf.Ticker(t).history(period=p,interval=i,auto_adjust=False,prepost=True)
    except:return pd.DataFrame()

@st.cache_data(ttl=900,show_spinner=False)
def finnhub_calendar(key,start,end):
    if not key:return pd.DataFrame()
    try:return pd.DataFrame(requests.get('https://finnhub.io/api/v1/calendar/earnings',params={'from':start,'to':end,'token':key},timeout=12).json().get('earningsCalendar',[]))
    except:return pd.DataFrame()

@st.cache_data(ttl=600,show_spinner=False)
def finnhub_news(key,t,start,end):
    if not key:return []
    try:
        x=requests.get('https://finnhub.io/api/v1/company-news',params={'symbol':t,'from':start,'to':end,'token':key},timeout=12).json(); return x if isinstance(x,list) else []
    except:return []

def f(x):return '—' if pd.isna(x) else f'{x:,.2f}'
def chart(d,t,kind,ma20,ma50):
    fig=go.Figure()
    if d.empty:return fig
    if kind=='Candlestick':fig.add_trace(go.Candlestick(x=d.index,open=d.Open,high=d.High,low=d.Low,close=d.Close,name=t,increasing_line_color='#26a69a',decreasing_line_color='#ef5350'))
    else:fig.add_trace(go.Scatter(x=d.index,y=d.Close,name=t,mode='lines'))
    if ma20 and len(d)>=20:fig.add_trace(go.Scatter(x=d.index,y=d.Close.rolling(20).mean(),name='MA20'))
    if ma50 and len(d)>=50:fig.add_trace(go.Scatter(x=d.index,y=d.Close.rolling(50).mean(),name='MA50'))
    fig.update_layout(height=470,template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',xaxis_rangeslider_visible=False,hovermode='x unified',margin=dict(l=10,r=10,t=35,b=10),title=f'{t} price')
    return fig

def signal(x):
    if pd.isna(x):return '데이터 없음'
    if x<=-5:return '급락 — 뉴스/구조 확인'
    if x<=-2:return '약세 — 지지 확인 우선'
    if x<0:return '소폭 약세'
    if x<2:return '보합~강세'
    if x<5:return '강세 — 추격 주의'
    return '급등 — 변동성 확대'

with st.sidebar:
    st.title('📈 Sungje'); st.caption('Market Command Center 2.0')
    page=st.radio('메뉴',['오늘의 시장','차트 연구실','포트폴리오','실적·뉴스','SKHY 패리티','3단계 매수계획','설정'],label_visibility='collapsed')
    st.divider()
    if st.button('🔄 데이터 새로고침',use_container_width=True):st.cache_data.clear();st.rerun()
    st.caption(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    st.markdown('<div class="muted">무료 시세는 지연·누락될 수 있습니다. 주문 실행 기능은 없습니다.</div>',unsafe_allow_html=True)

st.title('Sungje Market Command Center');st.caption('거시환경 → 관심 종목 → 실적 → 분할매수 계획을 하나로 연결한 개인용 웹앱')
M=S.get('market',DEFAULT['market']);md=quotes(tuple(M.values()));md['Name']=md.Ticker.map({v:k for k,v in M.items()});md=md[['Name','Ticker','Price','Change','Change %','Status']]

if page=='오늘의 시장':
    top=md.set_index('Name'); names=['S&P 500','Nasdaq','Russell 2000','VIX','US 10Y','WTI']; cols=st.columns(6)
    for c,n in zip(cols,names):
        r=top.loc[n] if n in top.index else None
        c.metric(n,f(r.Price) if r is not None else '—',f'{r["Change %"]:+.2f}%' if r is not None and not pd.isna(r['Change %']) else '—')
    nas=top.loc['Nasdaq','Change %'] if 'Nasdaq' in top.index else np.nan; vix=top.loc['VIX','Change %'] if 'VIX' in top.index else np.nan; ten=top.loc['US 10Y','Change %'] if 'US 10Y' in top.index else np.nan
    score=(1 if nas>0 else -1)+(1 if vix<0 else -1)+(1 if ten<0 else -1) if not any(pd.isna([nas,vix,ten])) else 0
    regime='Risk-On' if score>=2 else 'Risk-Off' if score<=-2 else 'Mixed'
    a,b,c=st.columns([1,1,2]);a.metric('Market Regime',regime);breadth=md['Change %'].dropna();b.metric('상승 자산 비율',f'{breadth.gt(0).mean()*100:.0f}%' if len(breadth) else '—')
    oil=top.loc['WTI','Change %'] if 'WTI' in top.index else np.nan
    notes=[]
    if oil<=-3:notes.append('유가 급락은 물가 부담에는 긍정적.')
    if ten<0:notes.append('10년물 하락은 성장주 밸류에이션에 우호적.')
    if nas<0 and ten<0:notes.append('그런데도 나스닥이 약하면 기술주 내부 매도가 더 강한 것.')
    c.markdown('#### 오늘의 해석');c.write(' '.join(notes) if notes else '지수 내부 순환매와 장중 변동성에 주의.')
    st.subheader('글로벌 크로스애셋');show=md.copy();show['Price']=show.Price.map(f);show['Change']=show.Change.map(f);show['Change %']=show['Change %'].map(lambda x:'—' if pd.isna(x) else f'{x:+.2f}%');st.dataframe(show,use_container_width=True,hide_index=True)
    st.subheader('내 관심 종목 레이더');w=quotes(tuple(clean(S.get('watchlist',[]))));w['Signal']=w['Change %'].map(signal);w=w.sort_values('Change %',na_position='last');st.dataframe(w,use_container_width=True,hide_index=True,column_config={'Price':st.column_config.NumberColumn(format='$%.2f'),'Change':st.column_config.NumberColumn(format='$%.2f'),'Change %':st.column_config.NumberColumn(format='%.2f%%')})

elif page=='차트 연구실':
    a,b,c,d=st.columns([1.2,1,1,1]);t=a.text_input('Ticker','SKHY').upper().strip();p=b.selectbox('기간',['1d','5d','1mo','3mo','6mo','1y','2y'],3);opts={'1d':['1m','2m','5m','15m'],'5d':['5m','15m','30m','60m'],'1mo':['30m','60m','1d'],'3mo':['1d'],'6mo':['1d'],'1y':['1d','1wk'],'2y':['1d','1wk']};i=c.selectbox('봉',opts[p]);kind=d.selectbox('형태',['Candlestick','Line'])
    x,y,z=st.columns(3);m20=x.checkbox('MA20',True);m50=y.checkbox('MA50',True);comp=z.text_input('비교 티커(선택)','').upper().strip();h=hist(t,p,i);st.plotly_chart(chart(h,t,kind,m20,m50),use_container_width=True)
    if comp:
        h2=hist(comp,p,i)
        if not h.empty and not h2.empty:
            q=pd.concat([h.Close.rename(t),h2.Close.rename(comp)],axis=1).dropna();q=q/q.iloc[0]*100;fig=go.Figure([go.Scatter(x=q.index,y=q[k],name=k) for k in q.columns]);fig.update_layout(height=380,template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',hovermode='x unified',title='Normalized performance (start=100)');st.plotly_chart(fig,use_container_width=True)
    if not h.empty:
        cl=h.Close;r=cl.pct_change();a,b,c,d=st.columns(4);a.metric('현재',f(cl.iloc[-1]));b.metric('기간 수익률',f'{(cl.iloc[-1]/cl.iloc[0]-1)*100:+.2f}%');c.metric('연환산 변동성',f'{r.std()*math.sqrt(252)*100:.1f}%' if i in ['1d','1wk'] else 'Intraday');d.metric('최대낙폭',f'{((cl/cl.cummax())-1).min()*100:.2f}%')

elif page=='포트폴리오':
    st.subheader('보유 종목 편집');ed=st.data_editor(PF,use_container_width=True,num_rows='dynamic',hide_index=True,column_config={'shares':st.column_config.NumberColumn(min_value=0.,step=1.),'avg_cost':st.column_config.NumberColumn(format='$%.2f',min_value=0.)})
    if st.button('💾 포트폴리오 저장'):ed.to_csv(PORTFOLIO,index=False);st.success('저장했습니다.');st.rerun()
    pf=ed.copy();pf.ticker=pf.ticker.astype(str).str.upper().str.strip();q=quotes(tuple(clean(pf.ticker)));pf=pf.merge(q[['Ticker','Price','Change %']],left_on='ticker',right_on='Ticker',how='left');pf['Market Value']=pf.shares*pf.Price;pf['Cost Basis']=pf.shares*pf.avg_cost;pf['Unrealized P/L']=np.where(pf.avg_cost>0,pf['Market Value']-pf['Cost Basis'],np.nan);pf['Weight %']=pf['Market Value']/pf['Market Value'].sum()*100
    total=pf['Market Value'].sum();day=(pf['Market Value']*pf['Change %']/100).sum();mx=pf['Weight %'].max();limit=float(S.get('risk',{}).get('max_position',12));a,b,c,d=st.columns(4);a.metric('추정 평가액',f'${total:,.0f}' if total else '—');b.metric('당일 추정 손익',f'${day:+,.0f}' if total else '—');c.metric('최대 단일 비중',f'{mx:.1f}%' if not pd.isna(mx) else '—');d.metric('집중도 경고','주의' if mx>limit else '정상',f'기준 {limit:.0f}%')
    st.dataframe(pf[['ticker','shares','Price','Change %','Market Value','Weight %','Unrealized P/L','account','group']],use_container_width=True,hide_index=True,column_config={'Price':st.column_config.NumberColumn(format='$%.2f'),'Change %':st.column_config.NumberColumn(format='%.2f%%'),'Market Value':st.column_config.NumberColumn(format='$%.2f'),'Weight %':st.column_config.ProgressColumn(format='%.1f%%',min_value=0,max_value=max(25,float(mx if not pd.isna(mx) else 25))),'Unrealized P/L':st.column_config.NumberColumn(format='$%.2f')})
    if total>0:
        g=pf.groupby('group',dropna=False)['Market Value'].sum().sort_values(ascending=False);fig=go.Figure(go.Pie(labels=g.index.astype(str),values=g.values,hole=.55));fig.update_layout(height=430,template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',title='테마별 비중');st.plotly_chart(fig,use_container_width=True)

elif page=='실적·뉴스':
    key=st.secrets.get('FINNHUB_API_KEY',os.getenv('FINNHUB_API_KEY',''));start=date.today();end=start+timedelta(days=14);st.subheader('다가오는 실적')
    if key:
        e=finnhub_calendar(key,start.isoformat(),end.isoformat());wl=set(clean(S.get('watchlist',[])));e=e[e.symbol.isin(wl)] if not e.empty and 'symbol' in e else e;st.dataframe(e,use_container_width=True,hide_index=True)
    else:st.info('Finnhub 무료 API 키를 설정하면 실적 캘린더와 종목 뉴스가 활성화됩니다. 나머지 기능은 키 없이 작동합니다.')
    st.subheader('종목 뉴스');a,b=st.columns([1,2]);t=a.text_input('뉴스 티커','SKHY').upper();days=b.slider('최근 일수',1,30,7)
    if key:
        for n in finnhub_news(key,t,(date.today()-timedelta(days=days)).isoformat(),date.today().isoformat())[:20]:
            ts=datetime.fromtimestamp(n.get('datetime',0)).strftime('%Y-%m-%d %H:%M');st.markdown(f"**{n.get('headline','')}**  \n{n.get('source','')} · {ts}  \n{n.get('summary','')[:350]}");
            if n.get('url'):st.link_button('기사 열기',n['url'])
            st.divider()

elif page=='SKHY 패리티':
    st.subheader('SKHY ↔ 한국 SK하이닉스 가격 비교');st.warning('ADR 1주당 한국 본주 수는 반드시 공식 전환 조건을 확인해 입력하세요. 기본값은 계산 예시입니다.')
    q=quotes(('SKHY','000660.KS','KRW=X')).set_index('Ticker');gv=lambda t,default:float(q.loc[t,'Price']) if t in q.index and not pd.isna(q.loc[t,'Price']) else default
    a,b,c=st.columns(3);ratio=a.number_input('ADR 1주가 대표하는 한국 본주 수',.0001,value=float(S.get('skhy',{}).get('ratio',.5)),step=.1,format='%.4f');adr=a.number_input('SKHY 가격($)',0.,value=gv('SKHY',0),step=.1);kr=b.number_input('한국 본주 가격(₩)',0.,value=gv('000660.KS',0),step=100.);fx=c.number_input('USD/KRW',1.,value=gv('KRW=X',1300),step=1.)
    parity=kr*ratio/fx if fx else np.nan;premium=(adr/parity-1)*100 if parity>0 else np.nan;a,b,c=st.columns(3);a.metric('한국 본주 환산 ADR 가치',f'${parity:,.2f}' if not pd.isna(parity) else '—');b.metric('SKHY 실제 가격',f'${adr:,.2f}');c.metric('프리미엄/디스카운트',f'{premium:+.2f}%' if not pd.isna(premium) else '—');alert=float(S.get('skhy',{}).get('alert',10))
    if not pd.isna(premium):
        if premium>alert:st.error(f'설정 기준({alert:.1f}%)보다 프리미엄이 큽니다. 교환·공급 확대 시 가격 압박 가능성을 별도로 보세요.')
        elif premium<-alert:st.success('설정 기준보다 큰 디스카운트입니다. 전환 제한·세금·결제시차는 별도 확인이 필요합니다.')
        else:st.info('설정한 정상 범위 안입니다.')
    st.caption('한국 본주 가격 × ADR 비율 ÷ USD/KRW. 수수료·세금·결제시차·전환 제한은 반영하지 않습니다.')

elif page=='3단계 매수계획':
    st.subheader('실적 후 3단계 진입 플래너');ed=st.data_editor(PL,use_container_width=True,num_rows='dynamic',hide_index=True,column_config={'status':st.column_config.SelectboxColumn(options=['대기','관찰','1차','2차','완료','취소'])})
    if st.button('💾 매수계획 저장'):ed.to_csv(PLAN,index=False);st.success('저장했습니다.');st.rerun()
    st.divider();a,b,c,d=st.columns(4);capital=a.number_input('종목별 총 투입액($)',0.,3000.,100.);p1=b.number_input('1차 예상가격',.01,140.,.5);p2=c.number_input('2차 예상가격',.01,135.,.5);p3=d.number_input('3차 예상가격',.01,130.,.5);tr=S.get('risk',{}).get('tranches',[30,35,35]);alloc=[capital*x/100 for x in tr];sh=[math.floor(x/y) for x,y in zip(alloc,[p1,p2,p3])];used=sum(x*y for x,y in zip(sh,[p1,p2,p3]));avg=used/sum(sh) if sum(sh) else 0
    st.dataframe(pd.DataFrame({'단계':['1차','2차','3차'],'배분':[f'{x}%' for x in tr],'예상가격':[p1,p2,p3],'예상주수':sh,'투입액':[x*y for x,y in zip(sh,[p1,p2,p3])]}),use_container_width=True,hide_index=True);a,b,c=st.columns(3);a.metric('총 예상 주수',f'{sum(sh)}주');b.metric('예상 평균단가',f'${avg:,.2f}' if avg else '—');c.metric('남는 현금',f'${capital-used:,.2f}')

elif page=='설정':
    st.subheader('Watchlist');txt=st.text_area('쉼표로 구분',', '.join(S.get('watchlist',[])),height=130);a,b=st.columns(2);mx=a.number_input('단일 종목 최대 비중(%)',1.,100.,float(S.get('risk',{}).get('max_position',12)),1.);al=b.number_input('SKHY 프리미엄 경고 기준(%)',0.,100.,float(S.get('skhy',{}).get('alert',10)),1.);tr=S.get('risk',{}).get('tranches',[30,35,35]);a,b,c=st.columns(3);x1=a.number_input('기본 1차 %',0,100,int(tr[0]));x2=b.number_input('기본 2차 %',0,100,int(tr[1]));x3=c.number_input('기본 3차 %',0,100,int(tr[2]));
    if x1+x2+x3!=100:st.warning(f'현재 합계 {x1+x2+x3}% — 100%로 맞추세요.')
    if st.button('💾 설정 저장',type='primary'):
        S['watchlist']=clean(txt.split(','));S.setdefault('risk',{})['max_position']=mx;S['risk']['tranches']=[x1,x2,x3];S.setdefault('skhy',{})['alert']=al;SETTINGS.write_text(json.dumps(S,ensure_ascii=False,indent=2),encoding='utf-8');st.success('저장했습니다.');st.rerun()
    st.divider();st.subheader('Finnhub 선택 기능');st.code('FINNHUB_API_KEY = "여기에_키"',language='toml');st.write('Streamlit Cloud → App settings → Secrets에 넣으면 실적과 뉴스가 활성화됩니다.');st.info('ChatGPT Plus와 OpenAI API는 별도입니다. 이 앱은 OpenAI API 키 없이 작동합니다.')

st.divider();st.caption('개인 연구·의사결정 보조용. 투자 조언이나 주문 시스템이 아닙니다.')
