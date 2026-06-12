"""
app.py
Streamlit Equity Research Dashboard
Goldman Sachs-style institutional research report generator.
Usage: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
import sys
import traceback

# Add directory to path
sys.path.insert(0, os.path.dirname(__file__))

from report_generator import fetch_stock_data, fmt_large, fmt_pct, fmt_num, search_ticker, resolve_input
from charts import (
    revenue_chart, margin_chart, fcf_chart,
    price_chart, scenario_chart, score_radar_chart, valuation_bar_chart,
)
from pdf_exporter import generate_pdf


def dark_table(rows: list[dict]):
    """Render a list of dicts as a dark-themed HTML table."""
    if not rows:
        return
    headers = list(rows[0].keys())
    html = "<table style='width:100%; border-collapse:collapse; font-size:0.82rem;'>"
    html += "<tr>"
    for h in headers:
        html += f"<th style='padding:7px 10px; background:#252520; color:#c8a951; font-weight:700; border-bottom:2px solid #c8a951; text-align:left;'>{h}</th>"
    html += "</tr>"
    for i, row in enumerate(rows):
        bg = "#1c1c1c" if i % 2 == 0 else "#161616"
        html += f"<tr style='background:{bg};'>"
        for j, val in enumerate(row.values()):
            color = "#c8a951" if j == 0 else "#f0e094"
            html += f"<td style='padding:6px 10px; color:{color}; border-bottom:1px solid #2a2a2a;'>{val}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Equity Research Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CUSTOM CSS — Goldman Sachs palette
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ── GLOBAL BACKGROUND ── */
    .stApp                          { background-color: #111111 !important; }
    .main .block-container          { background-color: #111111 !important; padding-top: 1.5rem; }

    /* ── TOOLBAR ── */
    header[data-testid="stHeader"]  { background-color: #111111 !important; border-bottom: 1px solid #c8a951; }
    header[data-testid="stHeader"] * { color: #c8a951 !important; }

    /* ── HEADER BANNER ── */
    .gs-header {
        background: linear-gradient(90deg, #1c1c1c 0%, #252525 100%);
        border: 1px solid #c8a951;
        border-left: 5px solid #c8a951;
        padding: 18px 28px;
        border-radius: 8px;
        margin-bottom: 18px;
    }
    .gs-header h1 { color: #c8a951 !important; margin: 0; font-size: 1.7rem; }
    .gs-header p  { color: #d4b96a !important; margin: 4px 0 0 0; font-size: 0.9rem; }

    /* ── KPI METRIC CARDS ── */
    .metric-card {
        background: #1c1c1c;
        border: 1px solid #c8a951;
        border-radius: 8px;
        padding: 14px 16px;
        text-align: center;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(200,169,81,0.35);
        border-color: #e8d48a;
    }
    .metric-label { font-size: 0.72rem; color: #c8a951; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 1.35rem; font-weight: 800; color: #f0e094; margin-top: 4px; }
    .metric-sub   { font-size: 0.73rem; color: #9a844a; }

    /* ── SECTION HEADERS ── */
    .section-header {
        background: #1c1c1c;
        border-left: 4px solid #c8a951;
        color: #c8a951 !important;
        padding: 8px 14px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.95rem;
        margin: 16px 0 10px 0;
        letter-spacing: 0.5px;
    }

    /* ── STREAMLIT TEXT (paragraphs, labels, etc.) ── */
    .stMarkdown p, .stMarkdown li, .stMarkdown span { color: #d4c47a !important; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3   { color: #c8a951 !important; }
    .stMarkdown strong                               { color: #f0e094 !important; }

    /* ── NATIVE METRIC WIDGET ── */
    [data-testid="stMetric"]        { background: #1c1c1c; border: 1px solid #c8a951; border-radius: 8px; padding: 10px; }
    [data-testid="stMetricLabel"] p { color: #c8a951 !important; font-weight: 600; }
    [data-testid="stMetricValue"]   { color: #f0e094 !important; }
    [data-testid="stMetricDelta"]   { color: #a8c870 !important; }

    /* ── DATAFRAMES ── */
    [data-testid="stDataFrame"] > div { background: #1c1c1c !important; border: 1px solid #333 !important; border-radius: 6px; }
    .dvn-scroller                     { background: #1c1c1c !important; }

    /* ── EXPANDERS ── */
    details[data-testid="stExpander"] > summary          { background: #1c1c1c !important; border: 1px solid #444 !important; border-radius: 6px; color: #c8a951 !important; }
    details[data-testid="stExpander"] > summary:hover    { border-color: #c8a951 !important; }
    details[data-testid="stExpander"] > div              { background: #181818 !important; border: 1px solid #333 !important; border-top: none !important; }
    details[data-testid="stExpander"] p                  { color: #d4c47a !important; }

    /* ── ALERT BOXES ── */
    [data-testid="stAlert"]                        { border-radius: 6px; }
    div[data-baseweb="notification"]               { background: #1c1500 !important; border-left: 4px solid #c8a951 !important; }
    div[data-baseweb="notification"] span          { color: #e8d48a !important; }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #1c1c1c !important;
        border-radius: 8px;
        padding: 4px;
        border: 1px solid #3a3a2a;
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #9a844a !important;
        font-weight: 600;
        font-size: 0.82rem;
        border-radius: 6px !important;
        padding: 6px 12px !important;
        transition: all 0.18s ease;
    }
    .stTabs [data-baseweb="tab"]:hover        { color: #e8d48a !important; background: #252520 !important; }
    .stTabs [aria-selected="true"]            {
        background: linear-gradient(135deg, #b89030 0%, #e8d48a 100%) !important;
        color: #111111 !important;
        font-weight: 800 !important;
    }
    .stTabs [data-baseweb="tab-panel"]        { background: #111111 !important; padding-top: 1rem; }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"]                               { background-color: #0e0e0e !important; border-right: 1px solid #c8a951; }
    [data-testid="stSidebar"] .stMarkdown p                 { color: #c8a951 !important; font-size: 0.83rem; }
    [data-testid="stSidebar"] .stMarkdown h2                { color: #c8a951 !important; }
    [data-testid="stSidebar"] .stMarkdown h3                { color: #9a844a !important; }
    [data-testid="stSidebar"] .stMarkdown strong            { color: #e8d48a !important; }
    [data-testid="stSidebar"] .stMarkdown li                { color: #c8a951 !important; }
    [data-testid="stSidebar"] hr                            { border-color: #3a3a2a !important; }
    [data-testid="stSidebar"] label                         { color: #c8a951 !important; font-weight: 600; font-size: 0.82rem; }
    [data-testid="stSidebar"] .stTextInput input            {
        background: #1c1c1c !important;
        color: #f0e094 !important;
        border: 1px solid #c8a951 !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebar"] .stTextInput input::placeholder { color: #6a5a2a !important; }
    [data-testid="stSidebar"] span[data-testid="stMarkdownContainer"] p { color: #c8a951 !important; }

    /* ── SIDEBAR QUICK-PICK BUTTONS ── */
    [data-testid="stSidebar"] .stButton > button {
        background: #1c1c1c !important;
        border: 1.5px solid #c8a951 !important;
        color: #c8a951 !important;
        font-weight: 700 !important;
        font-size: 0.83rem !important;
        border-radius: 6px !important;
        padding: 9px 14px !important;
        width: 100% !important;
        text-align: left !important;
        letter-spacing: 0.4px !important;
        transition: all 0.18s ease !important;
        margin-bottom: 2px !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #c8a951 0%, #e8d48a 100%) !important;
        color: #111111 !important;
        border-color: #e8d48a !important;
        box-shadow: 0 0 12px rgba(200,169,81,0.45) !important;
        transform: translateX(4px) !important;
    }

    /* ── ANALYZE BUTTON (first button in sidebar) ── */
    [data-testid="stSidebar"] > div > div > div > div > div:nth-child(3) .stButton > button {
        background: linear-gradient(135deg, #c8a951 0%, #e8d48a 100%) !important;
        color: #111111 !important;
        font-weight: 900 !important;
        border: none !important;
        font-size: 0.95rem !important;
        letter-spacing: 1px !important;
    }

    /* ── UPSIDE PILLS ── */
    .upside-pos { color: #5de87a; font-weight: 700; }
    .upside-neg { color: #ff5555; font-weight: 700; }

    /* ── SPINNER ── */
    [data-testid="stSpinner"] p { color: #c8a951 !important; }

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar       { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #1c1c1c; }
    ::-webkit-scrollbar-thumb { background: #c8a951; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #e8d48a; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.markdown("""
