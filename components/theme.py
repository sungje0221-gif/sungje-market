import streamlit as st

def inject_theme():
    st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {display:none;}
    [data-testid="stSidebar"] {
      background:linear-gradient(180deg,#091424 0%,#07101c 100%);
      border-right:1px solid rgba(255,255,255,.07);
      min-width:250px;
    }
    .block-container {max-width:1700px;padding-top:1rem;padding-bottom:2rem;}
    h1,h2,h3 {letter-spacing:-.03em;}
    .hero {
      padding:20px 24px;border-radius:18px;margin-bottom:16px;
      background:linear-gradient(135deg,rgba(30,64,175,.22),rgba(15,118,110,.15));
      border:1px solid rgba(96,165,250,.2);
    }
    .hero-kicker{font-size:11px;letter-spacing:.15em;text-transform:uppercase;opacity:.65}
    .hero-title{font-size:30px;font-weight:850;margin-top:5px}
    .hero-sub{font-size:14px;opacity:.72;margin-top:3px}
    .kcard {
      background:linear-gradient(180deg,rgba(15,28,46,.98),rgba(10,20,34,.98));
      border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:16px;
      min-height:122px;box-shadow:0 14px 34px rgba(0,0,0,.14);
    }
    .klabel{font-size:11px;letter-spacing:.09em;text-transform:uppercase;opacity:.62}
    .kvalue{font-size:28px;font-weight:850;margin-top:8px}
    .knote{font-size:12px;opacity:.7;margin-top:8px}
    .pos{color:#43D7A3}.neg{color:#FF6F7D}.warn{color:#F2C94C}.blue{color:#60A5FA}.purple{color:#A78BFA}
    .panel{
      background:#0c1828;border:1px solid rgba(255,255,255,.07);
      border-radius:16px;padding:18px;
    }
    .chip{
      display:inline-block;padding:5px 9px;border-radius:999px;margin-right:5px;margin-top:8px;
      background:rgba(59,130,246,.12);border:1px solid rgba(96,165,250,.2);font-size:11px
    }
    div[data-testid="stMetric"] {
      background:linear-gradient(180deg,rgba(15,28,46,.98),rgba(10,20,34,.98));
      border:1px solid rgba(255,255,255,.07);padding:14px;border-radius:14px;
    }
    div[data-testid="stDataFrame"]{border:1px solid rgba(255,255,255,.06);border-radius:14px;overflow:hidden}
    button[kind="primary"]{border-radius:10px}
    
    .delta-up{color:#4DA3FF;font-weight:750}
    .delta-down{color:#FF6474;font-weight:750}
    .delta-flat{color:#A9B4C4;font-weight:650}
    .statbox{
      background:#0c1828;border:1px solid rgba(255,255,255,.07);
      border-radius:14px;padding:14px 15px;min-height:92px
    }
    .statlabel{font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.6}
    .statvalue{font-size:22px;font-weight:820;margin-top:7px}
    </style>
    
    """, unsafe_allow_html=True)
