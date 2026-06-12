"""
report_generator.py
Fetches data from Yahoo Finance via yfinance and computes all metrics
for the institutional equity research report.
"""
import streamlit as st

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

# ---------------------------------------------------------------------------
# SECTOR PEER MAP
# ---------------------------------------------------------------------------
SECTOR_PEERS = {
    "Technology": ["MSFT", "ORCL", "CRM", "NOW", "WDAY"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "SNAP"],
    "Consumer Cyclical": ["AMZN", "TSLA", "NKE", "MCD", "SBUX"],
    "Consumer Defensive": ["PG", "KO", "PEP", "WMT", "COST"],
    "Healthcare": ["JNJ", "UNH", "LLY", "PFE", "ABBV"],
    "Financials": ["JPM", "BAC", "GS", "MS", "V"],
    "Industrials": ["GE", "HON", "MMM", "CAT", "BA"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "PSX"],
    "Materials": ["LIN", "APD", "ECL", "NEM", "FCX"],
    "Real Estate": ["AMT", "PLD", "CCI", "SPG", "EQIX"],
    "Utilities": ["NEE", "DUK", "SO", "AEP", "EXC"],
}

# ---------------------------------------------------------------------------
# SECTOR RISK TEMPLATES
# ---------------------------------------------------------------------------
SECTOR_RISKS = {
    "Technology": [
        "Rapid technology obsolescence and AI disruption risk",
        "Intense competition from hyperscalers (AWS, Azure, GCP)",
        "Cybersecurity / data privacy regulatory exposure (GDPR, AI Act)",
        "Talent retention in competitive engineering labor market",
        "Customer concentration risk in enterprise software",
    ],
    "Healthcare": [
        "FDA approval / clinical trial failure risk",
        "Drug pricing regulation and Medicare negotiation exposure",
        "Patent cliff / generic competition risk",
        "Product liability and litigation exposure",
        "Reimbursement rate pressure from payers",
    ],
    "Financials": [
        "Net interest margin compression in declining rate environment",
        "Credit loss provisions in economic slowdown",
        "Regulatory capital requirement increases (Basel III endgame)",
        "Fintech disruption to traditional revenue streams",
        "Macro sensitivity: recessions directly impair loan books",
    ],
    "Consumer Cyclical": [
        "Consumer spending slowdown in recession",
        "Input cost inflation (commodities, logistics, labor)",
        "Inventory management and supply chain disruption",
        "Brand erosion from competitive pricing pressure",
        "E-commerce structural disruption to physical retail",
    ],
    "Energy": [
        "Commodity price volatility (oil, gas, renewables pricing)",
        "Energy transition / stranded asset risk",
        "Geopolitical supply disruption",
        "Environmental regulation and carbon pricing",
        "Capital intensity and execution risk on major projects",
    ],
}

DEFAULT_RISKS = [
    "Macroeconomic slowdown compressing revenue growth",
    "Premium valuation multiple compression on guidance miss",
    "Competitive displacement by well-funded new entrants",
    "Currency headwinds on international revenue",
    "Key management departure and succession risk",
]

# ---------------------------------------------------------------------------
# SECTOR CATALYST TEMPLATES
# ---------------------------------------------------------------------------
SECTOR_CATALYSTS = {
    "Technology": [
        "Upcoming earnings — cloud revenue acceleration signal",
        "New product / AI feature launch at annual developer conference",
        "Customer win announcements vs. primary competitor",
        "Operating margin guidance raise at investor day",
        "Share buyback acceleration signaling management confidence",
    ],
    "Healthcare": [
        "FDA approval decision on lead pipeline candidate",
        "Phase III clinical trial data readout",
        "Drug pricing negotiation outcome",
        "M&A or licensing deal announcement",
        "Earnings beat driven by blockbuster drug sales",
    ],
    "Financials": [
        "Federal Reserve rate decision and guidance",
        "Quarterly earnings — net interest income trajectory",
        "Credit quality improvement in loan book",
        "Capital return program increase (buyback / dividend raise)",
        "Regulatory approval for new product or market entry",
    ],
}

DEFAULT_CATALYSTS = [
    "Quarterly earnings beat and forward guidance raise",
    "New product launch driving incremental revenue",
    "Share buyback announcement or acceleration",
    "Strategic partnership or major customer win",
    "Analyst upgrade from major institutional broker",
]