<div class="gs-header">
    <h1>📊 Equity Research Dashboard</h1>
    <p>Institutional-Grade Fundamental Analysis · Powered by Yahoo Finance · Goldman Sachs Style ·
        <span style="background:#22c55e; color:white; font-size:0.75rem; font-weight:700;
                     padding:2px 9px; border-radius:20px; margin-left:4px; letter-spacing:1px;">
            ● LIVE DATA
        </span>
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🔍 Stock Search")
    ticker_input = st.text_input(
        "Company Name or Ticker",
        value="",
        placeholder="e.g. Apple, SAP SE, NVDA, Tesla",
        help="Type any company name OR ticker symbol. Search works for NYSE, NASDAQ, XETRA, LSE and more.",
    )
    analyze_btn = st.button("🚀 Analyze", use_container_width=True, type="primary")

    # Live search-as-you-type suggestions
    if ticker_input and len(ticker_input) >= 2 and not ticker_input.strip().isupper():
        with st.spinner("Searching..."):
            candidates = search_ticker(ticker_input.strip())
        if candidates:
            st.markdown("**Matches found — click to select:**")
            for c in candidates[:6]:
                label = f"{c['ticker']} — {c['name']} ({c['exchange']})"
                if st.button(label, key=f"cand_{c['ticker']}", use_container_width=True):
                    st.session_state["quick_ticker"] = c["ticker"]
                    st.rerun()

    st.markdown("---")
    st.markdown("### 📌 Quick Examples")

    QUICK_PICKS = [
        ("SAP",  "SAP SE"),
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
        ("JNJ",  "Johnson & Johnson"),
        ("NVDA", "NVIDIA"),
        ("TSLA", "Tesla"),
    ]

    for ticker_sym, company_name in QUICK_PICKS:
        if st.button(f"{ticker_sym}  ·  {company_name}", key=f"qp_{ticker_sym}",
                     use_container_width=True):
            st.session_state["quick_ticker"] = ticker_sym

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
    This dashboard generates an **institutional equity research report** for any publicly traded stock using:
    - 📈 **Yahoo Finance** (free, no API key)
    - 🔎 **Company name search** (type name or ticker)
    - 🤖 **Rule-based scoring engine**
    - 📄 **PDF export** (Goldman Sachs style)

    *For informational purposes only. Not investment advice.*
    """)

# Handle quick ticker buttons
if "quick_ticker" in st.session_state:
    ticker_input = st.session_state.pop("quick_ticker")
    analyze_btn = True

# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
if "data" not in st.session_state:
    st.session_state["data"] = None
if "last_ticker" not in st.session_state:
    st.session_state["last_ticker"] = None

# ---------------------------------------------------------------------------
# TRIGGER ANALYSIS
# ---------------------------------------------------------------------------
if analyze_btn and ticker_input:
    resolved_ticker, candidates = resolve_input(ticker_input)
    ticker_clean = resolved_ticker.strip().upper()
    label = ticker_clean
    if candidates:
        # Show what we resolved to
        matched = candidates[0]
        label = f"{matched['name']} ({ticker_clean})"
    with st.spinner(f"⏳ Fetching data for **{label}** from Yahoo Finance..."):
        try:
            data = fetch_stock_data(ticker_clean)
            st.session_state["data"] = data
            st.session_state["last_ticker"] = ticker_clean
            if candidates and len(candidates) > 1:
                st.session_state["search_candidates"] = candidates
            else:
                st.session_state.pop("search_candidates", None)
        except Exception as e:
            st.error(f"❌ Could not fetch data for **{ticker_clean}**: {str(e)}")
            st.session_state["data"] = None

# ---------------------------------------------------------------------------
# DISPLAY REPORT
# ---------------------------------------------------------------------------
d = st.session_state.get("data")

# "Did you mean?" banner — show other matches from a name search
candidates_banner = st.session_state.get("search_candidates", [])
if d and candidates_banner and len(candidates_banner) > 1:
    st.info(
        f"**Showing: {candidates_banner[0]['name']} ({candidates_banner[0]['ticker']})**  "
        "  Other matches: "
        + "  |  ".join(
            f"`{c['ticker']}` {c['name']}" for c in candidates_banner[1:5]
        )
        + "  — type the ticker directly to switch."
    )

if d is None:
    # Landing state
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #6c757d;">
        <h2>Search for any company by name or ticker</h2>
        <p style="font-size:1.1rem;">Type a company name (e.g. <b>Apple</b>, <b>SAP SE</b>, <b>Goldman Sachs</b>) or a ticker (e.g. <b>AAPL</b>, <b>SAP</b>)</p>
        <p style="font-size:0.9rem; margin-top:20px;">
            Supports NYSE · NASDAQ · XETRA · LSE · TSX · and more
        </p>
        <p style="font-size:0.9rem; margin-top:8px;">
            Examples: <b>AAPL</b> · <b>MSFT</b> · <b>SAP</b> · <b>NVDA</b> · <b>Tesla</b> ·
            <b>Goldman Sachs</b> · <b>JPMorgan</b> · <b>Exxon</b> · <b>Alibaba</b> · <b>TSMC</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------------------------
# RECOMMENDATION CARD
# ---------------------------------------------------------------------------
sym = d["currency_sym"]
rec = d["recommendation"]

# Color mapping
rec_colors = {
    "STRONG BUY": "#0a5c36",
    "BUY": "#1a7a4a",
    "HOLD": "#b8860b",
    "REDUCE": "#c0392b",
    "SELL": "#922b21",
}
rec_color = rec_colors.get(rec, "#003366")

upside_val = d.get("upside")
upside_str = f"+{upside_val:.1f}%" if upside_val and upside_val >= 0 else (f"{upside_val:.1f}%" if upside_val else "N/A")
upside_class = "upside-pos" if upside_val and upside_val > 0 else "upside-neg"

st.markdown(f"""
<div style="background:{rec_color}; border-radius:10px; padding:20px 28px;
            color:white; margin-bottom:20px;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div>
            <div style="font-size:0.8rem; opacity:0.8; letter-spacing:1px;">COMPANY</div>
            <div style="font-size:1.6rem; font-weight:900;">{d['name']}</div>
            <div style="font-size:1rem; opacity:0.85;">{d['ticker']} · {d['sector']} · {d['industry']}</div>
        </div>
        <div style="text-align:center; background:rgba(255,255,255,0.15);
                    border-radius:8px; padding:14px 28px;">
            <div style="font-size:0.75rem; opacity:0.8; letter-spacing:1px;">RECOMMENDATION</div>
            <div style="font-size:2.2rem; font-weight:900; letter-spacing:2px;">{rec}</div>
            <div style="font-size:0.85rem; opacity:0.85;">Conviction: {d['conviction']} / 10</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.8rem; opacity:0.8;">
                Current Price
                <span style="background:#22c55e; color:white; font-size:0.65rem; font-weight:700;
                             padding:2px 7px; border-radius:20px; margin-left:6px; letter-spacing:1px;">
                    ● LIVE
                </span>
            </div>
            <div style="font-size:1.8rem; font-weight:700;">{fmt_large(d.get('price'), sym)}</div>
            <div style="font-size:0.9rem; opacity:0.85;">Target: {fmt_large(d.get('target_mean'), sym)}
                <span style="background:rgba(255,255,255,0.2); padding:2px 8px; border-radius:10px;">
                    {upside_str}
                </span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# KPI METRICS ROW
