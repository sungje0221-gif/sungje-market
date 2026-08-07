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
          /* Canonical price-direction colors used app-wide: up = blue, down = red.
             Any CSS/markup that colors a stock's daily change, P/L, or price move
             should reference these two variables instead of green/red directly. */
          --price-up:#4da3ff;
          --price-down:#ff6474;
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
          min-width:190px;
          width:190px;
        }
        [data-testid="stSidebar"] .block-container {padding:1.1rem .7rem 1.5rem;}
        .block-container {
          max-width:1720px;
          padding-top:2.2rem !important;
          padding-bottom:3rem;
          padding-left:2rem;
          padding-right:2rem;
        }
        h1,h2,h3 {letter-spacing:-.035em;color:var(--os-text);}
        h3 {margin-top:1.6rem !important;}
        .os-brand{display:flex;align-items:center;gap:9px;margin:2px 0 14px;}
        .os-brand-mark{display:grid;place-items:center;width:32px;height:32px;border-radius:12px;
          font-size:18px;font-weight:900;background:linear-gradient(145deg,#2563eb,#22c55e);
          box-shadow:0 8px 24px rgba(37,99,235,.28);}
        .os-brand-title{font-size:14px;font-weight:900;letter-spacing:.12em;}
        .os-brand-subtitle{font-size:8px;color:var(--os-muted);letter-spacing:.13em;margin-top:2px;}
        .refresh-time{font-size:10px;color:#73869b;text-align:center;margin:7px 0 19px;}
        .nav-group-label{font-size:9px;letter-spacing:.18em;color:#667b91;margin:11px 3px 5px;font-weight:800;}
        [data-testid="stSidebar"] .stButton>button {
          justify-content:flex-start;border-radius:10px;border:1px solid transparent;
          min-height:34px;font-size:11px;padding-left:10px;box-shadow:none;
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
        /* Some metrics in a row have a delta (e.g. "-4.98%") and some don't.
           st.metric() stacks label -> value -> delta vertically by default,
           so rows with a delta end up taller than rows without one. The
           actual label/value/delta elements are children of a single inner
           wrapper div (confirmed via DevTools), not direct children of
           [data-testid="stMetric"] itself -- so the grid has to go on that
           inner wrapper (stMetric's only direct child) to have any effect.
           Value and delta share row 2, delta pinned to the right edge,
           instead of stacking, so every card in a row is the same height
           regardless of whether its delta is present. */
        div[data-testid="stMetric"] > div {
          display: grid; grid-template-columns: 1fr auto; align-items: baseline; row-gap: 2px;
        }
        div[data-testid="stMetric"] > div > [data-testid="stMetricLabel"] { grid-column: 1 / -1; }
        div[data-testid="stMetric"] > div > [data-testid="stMetricValue"] { grid-column: 1; }
        div[data-testid="stMetric"] > div > div:has([data-testid="stMetricDelta"]) {
          grid-column: 2; justify-self: end; align-self: baseline; margin: 0 !important;
        }
        div[data-testid="stDataFrame"]{border:1px solid var(--os-border);border-radius:14px;overflow:hidden;}
        button[kind="primary"]{border-radius:10px;}
        .delta-up{color:#4DA3FF;font-weight:750}.delta-down{color:#FF6474;font-weight:750}
        /* st.metric() ships with hardcoded green-up/red-down deltas with no
           color param besides normal/inverse/off. Override both the delta text
           and its arrow icon so every metric across the app follows the same
           blue-up/red-down convention as the rest of the UI. Streamlit renders
           the delta color as an inline style, so several known color values
           (current + older Streamlit releases) are matched for robustness. */
        [data-testid="stMetricDelta"] { color: var(--price-up) !important; }
        [data-testid="stMetricDelta"] svg { fill: var(--price-up) !important; }
        [data-testid="stMetricDelta"][style*="rgb(255"] ,
        [data-testid="stMetricDelta"][style*="255, 43, 43"] ,
        [data-testid="stMetricDelta"][style*="ff2b2b"] {
          color: var(--price-down) !important;
        }
        [data-testid="stMetricDelta"][style*="rgb(255"] svg,
        [data-testid="stMetricDelta"][style*="255, 43, 43"] svg,
        [data-testid="stMetricDelta"][style*="ff2b2b"] svg {
          fill: var(--price-down) !important;
        }
        .delta-flat{color:#A9B4C4;font-weight:650}
        .statbox{background:#0c1828;border:1px solid var(--os-border);border-radius:14px;padding:14px 15px;min-height:92px;}
        .statlabel{font-size:10px;letter-spacing:.08em;text-transform:uppercase;opacity:.6}
        .statvalue{font-size:22px;font-weight:820;margin-top:7px}
        @media (max-width: 900px){
          .block-container{padding:1rem .85rem 2rem!important;max-width:100%!important}
          .hero-row{display:block}.hero-clock{text-align:left;margin-top:14px}
          .hero{padding:18px 16px;border-radius:16px}.hero-title{font-size:25px}.hero-sub{font-size:12px;line-height:1.55}
          .kcard,.signal-card,.watch-card,.action-card,.panel,.ai-brief-panel{min-height:auto!important}
          [data-testid="stHorizontalBlock"]{gap:.65rem!important}
          [data-testid="stDataFrame"],[data-testid="stTable"]{overflow-x:auto!important}
          [data-testid="stPlotlyChart"]{overflow:hidden;border-radius:13px}
          [data-testid="stTabs"] [data-baseweb="tab-list"]{overflow-x:auto;white-space:nowrap;scrollbar-width:none}
          [data-testid="stTabs"] [data-baseweb="tab-list"]::-webkit-scrollbar{display:none}
          [data-testid="stTabs"] button[role="tab"]{flex:0 0 auto!important;padding:8px 10px!important}
          .section-heading h3{font-size:19px}.section-heading{margin-top:20px}
          .statvalue,.mini-stat b{font-size:19px}.kvalue,.signal-value{font-size:22px}
          .os-brand-title{font-size:15px}.os-brand-subtitle{font-size:9px}
        }
        @media (max-width: 640px){
          [data-testid="stSidebar"]{min-width:220px!important;width:220px!important}
          .block-container{padding-top:.75rem!important}
          .hero-market-strip{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}
          .hero-quote{padding:8px 9px!important}.hero-quote b{font-size:13px!important}
          .terminal-hero .hero-title{font-size:24px!important}.terminal-hero{padding:16px!important}
          .heat-hero b{font-size:24px!important}.heat-hero,.heat-stat{padding:15px!important}
          div[data-testid="stMetric"]{padding:11px!important}
          .stButton>button{min-height:40px}
          h1{font-size:1.8rem!important}h2{font-size:1.45rem!important}h3{font-size:1.15rem!important}
        }

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

# Investment OS v0.92 dashboard-specific visual layer is injected separately so
# older pages retain their existing styling while the Command Center evolves.
def inject_dashboard_v092() -> None:
    st.markdown(
        """
        <style>
        .terminal-hero{padding:18px 22px;background:
          linear-gradient(105deg,rgba(22,55,108,.43),rgba(7,29,49,.72) 60%,rgba(7,53,55,.34));
          border-color:rgba(102,156,230,.23);position:relative;overflow:hidden}
        .terminal-hero:after{content:"";position:absolute;inset:0;pointer-events:none;opacity:.12;
          background-image:linear-gradient(rgba(255,255,255,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.07) 1px,transparent 1px);background-size:32px 32px}
        .terminal-hero>*{position:relative;z-index:1}.hero-copy{min-width:300px}
        .terminal-hero .hero-title{font-size:29px;margin-top:3px}.terminal-hero .hero-sub{margin-top:4px}
        .market-regime{display:inline-flex;align-items:center;gap:7px;margin-top:12px;padding:5px 9px;border-radius:999px;font-size:9px;font-weight:900;letter-spacing:.13em;border:1px solid var(--os-border);background:rgba(3,13,23,.45)}
        .market-regime span{width:7px;height:7px;border-radius:50%;background:currentColor;box-shadow:0 0 10px currentColor}
        .market-regime.positive{color:#35d6a5}.market-regime.negative{color:#ff6474}.market-regime.neutral{color:#f3c969}
        .hero-market-strip{display:grid;grid-template-columns:repeat(4,minmax(105px,1fr));gap:8px;align-self:center}
        .hero-quote{min-width:0!important;padding:9px 11px!important}.hero-quote b{font-variant-numeric:tabular-nums}
        .signal-card{position:relative;overflow:hidden;min-height:142px;padding:15px 15px 8px;border-radius:16px;background:linear-gradient(180deg,rgba(15,32,53,.98),rgba(7,18,31,.98));border:1px solid var(--os-border);box-shadow:0 16px 38px rgba(0,0,0,.14)}
        .signal-card:before{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:#69a3ff}
        .signal-card.purple-card:before{background:#b197fc}.signal-card.green-card:before{background:#35d6a5}.signal-card.red-card:before{background:#ff6474}.signal-card.yellow-card:before{background:#f3c969}
        .signal-top{display:flex;justify-content:space-between;align-items:center;font-size:9px;color:#7f94aa;text-transform:uppercase;letter-spacing:.1em;font-weight:800}
        .signal-dot{width:6px;height:6px;border-radius:50%;background:#69a3ff;box-shadow:0 0 10px #69a3ff}.purple-card .signal-dot{background:#b197fc}.green-card .signal-dot{background:#35d6a5}.red-card .signal-dot{background:#ff6474}.yellow-card .signal-dot{background:#f3c969}
        .signal-value{font-size:26px;font-weight:900;letter-spacing:-.04em;margin-top:8px}.signal-value small{font-size:12px;color:#72879e;font-weight:700}
        .signal-note{font-size:10px;color:#91a3b8;margin-top:3px;min-height:16px}.sparkline{display:block;width:100%;height:35px;margin-top:7px}.spark-empty{height:35px;margin-top:7px;font-size:9px;color:#53687d;display:flex;align-items:center}
        .section-heading{display:flex;align-items:flex-end;justify-content:space-between;margin:27px 0 12px}.section-heading.compact{margin-top:22px}
        .section-heading span{display:block;font-size:9px;letter-spacing:.17em;font-weight:900;color:#6f89a5}.section-heading h3{margin:1px 0 0!important;font-size:22px}.section-heading em{font-size:10px;font-style:normal;color:#71859a;margin-bottom:4px}
        .action-card{min-height:112px!important;position:relative;overflow:hidden}.action-top{display:flex;justify-content:space-between;align-items:center}.action-top>span{font-size:10px;color:#526a81;font-weight:900}.action-copy{font-size:12px!important;line-height:1.65!important}
        .watch-card{min-height:150px;padding:15px 16px 7px;border-radius:16px;background:linear-gradient(180deg,rgba(14,30,49,.98),rgba(7,18,31,.98));border:1px solid var(--os-border);transition:transform .18s ease,border-color .18s ease}
        .watch-card:hover{transform:translateY(-2px);border-color:rgba(105,163,255,.36)}.watch-head{display:flex;justify-content:space-between;align-items:center}.watch-head b{font-size:15px;letter-spacing:.02em}.score-pill{font-size:9px;font-weight:900;padding:4px 7px;border-radius:999px;background:rgba(243,201,105,.12);color:#f3c969;border:1px solid rgba(243,201,105,.2)}.score-pill.strong{background:rgba(53,214,165,.1);color:#35d6a5;border-color:rgba(53,214,165,.2)}.score-pill.weak{background:rgba(255,100,116,.1);color:#ff6474;border-color:rgba(255,100,116,.2)}
        .watch-price{font-size:22px;font-weight:900;margin-top:8px;letter-spacing:-.035em}.watch-change{font-size:11px;font-weight:800;margin-top:1px}
        .ai-brief-panel{min-height:320px;padding:20px;border-radius:16px;background:radial-gradient(circle at 90% 0%,rgba(79,140,255,.15),transparent 37%),linear-gradient(180deg,rgba(14,30,49,.98),rgba(7,18,31,.98));border:1px solid var(--os-border)}
        .ai-brief-head{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--os-border);padding-bottom:14px}.ai-brief-head span{font-size:9px;letter-spacing:.16em;color:#6f89a5;font-weight:900}.ai-brief-head b{font-size:23px;color:#69a3ff}
        .ai-brief-copy{font-size:13px;line-height:1.85;color:#bfccda;padding:18px 0}.brief-tags{display:flex;flex-wrap:wrap;gap:7px}.brief-tags span{padding:6px 9px;border-radius:999px;background:rgba(79,140,255,.09);border:1px solid rgba(79,140,255,.17);font-size:9px;color:#9eb4cc}
        @media(max-width:1200px){.hero-market-strip{grid-template-columns:repeat(2,minmax(110px,1fr))}.signal-card{min-height:134px}.signal-value{font-size:23px}}
        @media(max-width:900px){.hero-market-strip{margin-top:16px}.section-heading{align-items:flex-start}.section-heading em{display:none}}
        </style>
        """,
        unsafe_allow_html=True,
    )

# v0.93 heatmap component styles are injected separately to keep the base theme readable.
def inject_heatmap_v093() -> None:
    st.markdown(
        """
        <style>
        .heat-hero{min-height:116px;padding:20px 22px;border-radius:17px;background:radial-gradient(circle at 90% 10%,rgba(47,211,154,.17),transparent 38%),linear-gradient(135deg,rgba(15,32,53,.98),rgba(7,19,33,.98));border:1px solid rgba(47,211,154,.18)}
        .heat-hero span,.heat-stat span{display:block;font-size:9px;letter-spacing:.16em;color:#7890aa;font-weight:900}.heat-hero b{display:block;font-size:29px;letter-spacing:-.04em;margin-top:8px}.heat-hero p{font-size:11px;color:#91a5bb;margin:9px 0 0}.heat-hero strong{color:#d8e4f2}
        .heat-stat{min-height:116px;padding:18px;border-radius:16px;background:linear-gradient(180deg,rgba(14,30,49,.98),rgba(7,18,31,.98));border:1px solid rgba(148,163,184,.14)}
        .heat-stat b{display:block;font-size:25px;letter-spacing:-.04em;margin-top:10px}.heat-stat em{display:block;font-style:normal;font-size:10px;color:#71869d;margin-top:6px}.heat-stat.green b{color:var(--price-up)}.heat-stat.red b{color:var(--price-down)}.heat-stat.blue b{color:#69a3ff}
        [data-testid="stTabs"] [data-baseweb="tab-list"]{gap:8px;background:rgba(8,21,37,.72);padding:6px;border-radius:13px;border:1px solid rgba(148,163,184,.12)}
        [data-testid="stTabs"] button[role="tab"]{border-radius:9px;padding:9px 14px;font-size:12px}
        [data-testid="stTabs"] button[aria-selected="true"]{background:rgba(79,140,255,.17)}
        @media(max-width:900px){.heat-hero,.heat-stat{min-height:auto}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_v098() -> None:
    st.markdown(
        """
        <style>
        .advisor-signal{border-radius:14px;padding:15px;background:linear-gradient(180deg,rgba(14,30,49,.98),rgba(7,18,31,.98));border:1px solid var(--os-border)}
        @media(max-width:760px){
          [data-testid="stSidebar"]{min-width:245px}
          .block-container{padding-left:.72rem!important;padding-right:.72rem!important}
          .hero-market-strip{grid-template-columns:repeat(2,minmax(0,1fr))!important}
          .signal-value{font-size:21px!important}.watch-price{font-size:19px!important}
          [data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}
          [data-testid="stPlotlyChart"]>div{min-height:420px}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_v301() -> None:
    """Compact desktop shell and denser decision cards for v3.01."""
    st.markdown(
        """
        <style>
        @media (min-width: 901px){
          [data-testid="stSidebar"]{min-width:168px!important;width:168px!important;max-width:168px!important}
          [data-testid="stSidebar"] .block-container{padding:1rem .48rem 1.25rem!important}
          [data-testid="stSidebar"] .stButton>button{font-size:10px!important;min-height:31px!important;padding-left:7px!important}
          .nav-group-label{font-size:8px!important;margin:9px 2px 3px!important}
          .os-brand{gap:7px!important;margin-bottom:10px!important}.os-brand-mark{width:28px!important;height:28px!important;border-radius:10px!important;font-size:15px!important}
          .os-brand-title{font-size:12px!important}.os-brand-subtitle{font-size:7px!important}
        }
        .signal-card{min-height:116px!important;padding:13px 14px 6px!important}
        .signal-value{font-size:23px!important}.sparkline{height:29px!important;margin-top:4px!important}
        .action-card{min-height:96px!important;padding:13px 14px!important}
        .action-copy{margin-top:8px!important;line-height:1.45!important}
        .watch-card{min-height:102px!important;padding:12px 14px!important}
        .watch-price{font-size:19px!important;margin-top:5px!important}
        .section-heading{margin:20px 0 9px!important}
        .section-heading h3{font-size:19px!important}
        .compact-stock-card{background:#0d1b2d;border:1px solid #26384f;border-radius:12px;padding:11px 13px;min-height:104px;margin-bottom:5px}
        .compact-stock-card>div{display:flex;justify-content:space-between;align-items:center}.compact-stock-card b{font-size:15px}.compact-stock-card span{font-size:10px;color:#8ea4bf;text-transform:uppercase}.compact-stock-card strong{display:block;font-size:20px;margin:8px 0 2px}.compact-stock-card small{font-size:12px}.compact-stock-card p{margin:6px 0 0;color:#a9b7c9;font-size:11px;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .watch-grid-card{min-height:112px}.earnings-card{min-height:96px}
        [data-testid="stMetric"]{padding:7px 10px!important}.signal-card{min-height:88px!important;padding:10px 12px 4px!important}.signal-value{font-size:20px!important}.sparkline{height:22px!important}.action-card{min-height:78px!important;padding:10px 12px!important}.watch-card{min-height:82px!important;padding:9px 12px!important}.watch-price{font-size:17px!important}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_v309() -> None:
    """Dense hybrid watchlist: sortable mover table plus five-column cards."""
    st.markdown(
        """
        <style>
        .watch-grid-card-v309{
          min-height:92px!important;
          padding:10px 11px 8px!important;
          margin-bottom:4px!important;
          border-radius:11px!important;
        }
        .watch-card-head{display:flex;justify-content:space-between;align-items:center;gap:7px}
        .watch-card-head b{font-size:13px!important;white-space:nowrap}
        .watch-card-head span{font-size:8px!important;max-width:70px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .watch-card-body{display:flex;align-items:baseline;justify-content:space-between;gap:7px;margin-top:7px}
        .watch-card-body strong{font-size:17px!important;margin:0!important}
        .watch-card-body small{font-size:10px!important;font-weight:800;white-space:nowrap}
        .watch-grid-card-v309 p{font-size:9px!important;margin-top:5px!important;color:#8499b0!important}
        [data-testid="stDataFrame"]{border:1px solid rgba(148,163,184,.14);border-radius:12px;overflow:hidden}
        @media(max-width:1250px){.watch-card-head span{display:none}.watch-card-body{display:block}.watch-card-body small{display:block;margin-top:2px}}
        </style>
        """,
        unsafe_allow_html=True,
    )
