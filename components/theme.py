import streamlit as st

def inject_theme():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {display:none;}
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1726 0%, #0a1320 100%);
            border-right: 1px solid rgba(255,255,255,.06);
        }
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1600px;
        }
        h1,h2,h3 {letter-spacing:-0.02em;}
        .smcc-hero {
            background: linear-gradient(135deg, rgba(53,208,186,.16), rgba(58,107,255,.10));
            border: 1px solid rgba(83,220,204,.22);
            padding: 22px 24px;
            border-radius: 18px;
            margin-bottom: 18px;
        }
        .smcc-kicker {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: .14em;
            opacity: .65;
        }
        .smcc-title {
            font-size: 28px;
            font-weight: 800;
            margin-top: 5px;
        }
        .smcc-sub {
            opacity: .72;
            margin-top: 4px;
        }
        .smcc-card {
            background: linear-gradient(180deg, rgba(18,31,49,.98), rgba(11,22,36,.98));
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 16px;
            padding: 16px 18px;
            min-height: 126px;
            box-shadow: 0 12px 32px rgba(0,0,0,.14);
        }
        .smcc-label {
            font-size: 12px;
            opacity: .65;
            text-transform: uppercase;
            letter-spacing: .08em;
        }
        .smcc-value {
            font-size: 28px;
            font-weight: 800;
            margin-top: 10px;
        }
        .smcc-positive {color:#46d6a8;}
        .smcc-negative {color:#ff6e7d;}
        .smcc-neutral {color:#f2c94c;}
        .smcc-note {font-size:13px; opacity:.72; margin-top:7px;}
        .smcc-panel {
            background: #0d1929;
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 16px;
            padding: 18px;
        }
        .smcc-chip {
            display:inline-block;
            padding:5px 9px;
            border-radius:999px;
            background:rgba(53,208,186,.12);
            border:1px solid rgba(53,208,186,.22);
            margin-right:6px;
            font-size:12px;
        }
        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(18,31,49,.98), rgba(11,22,36,.98));
            border:1px solid rgba(255,255,255,.07);
            padding:14px 16px;
            border-radius:14px;
        }
        div[data-testid="stDataFrame"] {
            border:1px solid rgba(255,255,255,.06);
            border-radius:14px;
            overflow:hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