# ---------------------------------------------------------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)

def metric_card(col, label, value, sub=""):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

metric_card(k1, "Market Cap", fmt_large(d.get("market_cap"), sym), d.get("exchange", ""))
metric_card(k2, "Revenue (LTM)", fmt_large(d.get("latest_rev"), sym),
            f"Growth: {fmt_pct(d.get('latest_rev_growth'))}")
metric_card(k3, "FCF Margin", fmt_pct(d.get("fcf_margin")),
            f"FCF: {fmt_large(d.get('latest_fcf'), sym)}")
metric_card(k4, "EV/EBITDA", fmt_num(d.get("ev_to_ebitda"), suffix="x"),
            f"P/E: {fmt_num(d.get('trailing_pe'), suffix='x')}")
metric_card(k5, "Net Cash/(Debt)",
            fmt_large(d.get("net_cash"), sym),
            f"D/E: {fmt_num(d.get('debt_to_equity'), suffix='x')}")
metric_card(k6, "Quality Score", f"{d.get('composite_score')} / 10",
            f"Moat: {d.get('moat_label')}")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "📋 Overview",
    "💰 Revenue",
    "📈 Profitability",
    "🏦 Balance Sheet",
    "💵 Cash Flow",
    "⚖️ Valuation",
    "🎯 Scenarios",
    "⚠️ Risks & Catalysts",
    "📄 Full Report",
])

