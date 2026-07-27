import streamlit as st


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
          --os-bg:#06101d;
          --os-panel:#0b1828;
          --os-panel-2:#0f2035;
          --os-border:rgba(148,163,184,.14);
          --os-text:#f4f7fb;
          --os-muted:#8fa2b8;
          --os-blue:#4f8cff;
          --os-green:#2fd39a;
          --os-red:#ff6677;
          --os-yellow:#f3c969;
        }
        [data-testid="stSidebarNav"] {display:none;}
        [data-testid="stAppViewContainer"] {
          background:
            radial-gradient(circle at 76% -10%, rgba(37,99,235,.18), transparent 31%),
            linear-gradient(180deg,#071221 0%,var(--os-bg) 100%);
          color:var(--os-text);
        }
        [data-testid="stHeader"] {background:rgba(6,16,29,.72);backdrop-filter:blur(12px);}
        [data-testid="stSidebar"] {
          background:linear-gradient(180deg,#081525 0%,#050d17 100%);
          border-right:1px solid var(--os-border);
          min-width:270px;
        }
        [data-testid="stSidebar"] .block-container {padding-top:1.35rem;}
        .block-container {
          max-width:1720px;
          padding-top:2.2rem !important;
          padding-bottom:3rem;
          padding-left:2rem;
          padding-right:2rem;
        }
        h1,h2,h3 {letter-spacing:-.035em;color:var(--os-text);}
        h3 {margin-top:1.6rem !important;}
        .os-brand{display:flex;align-items:center;gap:12px;margin:2px 0 18px;}
        .os-brand-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;
          font-size:18px;font-weight:900;background:linear-gradient(145deg,#2563eb,#22c55e);
          box-shadow:0 8px 24px rgba(37,99,235,.28);}
        .os-brand-title{font-size:17px;font-weight:900;letter-spacing:.12em;}
        .os-brand-subtitle{font-size:10px;color:var(--os-muted);letter-spacing:.13em;margin-top:2px;}
        .refresh-time{font-size:10px;color:#73869b;text-align:center;margin:7px 0 19px;}
        .nav-group-label{font-size:9px;letter-spacing:.18em;color:#667b91;margin:16px 3px 7px;font-weight:800;}
        [data-testid="stSidebar"] .stButton>button {
          justify-content:flex-start;border-radius:10px;border:1px solid transparent;
          min-height:38px;font-size:12px;padding-left:13px;box-shadow:none;
        }
        [data-testid="stSidebar"] .stButton>button[kind="secondary"] {
          background:transparent;color:#aebdd0;
        }
        [data-testid="stSidebar"] .stButton>button[kind="secondary"]:hover {
          background:rgba(79,140,255,.08);border-color:rgba(79,140,255,.16);color:white;
        }
        [data-testid="stSidebar"] .stButton>button[kind="primary"] {
          background:linear-gradient(90deg,rgba(37,99,235,.35),rgba(37,99,235,.14));
          border-color:rgba(96,165,250,.24);color:#fff;
        }
        .sidebar-status-card{margin-top:22px;padding:14px;border-radius:13px;background:rgba(15,32,53,.78);
          border:1px solid var(--os-border);}
        .status-row{font-size:11px;display:flex;gap:7px;align-items:center;}
        .status-dot{width:7px;height:7px;border-radius:99px;background:var(--os-green);box-shadow:0 0 12px var(--os-green);}
        .status-copy{font-size:10px;color:#758aa0;margin-top:6px;}
        .hero {padding:24px 26px;border-radius:20px;margin:0 0 18px;
          background:linear-gradient(130deg,rgba(30,64,175,.3),rgba(8,47,73,.24) 55%,rgba(13,148,136,.12));
          border:1px solid rgba(96,165,250,.22);box-shadow:0 18px 55px rgba(0,0,0,.18);}
        .hero-row{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;}
        .hero-kicker{font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:#87a6ca;font-weight:800;}
        .hero-title{font-size:31px;font-weight:900;margin-top:5px;letter-spacing:-.04em;}
        .hero-sub{font-size:13px;color:#91a5bb;margin-top:6px;}
        .hero-clock{text-align:right;font-size:12px;color:#8fa2b8;white-space:nowrap;}
        .hero-clock b{display:block;color:#e5edf7;font-size:15px;margin-bottom:3px;}
        .section-eyebrow{font-size:10px;color:#70879e;letter-spacing:.14em;font-weight:800;margin-bottom:-6px;}
        .kcard {background:linear-gradient(180deg,rgba(15,32,53,.98),rgba(8,20,34,.98));
          border:1px solid var(--os-border);border-radius:16px;padding:16px;min-height:118px;
          box-shadow:0 16px 38px rgba(0,0,0,.14);}
        .klabel{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#7f94aa;}
        .kvalue{font-size:27px;font-weight:900;margin-top:8px;letter-spacing:-.035em;}
        .knote{font-size:11px;color:#8ea0b4;margin-top:8px;}
        .pos{color:var(--os-green)}.neg{color:var(--os-red)}.warn{color:var(--os-yellow)}
        .blue{color:#69a3ff}.purple{color:#b197fc}
        .panel{background:linear-gradient(180deg,rgba(13,29,48,.98),rgba(8,20,34,.98));
          border:1px solid var(--os-border);border-radius:16px;padding:18px;}
        .playbook-card{min-height:120px;background:linear-gradient(180deg,rgba(13,29,48,.98),rgba(8,20,34,.98));
          border:1px solid var(--os-border);border-radius:15px;padding:16px;}
        .playbook-number{display:grid;place-items:center;width:27px;height:27px;border-radius:9px;
          background:rgba(79,140,255,.14);border:1px solid rgba(79,140,255,.22);font-weight:900;font-size:11px;}
        .playbook-copy{font-size:12px;line-height:1.65;color:#b8c6d6;margin-top:12px;}
        .chip{display:inline-block;padding:5px 9px;border-radius:999px;margin-right:5px;margin-top:8px;
          background:rgba(59,130,246,.12);border:1px solid rgba(96,165,250,.2);font-size:10px;}
        div[data-testid="stMetric"] {background:linear-gradient(180deg,rgba(15,32,53,.98),rgba(8,20,34,.98));
          border:1px solid var(--os-border);padding:14px;border-radius:14px;}
        div[data-testid="stDataFrame"]{border:1px solid var(--os-border);border-radius:14px;overflow:hidden;}
        button[kind="primary"]{border-radius:10px;}
        .delta-up{color:#4DA3FF;font-weight:750}.delta-down{color:#FF6474;font-weight:750}
        .delta-flat{color:#A9B4C4;font-weight:650}
        .statbox{background:#0c1828;border:1px solid var(--os-border);border-radius:14px;padding:14px 15px;min-height:92px;}
        .statlabel{font-size:10px;letter-spacing:.08em;text-transform:uppercase;opacity:.6}
        .statvalue{font-size:22px;font-weight:820;margin-top:7px}
        @media (max-width: 900px){.block-container{padding-left:1rem;padding-right:1rem}.hero-row{display:block}.hero-clock{text-align:left;margin-top:14px}}

        .compact-hero{padding:17px 21px;margin-bottom:14px}.compact-hero .hero-title{font-size:27px}
        .hero-market-strip{display:flex;gap:9px;align-items:stretch}.hero-quote{min-width:112px;padding:9px 11px;border-radius:12px;background:rgba(5,15,27,.55);border:1px solid rgba(111,143,178,.18)}
        .hero-quote span{display:block;font-size:9px;color:#7f94aa;text-transform:uppercase;letter-spacing:.1em}.hero-quote b{display:block;font-size:15px;margin-top:3px}.hero-quote em{font-style:normal;font-size:10px}.up{color:#47d7ac}.down{color:#ff6b7d}
        .action-card{min-height:100px;border-radius:15px;padding:15px 16px;background:linear-gradient(180deg,rgba(13,29,48,.98),rgba(8,20,34,.98));border:1px solid var(--os-border)}
        .action-card.buy{border-top:2px solid #35d6a5}.action-card.hold{border-top:2px solid #64a6ff}.action-card.avoid{border-top:2px solid #ff6474}.action-card.watch{border-top:2px solid #f5c451}
        .action-label{font-size:11px;font-weight:900;letter-spacing:.14em}.buy .action-label{color:#35d6a5}.hold .action-label{color:#64a6ff}.avoid .action-label{color:#ff6474}.watch .action-label{color:#f5c451}
        .action-copy{font-size:12px;line-height:1.6;color:#bdcad8;margin-top:12px}.brief-score{font-size:22px;font-weight:900}.brief-copy{line-height:1.8;margin-top:10px;color:#b8c6d6}
        .page-kicker{font-size:10px;letter-spacing:.18em;color:#6f89a5;font-weight:800;margin-bottom:-8px}.mini-stat{padding:13px 14px;border-radius:14px;background:linear-gradient(180deg,rgba(15,32,53,.98),rgba(8,20,34,.98));border:1px solid var(--os-border)}
        .mini-stat span{display:block;font-size:9px;letter-spacing:.1em;color:#768ba1}.mini-stat b{display:block;font-size:22px;margin-top:5px}.mini-stat em{display:block;font-style:normal;font-size:10px;color:#71869a;margin-top:3px}
        </style>
        """,
        unsafe_allow_html=True,
    )

# Investment OS 1.0 Part 1B visual layer