# ---------------------------------------------------------------------------
# HELPER: safe get from dict
# ---------------------------------------------------------------------------
def sg(d, key, default=None):
    try:
        val = d.get(key, default)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return val
    except Exception:
        return default


def fmt_num(val, decimals=2, suffix=""):
    if val is None:
        return "N/A"
    try:
        return f"{val:,.{decimals}f}{suffix}"
    except Exception:
        return "N/A"


def fmt_pct(val, decimals=1):
    if val is None:
        return "N/A"
    try:
        return f"{val * 100:.{decimals}f}%"
    except Exception:
        return "N/A"


def fmt_large(val, currency="$"):
    """Format large numbers as B/M with currency prefix."""
    if val is None:
        return "N/A"
    try:
        if abs(val) >= 1e12:
            return f"{currency}{val/1e12:.2f}T"
        elif abs(val) >= 1e9:
            return f"{currency}{val/1e9:.2f}B"
        elif abs(val) >= 1e6:
            return f"{currency}{val/1e6:.2f}M"
        else:
            return f"{currency}{val:,.0f}"
    except Exception:
        return "N/A"


# ---------------------------------------------------------------------------
# COMPANY NAME / TICKER SEARCH
# ---------------------------------------------------------------------------
def search_ticker(query: str) -> list[dict]:
    """
    Search for tickers matching a company name or partial ticker.
    Returns list of dicts: [{ticker, name, exchange, type}]
    Uses yfinance Search + Lookup (no API key required).
    """
    out = []
    seen = set()

    # Primary: yf.Search (best for partial names and tickers)
    try:
        results = yf.Search(query, max_results=8)
        for q in (results.quotes or []):
            t = q.get("symbol", "")
            n = q.get("longname") or q.get("shortname") or t
            ex = q.get("exchDisp") or q.get("exchange", "")
            qt = q.get("quoteType", "")
            if t and qt in ("EQUITY", "ETF") and t not in seen:
                out.append({"ticker": t, "name": n, "exchange": ex, "type": qt})
                seen.add(t)
    except Exception:
        pass

    # Fallback: yf.Lookup (better for full company names)
    if not out:
        try:
            lk = yf.Lookup(query)
            df = lk.get_all()
            for _, row in df.head(6).iterrows():
                t = row.name if hasattr(row, "name") else row.get("symbol", "")
                n = row.get("longName") or row.get("shortName") or t
                ex = row.get("exchange", "")
                if t and t not in seen:
                    out.append({"ticker": t, "name": n, "exchange": ex, "type": "EQUITY"})
                    seen.add(t)
        except Exception:
            pass

    return out


def resolve_input(raw: str) -> tuple[str, list[dict]]:
    """
    Given raw user input, determine if it looks like a ticker or a name.
    Returns (resolved_ticker, candidates).
    - If input looks exactly like a ticker (≤6 chars, no spaces, all-caps or digits), return directly.
    - Otherwise search and return top matches for the user to pick.
    """
    clean = raw.strip()

    # Exactly a ticker: ≤6 chars, no spaces, all uppercase alphanumeric (allows . for exchange suffix)
    stripped = clean.replace(".", "").replace("-", "")
    is_ticker_like = (
        len(clean) <= 7
        and " " not in clean
        and stripped.isupper()
        and stripped.isalnum()
    )

    if is_ticker_like:
        return clean.upper(), []

    # Name or mixed input — search
    candidates = search_ticker(clean)
    if candidates:
        return candidates[0]["ticker"], candidates
    # Last resort: treat as ticker
    return clean.upper(), []