# ============================================================
# TAB 1: OVERVIEW
# ============================================================
with tabs[0]:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-header">Business Description</div>', unsafe_allow_html=True)
        st.write(d.get("description", "No description available.")[:1000])

        st.markdown('<div class="section-header">Company Profile</div>', unsafe_allow_html=True)
        profile_items = [
            ("Company",   d["name"]),
            ("Ticker",    d["ticker"]),
            ("Sector",    d["sector"]),
            ("Industry",  d["industry"]),
            ("Country",   d.get("country", "N/A")),
            ("Employees", f"{d.get('employees'):,}" if d.get("employees") else "N/A"),
            ("Exchange",  d.get("exchange", "N/A")),
            ("Currency",  d.get("currency", "N/A")),
        ]
        profile_html = "<table style='width:100%; border-collapse:collapse;'>"
        for i, (field, value) in enumerate(profile_items):
            bg = "#1c1c1c" if i % 2 == 0 else "#161616"
            profile_html += f"""
            <tr style="background:{bg};">
                <td style="padding:7px 10px; color:#c8a951; font-size:0.8rem;
                           font-weight:600; width:38%; border-bottom:1px solid #2a2a2a;">
                    {field}
                </td>
                <td style="padding:7px 10px; color:#f0e094; font-size:0.8rem;
                           border-bottom:1px solid #2a2a2a;">
                    {value}
                </td>
            </tr>"""
        profile_html += "</table>"
        st.markdown(profile_html, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-header">Quality Scorecard</div>', unsafe_allow_html=True)
        score_items = [
            ("Business Quality", d['business_quality_score'], ""),
            ("Balance Sheet",    d['balance_sheet_score'],    ""),
            ("Cash Flow Quality",d['cashflow_quality_score'], ""),
            ("Economic Moat",    d['moat_score'],             d['moat_label']),
            ("Management",       d['mgmt_score'],             ""),
            ("COMPOSITE",        d['composite_score'],        ""),
        ]
        rows_html = ""
        for label, score, sub in score_items:
            score_num = float(score) if score else 0
            bar_pct = score_num / 10 * 100
            bar_color = "#3dba70" if score_num >= 7 else ("#c8a951" if score_num >= 5 else "#e05555")
            is_composite = label == "COMPOSITE"
            rows_html += f"""
            <div style="margin-bottom:8px; padding:8px 10px;
                        background:{'#252510' if is_composite else '#1c1c1c'};
                        border:1px solid {'#c8a951' if is_composite else '#2a2a2a'};
                        border-radius:6px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                    <span style="color:#c8a951; font-size:0.78rem; font-weight:{'900' if is_composite else '600'};">
                        {label}
                    </span>
                    <span style="color:#f0e094; font-size:0.78rem; font-weight:700;">
                        {score} / 10 {'· ' + sub if sub else ''}
                    </span>
                </div>
                <div style="background:#2a2a2a; border-radius:3px; height:5px;">
                    <div style="background:{bar_color}; width:{bar_pct:.0f}%; height:5px; border-radius:3px;"></div>
                </div>
            </div>"""
        st.markdown(rows_html, unsafe_allow_html=True)

        st.markdown('<div class="section-header">52-Week Range</div>', unsafe_allow_html=True)
        w_low = d.get("week_52_low")
        w_high = d.get("week_52_high")
        price = d.get("price")
        if w_low and w_high and price:
            pct_range = (price - w_low) / (w_high - w_low) * 100 if (w_high - w_low) != 0 else 50
            st.markdown(f"""
            <div style='background:#eef2f8; border-radius:6px; padding:12px;'>
                <div style='display:flex; justify-content:space-between;'>
                    <span style='color:#c0392b; font-weight:700;'>{sym}{w_low:.2f}</span>
                    <span style='color:#003366; font-weight:700; font-size:1.1rem;'>{sym}{price:.2f}</span>
                    <span style='color:#1a7a4a; font-weight:700;'>{sym}{w_high:.2f}</span>
                </div>
                <div style='background:#dee2e6; border-radius:4px; height:8px; margin:8px 0;'>
                    <div style='background:#003366; height:8px; border-radius:4px; width:{pct_range:.1f}%;'></div>
                </div>
                <div style='text-align:center; font-size:0.8rem; color:#6c757d;'>
                    {pct_range:.1f}% of 52-week range · Beta: {fmt_num(d.get('beta'))}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Price chart
    st.markdown('<div class="section-header">1-Year Price Chart</div>', unsafe_allow_html=True)
    st.plotly_chart(price_chart(d), use_container_width=True)

    # Radar
    st.markdown('<div class="section-header">Quality Radar</div>', unsafe_allow_html=True)
    st.plotly_chart(score_radar_chart(d), use_container_width=True)

# ============================================================
# TAB 2: REVENUE
# ============================================================
with tabs[1]:
    st.markdown('<div class="section-header">Revenue History & Growth</div>', unsafe_allow_html=True)
    st.plotly_chart(revenue_chart(d), use_container_width=True)

    rev = d.get("revenue_hist", {})
    growth = d.get("revenue_growth", {})
    if rev:
        years = sorted(rev.keys())
        rows = []
        for y in years:
            gp = d.get("gross_profit_hist", {}).get(y)
            gm = d.get("gross_margins", {}).get(y)
            g = growth.get(y)
            rows.append({
                "Year": y,
                "Revenue": fmt_large(rev.get(y), sym),
                "YoY Growth": fmt_pct(g) if g is not None else "N/A",
                "Gross Profit": fmt_large(gp, sym) if gp else "N/A",
                "Gross Margin": fmt_pct(gm) if gm else "N/A",
            })
        dark_table(rows)
    for i, cat in enumerate(d.get("catalysts", []), 1):
        st.markdown(f"**{i}.** {cat}")

# ============================================================
# TAB 3: PROFITABILITY
# ============================================================
with tabs[2]:
    st.plotly_chart(margin_chart(d), use_container_width=True)

    years = sorted(d.get("gross_margins", {}).keys())
    if years:
        rows = []
        for y in years:
            rows.append({
                "Year": y,
                "Gross Margin": fmt_pct(d["gross_margins"].get(y)),
                "Operating Margin": fmt_pct(d["operating_margins"].get(y)),
                "Net Margin": fmt_pct(d["net_margins"].get(y)),
            })
        dark_table(rows)

    col1, col2, col3 = st.columns(3)
    col1.metric("ROE", fmt_pct(d.get("roe")))
    col2.metric("ROIC", fmt_pct(d.get("roic")))
    col3.metric("Operating Margin (Latest)", fmt_pct(d.get("latest_om")))

# ============================================================
# TAB 4: BALANCE SHEET
# ============================================================
with tabs[3]:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">Balance Sheet Summary</div>', unsafe_allow_html=True)
        bs_rows = {
            "Total Debt": fmt_large(d.get("total_debt"), sym),
            "Cash & Equivalents": fmt_large(d.get("cash"), sym),
            "Net Cash / (Debt)": fmt_large(d.get("net_cash"), sym),
            "Total Equity": fmt_large(d.get("equity"), sym),
            "Total Assets": fmt_large(d.get("total_assets"), sym),
            "Current Assets": fmt_large(d.get("current_assets"), sym),
            "Current Liabilities": fmt_large(d.get("current_liabilities"), sym),
        }
        dark_table([{"Metric": k, "Value": v} for k, v in bs_rows.items()])

    with col2:
        st.markdown('<div class="section-header">Key Ratios</div>', unsafe_allow_html=True)
        ratio_rows = {
            "Debt-to-Equity": fmt_num(d.get("debt_to_equity"), suffix="x"),
            "Current Ratio": fmt_num(d.get("current_ratio"), suffix="x"),
            "Interest Coverage": fmt_num(d.get("interest_coverage"), suffix="x"),
            "ROE": fmt_pct(d.get("roe")),
            "ROIC": fmt_pct(d.get("roic")),
            "Balance Sheet Score": f"{d.get('balance_sheet_score')} / 10",
        }
        dark_table([{"Ratio": k, "Value": v} for k, v in ratio_rows.items()])

        # Net cash meter
        net_cash = d.get("net_cash")
        if net_cash is not None:
            net_cash_label = "NET CASH" if net_cash >= 0 else "NET DEBT"
            net_cash_color = "#1a7a4a" if net_cash >= 0 else "#c0392b"
            st.markdown(f"""
            <div style='background:{net_cash_color}; color:white; border-radius:8px;
                        padding:14px; text-align:center; margin-top:10px;'>
                <div style='font-size:0.8rem; opacity:0.85;'>{net_cash_label}</div>
                <div style='font-size:1.6rem; font-weight:900;'>{fmt_large(abs(net_cash), sym)}</div>
            </div>
            """, unsafe_allow_html=True)

# ============================================================
# TAB 5: CASH FLOW
# ============================================================
with tabs[4]:
    st.plotly_chart(fcf_chart(d), use_container_width=True)

    fcf = d.get("fcf_hist", {})
    ocf = d.get("ocf_hist", {})
    capex = d.get("capex_hist", {})
    if fcf:
        years_cf = sorted(fcf.keys())
        rows = []
        for y in years_cf:
            rev_y = d.get("revenue_hist", {}).get(y)
            fcf_y = fcf.get(y)
            fcf_m = (fcf_y / rev_y) if (fcf_y and rev_y and rev_y != 0) else None
            rows.append({
                "Year": y,
                "Operating CF": fmt_large(ocf.get(y), sym),
                "CapEx": fmt_large(abs(capex.get(y)) if capex.get(y) else None, sym),
                "Free Cash Flow": fmt_large(fcf_y, sym),
                "FCF Margin": fmt_pct(fcf_m),
            })
        dark_table(rows)

    col1, col2, col3 = st.columns(3)
    col1.metric("FCF Yield", fmt_pct(d.get("fcf_yield")))
    col2.metric("FCF Margin (Latest)", fmt_pct(d.get("fcf_margin")))
    col3.metric("Cash Flow Quality Score", f"{d.get('cashflow_quality_score')} / 10")

# ============================================================
# TAB 6: VALUATION
# ============================================================
with tabs[5]:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.plotly_chart(valuation_bar_chart(d), use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">Valuation Metrics</div>', unsafe_allow_html=True)
        val_rows = {
            "Trailing P/E": fmt_num(d.get("trailing_pe"), suffix="x"),
            "Forward P/E": fmt_num(d.get("forward_pe"), suffix="x"),
            "EV/EBITDA": fmt_num(d.get("ev_to_ebitda"), suffix="x"),
            "Price/Sales": fmt_num(d.get("price_to_sales"), suffix="x"),
            "Price/Book": fmt_num(d.get("price_to_book"), suffix="x"),
            "PEG Ratio": fmt_num(d.get("peg_ratio"), suffix="x"),
            "FCF Yield": fmt_pct(d.get("fcf_yield")),
            "Dividend Yield": fmt_pct(d.get("dividend_yield")),
        }
        dark_table([{"Metric": k, "Value": v} for k, v in val_rows.items()])

        # Valuation verdict badge
        verdict = d.get("valuation_verdict", "Fairly Valued")
        v_color = {"Undervalued": "#1a7a4a", "Fairly Valued": "#b8860b", "Overvalued": "#c0392b"}.get(verdict, "#003366")
        st.markdown(f"""
        <div style='background:{v_color}; color:white; border-radius:8px;
                    padding:14px; text-align:center; margin-top:10px;'>
            <div style='font-size:0.8rem; opacity:0.85;'>VALUATION VERDICT</div>
            <div style='font-size:1.4rem; font-weight:900;'>{verdict}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Analyst Consensus</div>', unsafe_allow_html=True)
    col3, col4, col5 = st.columns(3)
    col3.metric("Consensus Target", fmt_large(d.get("target_mean"), sym))
    col4.metric("High / Low Target",
                f"{fmt_large(d.get('target_high'), sym)} / {fmt_large(d.get('target_low'), sym)}")
    col5.metric("Analyst Count", d.get("analyst_count", "N/A"))

# ============================================================
# TAB 7: SCENARIOS
# ============================================================
with tabs[6]:
    st.plotly_chart(scenario_chart(d), use_container_width=True)

    scenarios = d.get("scenarios")
    if scenarios:
        scenario_rows = [
            {"Scenario": "BEAR CASE", "Probability": scenarios["bear"]["prob"], "Rev Growth": scenarios["bear"]["growth"], "Op. Margin": scenarios["bear"]["margin"], "Multiple": scenarios["bear"]["multiple"], "Price Target": f"{sym}{scenarios['bear']['target']:.2f}", "Expected Return": scenarios["bear"]["return"]},
            {"Scenario": "BASE CASE", "Probability": scenarios["base"]["prob"], "Rev Growth": scenarios["base"]["growth"], "Op. Margin": scenarios["base"]["margin"], "Multiple": scenarios["base"]["multiple"], "Price Target": f"{sym}{scenarios['base']['target']:.2f}", "Expected Return": scenarios["base"]["return"]},
            {"Scenario": "BULL CASE", "Probability": scenarios["bull"]["prob"], "Rev Growth": scenarios["bull"]["growth"], "Op. Margin": scenarios["bull"]["margin"], "Multiple": scenarios["bull"]["multiple"], "Price Target": f"{sym}{scenarios['bull']['target']:.2f}", "Expected Return": scenarios["bull"]["return"]},
        ]
        dark_table(scenario_rows)

        pw = d.get("pw_target")
        if pw:
            st.info(f"**Probability-Weighted 12-Month Target: {sym}{pw:.2f}**")

# ============================================================
# TAB 8: RISKS & CATALYSTS
# ============================================================
with tabs[7]:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">⚠️ Key Risks</div>', unsafe_allow_html=True)
        risk_levels = ["🔴 CRITICAL", "🔴 HIGH", "🟠 HIGH", "🟡 MEDIUM", "🟡 MEDIUM"]
        for i, risk in enumerate(d.get("risks", []), 1):
            level = risk_levels[i - 1] if i <= len(risk_levels) else "🟡 MEDIUM"
            with st.expander(f"{level} — Risk {i}"):
                st.write(risk)

    with col2:
        st.markdown('<div class="section-header">🚀 Key Catalysts</div>', unsafe_allow_html=True)
        impact_levels = ["⭐⭐⭐ Very High", "⭐⭐⭐ Very High", "⭐⭐ High", "⭐⭐ High", "⭐ Medium"]
        for i, cat in enumerate(d.get("catalysts", []), 1):
            impact = impact_levels[i - 1] if i <= len(impact_levels) else "⭐ Medium"
            with st.expander(f"Catalyst {i} — {impact}"):
                st.write(cat)

# ============================================================
# TAB 9: FULL REPORT
# ============================================================
with tabs[8]:
    st.markdown('<div class="section-header">Full Institutional Research Report</div>',
                unsafe_allow_html=True)
    st.markdown(f"""
---
## {d['name']} ({d['ticker']}) — Equity Research Report
**Date:** {d['report_date']} | **Sector:** {d['sector']} | **Industry:** {d['industry']}

---
### EXECUTIVE SUMMARY

| Field | Value |
|---|---|
| **Company** | {d['name']} |
| **Ticker** | {d['ticker']} |
| **Current Price** | {fmt_large(d.get('price'), sym)} |
| **Market Cap** | {fmt_large(d.get('market_cap'), sym)} |
| **Recommendation** | **{rec}** |
| **Conviction** | {d.get('conviction')} / 10 |
| **Fair Value** | {fmt_large(d.get('fair_value'), sym)} |
| **Analyst Target** | {fmt_large(d.get('target_mean'), sym)} |
| **Upside** | {upside_str} |
| **52-Week Range** | {fmt_large(d.get('week_52_low'), sym)} — {fmt_large(d.get('week_52_high'), sym)} |
| **Beta** | {fmt_num(d.get('beta'))} |

---
### 1. BUSINESS OVERVIEW
**Business Quality Score: {d['business_quality_score']} / 10**

{d.get('description', 'N/A')}

---
### 2. PROFITABILITY

| Year | Gross Margin | Operating Margin | Net Margin |
|---|---|---|---|
""" + "\n".join([
        f"| {y} | {fmt_pct(d['gross_margins'].get(y))} | {fmt_pct(d['operating_margins'].get(y))} | {fmt_pct(d['net_margins'].get(y))} |"
        for y in sorted(d.get('gross_margins', {}).keys())
    ]) + f"""

**ROE:** {fmt_pct(d.get('roe'))} | **ROIC:** {fmt_pct(d.get('roic'))}

---
### 3. BALANCE SHEET

| Metric | Value |
|---|---|
| Total Debt | {fmt_large(d.get('total_debt'), sym)} |
| Cash | {fmt_large(d.get('cash'), sym)} |
| **Net Cash / (Debt)** | **{fmt_large(d.get('net_cash'), sym)}** |
| Debt-to-Equity | {fmt_num(d.get('debt_to_equity'), suffix='x')} |
| Current Ratio | {fmt_num(d.get('current_ratio'), suffix='x')} |
| Interest Coverage | {fmt_num(d.get('interest_coverage'), suffix='x')} |
| **Balance Sheet Score** | **{d.get('balance_sheet_score')} / 10** |

---
### 4. CASH FLOW

| Metric | Value |
|---|---|
| Latest FCF | {fmt_large(d.get('latest_fcf'), sym)} |
| FCF Margin | {fmt_pct(d.get('fcf_margin'))} |
| FCF Yield | {fmt_pct(d.get('fcf_yield'))} |
| **Cash Flow Quality Score** | **{d.get('cashflow_quality_score')} / 10** |

---
### 5. VALUATION

| Multiple | Current |
|---|---|
| Trailing P/E | {fmt_num(d.get('trailing_pe'), suffix='x')} |
| Forward P/E | {fmt_num(d.get('forward_pe'), suffix='x')} |
| EV/EBITDA | {fmt_num(d.get('ev_to_ebitda'), suffix='x')} |
| Price/Sales | {fmt_num(d.get('price_to_sales'), suffix='x')} |
| Price/Book | {fmt_num(d.get('price_to_book'), suffix='x')} |
| PEG Ratio | {fmt_num(d.get('peg_ratio'), suffix='x')} |
| FCF Yield | {fmt_pct(d.get('fcf_yield'))} |
| **Verdict** | **{d.get('valuation_verdict')}** |

---
### 6. ECONOMIC MOAT
**Moat Score: {d.get('moat_score')} / 10 — {d.get('moat_label')}**

---
### 7. SCENARIO ANALYSIS
""" + ("""
| Scenario | Probability | Rev Growth | Op Margin | Target | Return |
|---|---|---|---|---|---|
""" + "\n".join([
        f"| {s.upper()} | {scenarios[s]['prob']} | {scenarios[s]['growth']} | {scenarios[s]['margin']} | {sym}{scenarios[s]['target']:.2f} | {scenarios[s]['return']} |"
        for s in ["bear", "base", "bull"]
    ]) + f"\n\n**Probability-Weighted Target: {sym}{d.get('pw_target', 'N/A')}**" if scenarios else "Insufficient data.") + f"""

---
### 8. KEY RISKS
""" + "\n".join([f"{i}. {r}" for i, r in enumerate(d.get("risks", []), 1)]) + f"""

---
### 9. KEY CATALYSTS
""" + "\n".join([f"{i}. {c}" for i, c in enumerate(d.get("catalysts", []), 1)]) + f"""

---
### 10. FINAL CONCLUSION

**Recommendation: {rec} | Conviction: {d.get('conviction')}/10 | Composite Score: {d.get('composite_score')}/10**

*For institutional use only. Data sourced from Yahoo Finance. Not investment advice.*
""")

    # -----------------------------------------------------------------------
    # PDF DOWNLOAD
    # -----------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📥 Download Report as PDF")

    if st.button("🖨️ Generate PDF Report", type="primary"):
        with st.spinner("Generating PDF..."):
            try:
                import tempfile
                tmp_path = os.path.join(tempfile.gettempdir(), f"report_{d['ticker']}.pdf")
                pdf_path = generate_pdf(d, tmp_path)
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label=f"📄 Download {d['ticker']} Research Report PDF",
                    data=pdf_bytes,
                    file_name=f"{d['ticker']}_equity_research_{d['report_date'].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success("✅ PDF ready! Click the button above to download.")
            except Exception as e:
                st.error(f"PDF generation failed: {str(e)}")
                st.code(traceback.format_exc())

# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#6c757d; font-size:0.78rem; padding:10px;">
    <b>Equity Research Dashboard</b> · Data: Yahoo Finance (yfinance) ·
    For Informational Purposes Only · Not Investment Advice ·
    Goldman Sachs branding used for illustrative purposes only
</div>
""", unsafe_allow_html=True)
