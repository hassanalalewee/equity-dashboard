"""
pdf_exporter.py
Generates a styled institutional equity research report PDF using fpdf2.
"""

from fpdf import FPDF
from datetime import datetime
import os


class ReportPDF(FPDF):
    def __init__(self, company_name, ticker):
        super().__init__()
        self.company_name = company_name
        self.ticker = ticker
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_fill_color(0, 51, 102)  # GS Blue
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(255, 255, 255)
        self.set_y(3)
        self.cell(0, 6, "Goldman Sachs Global Investment Research | Equity Research", align="C")
        self.set_text_color(0, 0, 0)
        self.set_y(16)

    def footer(self):
        self.set_y(-12)
        self.set_fill_color(0, 51, 102)
        self.rect(0, 285, 210, 12, "F")
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6,
                  f"CONFIDENTIAL — For Institutional Use Only | {self.company_name} ({self.ticker}) | "
                  f"Page {self.page_no()} | {datetime.now().strftime('%B %d, %Y')}",
                  align="C")
        self.set_text_color(0, 0, 0)

    def section_title(self, title):
        self.ln(4)
        self.set_fill_color(0, 51, 102)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f"  {title}", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(0, 51, 102)
        self.cell(0, 6, title, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def body_text(self, text, size=9):
        self.set_font("Helvetica", "", size)
        self.multi_cell(0, 5, str(text))
        self.ln(1)

    def kv_row(self, label, value, bold_value=False):
        self.set_font("Helvetica", "B", 9)
        self.cell(70, 6, label + ":", border="B")
        if bold_value:
            self.set_font("Helvetica", "B", 9)
        else:
            self.set_font("Helvetica", "", 9)
        self.cell(0, 6, str(value), border="B", ln=True)

    def table_header(self, cols, widths):
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        for col, w in zip(cols, widths):
            self.cell(w, 7, str(col), border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(0, 0, 0)

    def table_row(self, values, widths, fill=False):
        self.set_font("Helvetica", "", 8)
        if fill:
            self.set_fill_color(235, 241, 250)
        for val, w in zip(values, widths):
            self.cell(w, 6, str(val), border=1, fill=fill, align="C")
        self.ln()


def fmt(val, decimals=2, suffix="", prefix=""):
    if val is None:
        return "N/A"
    try:
        return f"{prefix}{val:,.{decimals}f}{suffix}"
    except Exception:
        return "N/A"


def fmt_pct(val):
    if val is None:
        return "N/A"
    try:
        return f"{val * 100:.1f}%"
    except Exception:
        return "N/A"


def fmt_large(val, sym="$"):
    if val is None:
        return "N/A"
    try:
        if abs(val) >= 1e12:
            return f"{sym}{val/1e12:.2f}T"
        elif abs(val) >= 1e9:
            return f"{sym}{val/1e9:.2f}B"
        elif abs(val) >= 1e6:
            return f"{sym}{val/1e6:.2f}M"
        return f"{sym}{val:,.0f}"
    except Exception:
        return "N/A"


def generate_pdf(d: dict, output_path: str = None) -> str:
    sym = d["currency_sym"]
    ticker = d["ticker"]
    name = d["name"]

    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), f"report_{ticker}.pdf")

    pdf = ReportPDF(name, ticker)
    pdf.add_page()

    # -----------------------------------------------------------------------
    # TITLE PAGE
    # -----------------------------------------------------------------------
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, name, ln=True, align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(200, 169, 81)
    pdf.cell(0, 8, f"({ticker}) — Institutional Equity Research", ln=True, align="C")
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Date: {d['report_date']}  |  Sector: {d['sector']}  |  Industry: {d['industry']}",
             ln=True, align="C")
    pdf.ln(4)

    # Recommendation banner
    rec = d["recommendation"]
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 14, f"RECOMMENDATION:  {rec}", fill=True, ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # Summary KV box
    pdf.section_title("EXECUTIVE SUMMARY")
    rows = [
        ("Company", name),
        ("Ticker", ticker),
        ("Exchange", d.get("exchange", "N/A")),
        ("Sector / Industry", f"{d['sector']} / {d['industry']}"),
        ("Current Price", fmt_large(d.get("price"), sym)),
        ("Market Capitalization", fmt_large(d.get("market_cap"), sym)),
        ("52-Week Range", f"{fmt_large(d.get('week_52_low'), sym)} — {fmt_large(d.get('week_52_high'), sym)}"),
        ("Beta", fmt(d.get("beta"))),
        ("Recommendation", rec),
        ("Conviction Level", f"{d.get('conviction')} / 10"),
        ("Fair Value Estimate", fmt_large(d.get("fair_value"), sym)),
        ("Analyst Consensus Target", fmt_large(d.get("target_mean"), sym)),
        ("Upside to Target", fmt_pct(d.get("upside", 0) / 100) if d.get("upside") else "N/A"),
        ("Composite Quality Score", f"{d.get('composite_score')} / 10"),
    ]
    for label, value in rows:
        bold = label in ("Recommendation", "Conviction Level", "Fair Value Estimate")
        pdf.kv_row(label, value, bold_value=bold)
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # KEY THESIS
    # -----------------------------------------------------------------------
    pdf.sub_title("Key Investment Thesis")
    thesis_points = [
        f"Strong free cash flow generation with FCF margin of {fmt_pct(d.get('fcf_margin'))} "
        f"supporting sustained capital returns and reinvestment.",
        f"Revenue growth trajectory of {fmt_pct(d.get('latest_rev_growth'))} YoY underpinned by "
        f"durable competitive positioning in {d['industry']}.",
        f"Quality business with composite score of {d.get('composite_score')}/10 — "
        f"{d.get('moat_label')} economic moat, investment-grade balance sheet, and "
        f"consistent margin profile.",
    ]
    for i, pt in enumerate(thesis_points, 1):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(8, 5, f"{i}.")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, pt)
    pdf.ln(2)

    # Key risks
    pdf.sub_title("Key Risks")
    for i, risk in enumerate(d.get("risks", [])[:3], 1):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(8, 5, f"{i}.")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, risk)
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # BUSINESS OVERVIEW
    # -----------------------------------------------------------------------
    pdf.section_title("1. BUSINESS OVERVIEW")
    pdf.body_text(d.get("description", "")[:800])
    rows2 = [
        ("Country of Domicile", d.get("country", "N/A")),
        ("Employees (Full-Time)", f"{d.get('employees'):,}" if d.get("employees") else "N/A"),
        ("Business Quality Score", f"{d.get('business_quality_score')} / 10"),
    ]
    for label, value in rows2:
        pdf.kv_row(label, value)
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # REVENUE ANALYSIS
    # -----------------------------------------------------------------------
    pdf.section_title("2. REVENUE ANALYSIS")
    rev = d.get("revenue_hist", {})
    growth = d.get("revenue_growth", {})
    if rev:
        years = sorted(rev.keys())
        cols = ["Year", "Revenue", "YoY Growth", "Gross Profit", "Gross Margin"]
        widths = [25, 38, 30, 38, 30]
        pdf.table_header(cols, widths)
        for i, y in enumerate(years):
            gp = d.get("gross_profit_hist", {}).get(y)
            gm = d.get("gross_margins", {}).get(y)
            g = growth.get(y)
            row = [
                str(y),
                fmt_large(rev.get(y), sym),
                fmt_pct(g) if g is not None else "N/A",
                fmt_large(gp, sym) if gp else "N/A",
                fmt_pct(gm) if gm else "N/A",
            ]
            pdf.table_row(row, widths, fill=(i % 2 == 0))
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # PROFITABILITY ANALYSIS
    # -----------------------------------------------------------------------
    pdf.section_title("3. PROFITABILITY ANALYSIS")
    years = sorted(d.get("gross_margins", {}).keys())
    if years:
        cols = ["Year", "Gross Margin", "Operating Margin", "Net Margin", "ROE", "ROIC"]
        widths = [22, 30, 32, 28, 28, 28]
        pdf.table_header(cols, widths)
        for i, y in enumerate(years):
            gm = d["gross_margins"].get(y)
            om = d["operating_margins"].get(y)
            nm = d["net_margins"].get(y)
            row = [
                str(y),
                fmt_pct(gm) if gm else "N/A",
                fmt_pct(om) if om else "N/A",
                fmt_pct(nm) if nm else "N/A",
                fmt_pct(d.get("roe")) if y == max(years) else "—",
                fmt_pct(d.get("roic")) if y == max(years) else "—",
            ]
            pdf.table_row(row, widths, fill=(i % 2 == 0))
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # BALANCE SHEET
    # -----------------------------------------------------------------------
    pdf.section_title("4. BALANCE SHEET STRENGTH")
    bs_rows = [
        ("Total Debt", fmt_large(d.get("total_debt"), sym)),
        ("Cash & Equivalents", fmt_large(d.get("cash"), sym)),
        ("Net Cash / (Debt)", fmt_large(d.get("net_cash"), sym)),
        ("Total Equity", fmt_large(d.get("equity"), sym)),
        ("Debt-to-Equity", fmt(d.get("debt_to_equity"), suffix="x")),
        ("Current Ratio", fmt(d.get("current_ratio"), suffix="x")),
        ("Interest Coverage", fmt(d.get("interest_coverage"), suffix="x")),
        ("Balance Sheet Score", f"{d.get('balance_sheet_score')} / 10"),
    ]
    for label, value in bs_rows:
        pdf.kv_row(label, value)
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # CASH FLOW
    # -----------------------------------------------------------------------
    pdf.section_title("5. CASH FLOW ANALYSIS")
    fcf = d.get("fcf_hist", {})
    ocf = d.get("ocf_hist", {})
    capex = d.get("capex_hist", {})
    if fcf:
        years_cf = sorted(fcf.keys())
        cols = ["Year", "Operating CF", "CapEx", "Free Cash Flow", "FCF Margin"]
        widths = [25, 38, 32, 38, 28]
        pdf.table_header(cols, widths)
        for i, y in enumerate(years_cf):
            rev_y = d.get("revenue_hist", {}).get(y)
            fcf_y = fcf.get(y)
            fcf_m = (fcf_y / rev_y) if (fcf_y and rev_y and rev_y != 0) else None
            row = [
                str(y),
                fmt_large(ocf.get(y), sym),
                fmt_large(abs(capex.get(y)) if capex.get(y) else None, sym),
                fmt_large(fcf_y, sym),
                fmt_pct(fcf_m) if fcf_m else "N/A",
            ]
            pdf.table_row(row, widths, fill=(i % 2 == 0))
    pdf.kv_row("Cash Flow Quality Score", f"{d.get('cashflow_quality_score')} / 10")
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # MOAT
    # -----------------------------------------------------------------------
    pdf.section_title("6. ECONOMIC MOAT & COMPETITIVE ADVANTAGE")
    pdf.kv_row("Moat Score", f"{d.get('moat_score')} / 10")
    pdf.kv_row("Moat Width", d.get("moat_label", "N/A"))
    pdf.kv_row("Gross Margin (Moat Proxy)", fmt_pct(d.get("latest_gm")))
    pdf.kv_row("ROIC (Capital Efficiency)", fmt_pct(d.get("roic")))
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # MANAGEMENT
    # -----------------------------------------------------------------------
    pdf.section_title("7. MANAGEMENT QUALITY")
    pdf.kv_row("Management Score", f"{d.get('mgmt_score')} / 10")
    pdf.kv_row("ROE (Return on Equity)", fmt_pct(d.get("roe")))
    pdf.kv_row("Dividend Yield", fmt_pct(d.get("dividend_yield")))
    pdf.kv_row("Payout Ratio", fmt_pct(d.get("payout_ratio")))
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # VALUATION
    # -----------------------------------------------------------------------
    pdf.section_title("8. VALUATION ANALYSIS")
    val_rows = [
        ("Trailing P/E", fmt(d.get("trailing_pe"), suffix="x")),
        ("Forward P/E", fmt(d.get("forward_pe"), suffix="x")),
        ("EV/EBITDA", fmt(d.get("ev_to_ebitda"), suffix="x")),
        ("Price/Sales", fmt(d.get("price_to_sales"), suffix="x")),
        ("Price/Book", fmt(d.get("price_to_book"), suffix="x")),
        ("PEG Ratio", fmt(d.get("peg_ratio"), suffix="x")),
        ("FCF Yield", fmt_pct(d.get("fcf_yield"))),
        ("Valuation Verdict", d.get("valuation_verdict", "N/A")),
    ]
    for label, value in val_rows:
        pdf.kv_row(label, value, bold_value=(label == "Valuation Verdict"))
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # SCENARIO ANALYSIS
    # -----------------------------------------------------------------------
    pdf.section_title("9. SCENARIO ANALYSIS")
    scenarios = d.get("scenarios")
    if scenarios:
        cols = ["Scenario", "Probability", "Rev Growth", "Op Margin", "Multiple", "Price Target", "Return"]
        widths = [25, 25, 25, 25, 30, 28, 22]
        pdf.table_header(cols, widths)
        scenario_data = [
            ("BEAR", scenarios["bear"]),
            ("BASE", scenarios["base"]),
            ("BULL", scenarios["bull"]),
        ]
        for i, (label, s) in enumerate(scenario_data):
            row = [
                label,
                s["prob"],
                s["growth"],
                s["margin"],
                s["multiple"],
                f"{sym}{s['target']:.2f}",
                s["return"],
            ]
            pdf.table_row(row, widths, fill=(i % 2 == 0))
        pdf.ln(2)
        pdf.kv_row("Probability-Weighted Target", fmt_large(d.get("pw_target"), sym))
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # CATALYSTS
    # -----------------------------------------------------------------------
    pdf.section_title("10. KEY CATALYSTS")
    for i, cat in enumerate(d.get("catalysts", []), 1):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(8, 5, f"{i}.")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, cat)
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # RISKS
    # -----------------------------------------------------------------------
    pdf.section_title("11. KEY RISKS")
    risk_labels = ["CRITICAL", "HIGH", "HIGH", "MEDIUM", "MEDIUM"]
    for i, risk in enumerate(d.get("risks", []), 1):
        severity = risk_labels[i - 1] if i <= len(risk_labels) else "MEDIUM"
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(8, 5, f"{i}.")
        pdf.cell(25, 5, f"[{severity}]")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, risk)
    pdf.ln(3)

    # -----------------------------------------------------------------------
    # FINAL CONCLUSION
    # -----------------------------------------------------------------------
    pdf.section_title("12. FINAL INVESTMENT CONCLUSION")
    conclusion_rows = [
        ("Final Recommendation", rec),
        ("Conviction Level", f"{d.get('conviction')} / 10"),
        ("Investment Horizon", "12–36 Months"),
        ("12-Month Price Target", fmt_large(d.get("target_mean"), sym)),
        ("Probability-Weighted Target", fmt_large(d.get("pw_target"), sym)),
        ("Composite Quality Score", f"{d.get('composite_score')} / 10"),
        ("Valuation Verdict", d.get("valuation_verdict", "N/A")),
        ("FCF Yield", fmt_pct(d.get("fcf_yield"))),
        ("Free Cash Flow (Latest)", fmt_large(d.get("latest_fcf"), sym)),
        ("FCF Margin", fmt_pct(d.get("fcf_margin"))),
    ]
    for label, value in conclusion_rows:
        bold = label in ("Final Recommendation", "Conviction Level")
        pdf.kv_row(label, value, bold_value=bold)
    pdf.ln(4)

    # Investment committee summary paragraph
    pdf.sub_title("Investment Committee Summary")
    summary = (
        f"{name} ({ticker}) presents a {rec.lower()} opportunity in the {d['sector']} sector "
        f"with a composite quality score of {d.get('composite_score')}/10. "
        f"The company generates {fmt_pct(d.get('fcf_margin'))} free cash flow margins on "
        f"{fmt_large(d.get('latest_rev'), sym)} in annual revenue, underpinned by a "
        f"{d.get('moat_label').lower()} economic moat and a "
        f"{'net cash' if (d.get('net_cash') or 0) > 0 else 'levered'} balance sheet "
        f"({'net cash of ' + fmt_large(d.get('net_cash'), sym) if (d.get('net_cash') or 0) > 0 else 'D/E of ' + fmt(d.get('debt_to_equity'), suffix='x')}). "
        f"At a current price of {fmt_large(d.get('price'), sym)}, consensus analyst targets imply "
        f"{fmt_pct((d.get('upside') or 0) / 100)} upside to {fmt_large(d.get('target_mean'), sym)}. "
        f"We recommend this security as a {rec} with conviction {d.get('conviction')}/10 "
        f"for institutional portfolios with a 12–36 month investment horizon."
    )
    pdf.body_text(summary, size=9)

    # -----------------------------------------------------------------------
    # DISCLOSURES
    # -----------------------------------------------------------------------
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4,
        "DISCLOSURES: This report is prepared for institutional use only. Data sourced from Yahoo Finance via yfinance. "
        "All financial metrics are derived from publicly available filings. This document does not constitute an offer "
        "or solicitation to buy or sell any security. Analyst estimates and price targets are forward-looking and subject "
        "to change. Past performance is not indicative of future results. Goldman Sachs branding used for illustrative "
        "purposes only — this is a research tool, not an official Goldman Sachs publication.")
    pdf.set_text_color(0, 0, 0)

    pdf.output(output_path)
    return output_path