# ---------------------------------------------------------------------------
# MAIN DATA FETCHER
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def fetch_stock_data(ticker_symbol: str) -> dict:
    """
    Fetches all data from yfinance and computes derived metrics.
    Returns a structured dict consumed by the UI and PDF exporter.
    """
    ticker_symbol = ticker_symbol.strip().upper()
    t = yf.Ticker(ticker_symbol)

    # Retry up to 3 times on rate limit
    info = {}
    for attempt in range(3):
        try:
            info = t.info or {}
            if info and isinstance(info, dict) and len(info) > 1:
                break
        except Exception as e:
            if "too many requests" in str(e).lower() or "rate limit" in str(e).lower():
                if attempt < 2:
                    time.sleep(3 + attempt * 2)
                    continue
            raise
        if attempt < 2:
            time.sleep(2)

    if not info or not isinstance(info, dict) or len(info) <= 1:
        raise ValueError(f"Ticker '{ticker_symbol}' not found or data unavailable. Please check the symbol.")

    # -----------------------------------------------------------------------
    # BASIC INFO
    # -----------------------------------------------------------------------
    name = sg(info, "longName") or sg(info, "shortName") or ticker_symbol
    sector = sg(info, "sector", "Technology")
    industry = sg(info, "industry", "N/A")
    country = sg(info, "country", "N/A")
    employees = sg(info, "fullTimeEmployees")
    description = sg(info, "longBusinessSummary", "No description available.")
    currency = sg(info, "currency", "USD")
    currency_sym = "$" if currency == "USD" else currency + " "
    exchange = sg(info, "exchange", "")

    price = sg(info, "currentPrice") or sg(info, "regularMarketPrice") or sg(info, "previousClose")
    market_cap = sg(info, "marketCap")
    shares_outstanding = sg(info, "sharesOutstanding")

    week_52_high = sg(info, "fiftyTwoWeekHigh")
    week_52_low = sg(info, "fiftyTwoWeekLow")
    beta = sg(info, "beta")

    # -----------------------------------------------------------------------
    # VALUATION MULTIPLES (from yfinance)
    # -----------------------------------------------------------------------
    trailing_pe = sg(info, "trailingPE")
    forward_pe = sg(info, "forwardPE")
    peg_ratio = sg(info, "pegRatio")
    price_to_book = sg(info, "priceToBook")
    price_to_sales = sg(info, "priceToSalesTrailingTwelveMonths")
    ev_to_ebitda = sg(info, "enterpriseToEbitda")
    ev = sg(info, "enterpriseValue")
    dividend_yield = sg(info, "dividendYield")
    payout_ratio = sg(info, "payoutRatio")

    # Analyst consensus
    target_mean = sg(info, "targetMeanPrice")
    target_high = sg(info, "targetHighPrice")
    target_low = sg(info, "targetLowPrice")
    recommendation_mean = sg(info, "recommendationMean")  # 1=Strong Buy, 5=Sell
    recommendation_key = sg(info, "recommendationKey", "hold")
    analyst_count = sg(info, "numberOfAnalystOpinions", 0)

    upside = ((target_mean - price) / price * 100) if (target_mean and price) else None

    # -----------------------------------------------------------------------
    # FINANCIALS (income statement, balance sheet, cash flow)
    # -----------------------------------------------------------------------
    try:
        financials = t.financials  # columns = dates, rows = line items
    except Exception:
        financials = pd.DataFrame()

    try:
        balance_sheet = t.balance_sheet
    except Exception:
        balance_sheet = pd.DataFrame()

    try:
        cashflow = t.cashflow
    except Exception:
        cashflow = pd.DataFrame()

    # -----------------------------------------------------------------------
    # REVENUE & INCOME METRICS (multi-year)
    # -----------------------------------------------------------------------
    def get_row(df, *keys):
        """Try multiple key names, return series or None."""
        if df is None or df.empty:
            return None
        for key in keys:
            if key in df.index:
                return df.loc[key]
        return None

    rev_series = get_row(financials, "Total Revenue", "Revenue")
    gp_series = get_row(financials, "Gross Profit")
    op_series = get_row(financials, "Operating Income", "EBIT")
    ni_series = get_row(financials, "Net Income")
    ebitda_series = get_row(financials, "EBITDA", "Normalized EBITDA")

    def series_to_dict(series):
        if series is None:
            return {}
        result = {}
        for col, val in series.items():
            try:
                year = pd.Timestamp(col).year
                result[year] = float(val) if not pd.isna(val) else None
            except Exception:
                pass
        return dict(sorted(result.items()))

    revenue_hist = series_to_dict(rev_series)
    gross_profit_hist = series_to_dict(gp_series)
    operating_income_hist = series_to_dict(op_series)
    net_income_hist = series_to_dict(ni_series)

    # Compute margins
    def compute_margins(numerator_hist, revenue_hist):
        margins = {}
        for year in revenue_hist:
            rev = revenue_hist.get(year)
            num = numerator_hist.get(year)
            if rev and num and rev != 0:
                margins[year] = num / rev
            else:
                margins[year] = None
        return margins

    gross_margins = compute_margins(gross_profit_hist, revenue_hist)
    operating_margins = compute_margins(operating_income_hist, revenue_hist)
    net_margins = compute_margins(net_income_hist, revenue_hist)

    # Revenue growth YoY
    revenue_growth = {}
    rev_years = sorted(revenue_hist.keys())
    for i in range(1, len(rev_years)):
        y = rev_years[i]
        prev = revenue_hist.get(rev_years[i - 1])
        curr = revenue_hist.get(y)
        if prev and curr and prev != 0:
            revenue_growth[y] = (curr - prev) / abs(prev)
        else:
            revenue_growth[y] = None

    # -----------------------------------------------------------------------
    # BALANCE SHEET METRICS
    # -----------------------------------------------------------------------
    total_debt_series = get_row(balance_sheet, "Total Debt", "Long Term Debt And Capital Lease Obligation")
    cash_series = get_row(balance_sheet, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    equity_series = get_row(balance_sheet, "Stockholders Equity", "Total Equity Gross Minority Interest")
    current_assets_series = get_row(balance_sheet, "Current Assets", "Total Current Assets")
    current_liabilities_series = get_row(balance_sheet, "Current Liabilities", "Total Current Liabilities")
    total_assets_series = get_row(balance_sheet, "Total Assets")

    def latest(series):
        if series is None:
            return None
        try:
            vals = [v for v in series.values if not pd.isna(v)]
            return float(vals[0]) if vals else None
        except Exception:
            return None

    total_debt = latest(total_debt_series)
    cash = latest(cash_series)
    equity = latest(equity_series)
    current_assets = latest(current_assets_series)
    current_liabilities = latest(current_liabilities_series)
    total_assets = latest(total_assets_series)

    net_cash = (cash - total_debt) if (cash is not None and total_debt is not None) else None
    debt_to_equity = (total_debt / equity) if (total_debt and equity and equity != 0) else None
    current_ratio = (current_assets / current_liabilities) if (current_assets and current_liabilities and current_liabilities != 0) else None

    # ROIC estimate: EBIT*(1-tax) / (Equity + Debt - Cash)
    latest_oi = list(operating_income_hist.values())[-1] if operating_income_hist else None
    invested_capital = None
    roic = None
    if equity and total_debt and cash and latest_oi:
        invested_capital = equity + total_debt - cash
        if invested_capital and invested_capital != 0:
            roic = (latest_oi * 0.75) / invested_capital  # assume ~25% tax

    # ROE: Net Income / Equity
    latest_ni = list(net_income_hist.values())[-1] if net_income_hist else None
    roe = (latest_ni / equity) if (latest_ni and equity and equity != 0) else None

    # Interest coverage: EBIT / Interest Expense
    interest_series = get_row(financials, "Interest Expense", "Net Interest Income")
    latest_interest = abs(latest(interest_series)) if interest_series is not None else None
    interest_coverage = (latest_oi / latest_interest) if (latest_oi and latest_interest and latest_interest != 0) else None

    # -----------------------------------------------------------------------
    # CASH FLOW METRICS
    # -----------------------------------------------------------------------
    ocf_series = get_row(cashflow, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    capex_series = get_row(cashflow, "Capital Expenditure", "Purchase Of PPE")

    ocf_hist = series_to_dict(ocf_series)
    capex_hist = series_to_dict(capex_series)

    fcf_hist = {}
    for year in ocf_hist:
        ocf = ocf_hist.get(year)
        capex = capex_hist.get(year)
        if ocf is not None:
            fcf_hist[year] = ocf - abs(capex) if capex is not None else ocf
        else:
            fcf_hist[year] = None

    latest_rev = list(revenue_hist.values())[-1] if revenue_hist else None
    latest_fcf = list(fcf_hist.values())[-1] if fcf_hist else None
    latest_ocf = list(ocf_hist.values())[-1] if ocf_hist else None
    latest_capex = list(capex_hist.values())[-1] if capex_hist else None
    fcf_margin = (latest_fcf / latest_rev) if (latest_fcf and latest_rev and latest_rev != 0) else None
    fcf_yield = (latest_fcf / market_cap) if (latest_fcf and market_cap and market_cap != 0) else None

    # -----------------------------------------------------------------------
    # SCORING ENGINE
    # -----------------------------------------------------------------------
    def score_clamp(val, lo=1, hi=10):
        return max(lo, min(hi, round(val)))

    # Business Quality (1-10)
    biz_score = 5.0
    if latest_rev and latest_rev > 1e9:
        biz_score += 1.0
    latest_gm = list(gross_margins.values())[-1] if gross_margins else None
    if latest_gm and latest_gm > 0.6:
        biz_score += 1.0
    if latest_gm and latest_gm > 0.4:
        biz_score += 0.5
    latest_rev_growth = list(revenue_growth.values())[-1] if revenue_growth else None
    if latest_rev_growth and latest_rev_growth > 0.1:
        biz_score += 1.0
    elif latest_rev_growth and latest_rev_growth > 0.05:
        biz_score += 0.5
    if ev_to_ebitda and ev_to_ebitda < 30:
        biz_score += 0.5
    business_quality_score = score_clamp(biz_score)

    # Balance Sheet Quality (1-10)
    bs_score = 5.0
    if net_cash and net_cash > 0:
        bs_score += 2.0
    elif debt_to_equity and debt_to_equity < 0.5:
        bs_score += 1.0
    if current_ratio and current_ratio > 1.5:
        bs_score += 1.0
    elif current_ratio and current_ratio > 1.0:
        bs_score += 0.5
    if interest_coverage and interest_coverage > 10:
        bs_score += 1.5
    elif interest_coverage and interest_coverage > 5:
        bs_score += 0.5
    if debt_to_equity and debt_to_equity > 2.0:
        bs_score -= 2.0
    balance_sheet_score = score_clamp(bs_score)

    # Cash Flow Quality (1-10)
    cf_score = 5.0
    if fcf_margin and fcf_margin > 0.2:
        cf_score += 2.0
    elif fcf_margin and fcf_margin > 0.1:
        cf_score += 1.0
    if fcf_yield and fcf_yield > 0.04:
        cf_score += 1.0
    if latest_fcf and latest_ni and latest_ni != 0:
        conversion = latest_fcf / abs(latest_ni)
        if conversion > 1.2:
            cf_score += 1.5
        elif conversion > 0.9:
            cf_score += 0.5
    cashflow_quality_score = score_clamp(cf_score)

    # Moat Score (1-10) — proxy from margins + market position
    moat_score = 5.0
    if latest_gm and latest_gm > 0.6:
        moat_score += 1.5
    elif latest_gm and latest_gm > 0.4:
        moat_score += 0.5
    latest_om = list(operating_margins.values())[-1] if operating_margins else None
    if latest_om and latest_om > 0.2:
        moat_score += 1.0
    if roic and roic > 0.15:
        moat_score += 1.5
    elif roic and roic > 0.1:
        moat_score += 0.5
    if sector == "Technology":
        moat_score += 0.5
    moat_score_val = score_clamp(moat_score)

    # Management Score (1-10)
    mgmt_score = 6.0
    if dividend_yield and dividend_yield > 0:
        mgmt_score += 0.5
    if roic and roic > 0.12:
        mgmt_score += 1.0
    if roe and roe > 0.15:
        mgmt_score += 0.5
    mgmt_score_val = score_clamp(mgmt_score)

    # Composite
    composite_score = round(
        (business_quality_score + balance_sheet_score + cashflow_quality_score +
         moat_score_val + mgmt_score_val) / 5, 1
    )

    # -----------------------------------------------------------------------
    # RECOMMENDATION ENGINE
    # -----------------------------------------------------------------------
    def map_recommendation(rec_mean, rec_key, upside_pct):
        if rec_mean is None:
            rec_mean = 3.0
        if rec_mean <= 1.5:
            rec = "STRONG BUY"
            color = "#0a5c36"
            text_color = "white"
        elif rec_mean <= 2.2:
            rec = "BUY"
            color = "#1a7a4a"
            text_color = "white"
        elif rec_mean <= 2.8:
            rec = "BUY"
            color = "#1a7a4a"
            text_color = "white"
        elif rec_mean <= 3.5:
            rec = "HOLD"
            color = "#b8860b"
            text_color = "white"
        elif rec_mean <= 4.2:
            rec = "REDUCE"
            color = "#c0392b"
            text_color = "white"
        else:
            rec = "SELL"
            color = "#922b21"
            text_color = "white"

        # Override with upside if very compelling
        if upside_pct and upside_pct > 30 and rec == "HOLD":
            rec = "BUY"
            color = "#1a7a4a"

        return rec, color, text_color

    recommendation, rec_color, rec_text_color = map_recommendation(
        recommendation_mean, recommendation_key, upside
    )

    # Conviction (1-10) based on analyst consensus + FCF + growth
    conviction = 5
    if analyst_count and analyst_count >= 10:
        conviction += 1
    if fcf_yield and fcf_yield > 0.03:
        conviction += 1
    if latest_rev_growth and latest_rev_growth > 0.08:
        conviction += 1
    if upside and upside > 20:
        conviction += 1
    if recommendation_mean and recommendation_mean < 2.5:
        conviction += 1
    conviction = min(10, max(1, conviction))

    # Fair value estimate (use analyst target or DCF proxy)
    fair_value = target_mean
    if fair_value is None and price and latest_fcf and market_cap:
        # Simple DCF proxy: FCF * 25 growth multiple
        fair_value = (latest_fcf * 25) / (shares_outstanding or 1)

    # -----------------------------------------------------------------------
    # SCENARIO ANALYSIS
    # -----------------------------------------------------------------------
    def build_scenarios(price, ev_to_ebitda, latest_rev, latest_om, latest_rev_growth):
        if not price:
            return None

        base_growth = latest_rev_growth if latest_rev_growth else 0.08
        base_om = latest_om if latest_om else 0.15
        base_multiple = ev_to_ebitda if ev_to_ebitda else 20

        # Bear
        bear_growth = base_growth * 0.4
        bear_margin = base_om * 0.85
        bear_multiple = base_multiple * 0.7
        bear_target = price * (1 + bear_growth - 0.15) * (bear_multiple / base_multiple)

        # Base
        base_target = price * (1 + base_growth + 0.05)

        # Bull
        bull_growth = base_growth * 1.6
        bull_margin = base_om * 1.15
        bull_multiple = base_multiple * 1.3
        bull_target = price * (1 + bull_growth + 0.15) * (bull_multiple / base_multiple)

        return {
            "bear": {
                "growth": f"{bear_growth*100:.1f}%",
                "margin": f"{bear_margin*100:.1f}%",
                "multiple": f"{bear_multiple:.1f}x EV/EBITDA",
                "target": round(bear_target, 2),
                "return": f"{(bear_target/price - 1)*100:.1f}%",
                "prob": "25%",
            },
            "base": {
                "growth": f"{base_growth*100:.1f}%",
                "margin": f"{base_om*100:.1f}%",
                "multiple": f"{base_multiple:.1f}x EV/EBITDA",
                "target": round(base_target, 2),
                "return": f"{(base_target/price - 1)*100:.1f}%",
                "prob": "55%",
            },
            "bull": {
                "growth": f"{bull_growth*100:.1f}%",
                "margin": f"{bull_margin*100:.1f}%",
                "multiple": f"{bull_multiple:.1f}x EV/EBITDA",
                "target": round(bull_target, 2),
                "return": f"{(bull_target/price - 1)*100:.1f}%",
                "prob": "20%",
            },
        }

    scenarios = build_scenarios(price, ev_to_ebitda, latest_rev, latest_om, latest_rev_growth)

    # Probability-weighted target
    pw_target = None
    if scenarios:
        bt = scenarios["bear"]["target"]
        bst = scenarios["base"]["target"]
        bult = scenarios["bull"]["target"]
        pw_target = round(bt * 0.25 + bst * 0.55 + bult * 0.20, 2)

    # -----------------------------------------------------------------------
    # PEER DATA
    # -----------------------------------------------------------------------
    peers = SECTOR_PEERS.get(sector, ["SPY", "QQQ"])[:3]
    # Remove the ticker itself from peers
    peers = [p for p in peers if p != ticker_symbol][:3]

    # -----------------------------------------------------------------------
    # PRICE HISTORY
    # -----------------------------------------------------------------------
    try:
        hist_5y = t.history(period="5y")
        hist_1y = t.history(period="1y")
    except Exception:
        hist_5y = pd.DataFrame()
        hist_1y = pd.DataFrame()

    # -----------------------------------------------------------------------
    # MOAT LABEL
    # -----------------------------------------------------------------------
    if moat_score_val >= 8:
        moat_label = "Very Wide"
    elif moat_score_val >= 6:
        moat_label = "Wide"
    else:
        moat_label = "Narrow"

    # -----------------------------------------------------------------------
    # VALUATION VERDICT
    # -----------------------------------------------------------------------
    if ev_to_ebitda and trailing_pe:
        # Compare to rough sector averages
        tech_ev_avg = 25
        if ev_to_ebitda > tech_ev_avg * 1.3:
            valuation_verdict = "Overvalued"
        elif ev_to_ebitda > tech_ev_avg * 0.9:
            valuation_verdict = "Fairly Valued"
        else:
            valuation_verdict = "Undervalued"
    elif upside and upside > 20:
        valuation_verdict = "Undervalued"
    elif upside and upside < -10:
        valuation_verdict = "Overvalued"
    else:
        valuation_verdict = "Fairly Valued"

    # -----------------------------------------------------------------------
    # PACK RESULT
    # -----------------------------------------------------------------------
    return {
        # Identity
        "ticker": ticker_symbol,
        "name": name,
        "sector": sector,
        "industry": industry,
        "country": country,
        "employees": employees,
        "description": description,
        "currency": currency,
        "currency_sym": currency_sym,
        "exchange": exchange,
        "report_date": datetime.now().strftime("%B %d, %Y"),

        # Price & Market
        "price": price,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
        "week_52_high": week_52_high,
        "week_52_low": week_52_low,
        "beta": beta,

        # Recommendation
        "recommendation": recommendation,
        "rec_color": rec_color,
        "rec_text_color": rec_text_color,
        "conviction": conviction,
        "target_mean": target_mean,
        "target_high": target_high,
        "target_low": target_low,
        "fair_value": fair_value,
        "upside": upside,
        "recommendation_mean": recommendation_mean,
        "analyst_count": analyst_count,
        "pw_target": pw_target,

        # Valuation multiples
        "trailing_pe": trailing_pe,
        "forward_pe": forward_pe,
        "peg_ratio": peg_ratio,
        "price_to_book": price_to_book,
        "price_to_sales": price_to_sales,
        "ev_to_ebitda": ev_to_ebitda,
        "ev": ev,
        "dividend_yield": dividend_yield,
        "payout_ratio": payout_ratio,
        "fcf_yield": fcf_yield,
        "valuation_verdict": valuation_verdict,

        # Revenue & margins (historical)
        "revenue_hist": revenue_hist,
        "gross_profit_hist": gross_profit_hist,
        "operating_income_hist": operating_income_hist,
        "net_income_hist": net_income_hist,
        "revenue_growth": revenue_growth,
        "gross_margins": gross_margins,
        "operating_margins": operating_margins,
        "net_margins": net_margins,
        "latest_rev": latest_rev,
        "latest_rev_growth": latest_rev_growth,
        "latest_gm": latest_gm,
        "latest_om": latest_om,

        # Balance sheet
        "total_debt": total_debt,
        "cash": cash,
        "equity": equity,
        "net_cash": net_cash,
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "total_assets": total_assets,
        "roe": roe,
        "roic": roic,
        "interest_coverage": interest_coverage,

        # Cash flow
        "ocf_hist": ocf_hist,
        "capex_hist": capex_hist,
        "fcf_hist": fcf_hist,
        "latest_ocf": latest_ocf,
        "latest_capex": latest_capex,
        "latest_fcf": latest_fcf,
        "fcf_margin": fcf_margin,
        "latest_ni": latest_ni,

        # Scores
        "business_quality_score": business_quality_score,
        "balance_sheet_score": balance_sheet_score,
        "cashflow_quality_score": cashflow_quality_score,
        "moat_score": moat_score_val,
        "moat_label": moat_label,
        "mgmt_score": mgmt_score_val,
        "composite_score": composite_score,

        # Scenarios
        "scenarios": scenarios,

        # Templates
        "risks": SECTOR_RISKS.get(sector, DEFAULT_RISKS),
        "catalysts": SECTOR_CATALYSTS.get(sector, DEFAULT_CATALYSTS),

        # Peers & price history
        "peers": peers,
        "hist_5y": hist_5y,
        "hist_1y": hist_1y,
    }
