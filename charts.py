"""
charts.py
All Plotly chart builders for the equity dashboard.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

# ── DARK GOLD/BLACK PALETTE ──────────────────────────────────────────────────
GOLD       = "#c8a951"
GOLD_LIGHT = "#e8d48a"
GOLD_DIM   = "#9a7a3a"
BLACK      = "#111111"
CARD_BG    = "#1c1c1c"
GRID       = "#2a2a2a"
GREEN      = "#3dba70"
RED        = "#e05555"
BLUE_DIM   = "#3a6090"   # kept for secondary bars
GRAY       = "#555555"

_LAYOUT = dict(
    paper_bgcolor=CARD_BG,
    plot_bgcolor=BLACK,
    font=dict(family="Arial", size=12, color=GOLD_LIGHT),
    title_font=dict(color=GOLD, size=14, family="Arial"),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=GOLD_LIGHT),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    ),
    xaxis=dict(
        gridcolor=GRID, linecolor=GRID,
        tickfont=dict(color=GOLD_LIGHT), title_font=dict(color=GOLD),
    ),
    yaxis=dict(
        gridcolor=GRID, linecolor=GRID,
        tickfont=dict(color=GOLD_LIGHT), title_font=dict(color=GOLD),
    ),
    margin=dict(l=50, r=30, t=60, b=40),
)


def _base_layout(**overrides):
    """Return a merged layout dict."""
    out = dict(_LAYOUT)
    out.update(overrides)
    return out


def _years_labels(hist_dict):
    return [str(y) for y in sorted(hist_dict.keys())]


def _values(hist_dict):
    return [hist_dict[y] for y in sorted(hist_dict.keys())]


# ── REVENUE CHART ─────────────────────────────────────────────────────────────
def revenue_chart(d):
    years  = _years_labels(d["revenue_hist"])
    values = [v / 1e9 if v else 0 for v in _values(d["revenue_hist"])]
    sym    = d["currency_sym"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=years, y=values,
        marker=dict(color=GOLD, opacity=0.85,
                    line=dict(color=GOLD_LIGHT, width=0.5)),
        name="Revenue",
        text=[f"{sym}{v:.1f}B" for v in values],
        textposition="outside",
        textfont=dict(color=GOLD_LIGHT),
    ))

    growth_years, growth_vals = [], []
    for y in sorted(d["revenue_growth"].keys()):
        g = d["revenue_growth"][y]
        if g is not None:
            growth_years.append(str(y))
            growth_vals.append(g * 100)

    fig.add_trace(go.Scatter(
        x=growth_years, y=growth_vals,
        mode="lines+markers", name="YoY Growth %",
        yaxis="y2",
        line=dict(color=GREEN, width=2),
        marker=dict(size=7, color=GREEN),
    ))

    layout = _base_layout(
        title=f"{d['name']} — Revenue Trend ({d['currency']})",
        yaxis=dict(title=f"Revenue ({sym}B)", showgrid=True,
                   gridcolor=GRID, tickfont=dict(color=GOLD_LIGHT),
                   title_font=dict(color=GOLD)),
        yaxis2=dict(title="YoY Growth %", overlaying="y", side="right",
                    tickformat=".1f", showgrid=False,
                    tickfont=dict(color=GREEN), title_font=dict(color=GREEN)),
        height=380,
    )
    fig.update_layout(**layout)
    return fig


# ── MARGIN CHART ──────────────────────────────────────────────────────────────
def margin_chart(d):
    years = _years_labels(d["gross_margins"])

    def safe_pct(hist, year):
        v = hist.get(int(year))
        return v * 100 if v is not None else None

    gm = [safe_pct(d["gross_margins"], y) for y in years]
    om = [safe_pct(d["operating_margins"], y) for y in years]
    nm = [safe_pct(d["net_margins"], y) for y in years]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=gm, mode="lines+markers",
                             name="Gross Margin",
                             line=dict(color=GOLD, width=2.5),
                             marker=dict(size=8, color=GOLD)))
    fig.add_trace(go.Scatter(x=years, y=om, mode="lines+markers",
                             name="Operating Margin",
                             line=dict(color=GOLD_LIGHT, width=2.5),
                             marker=dict(size=8, color=GOLD_LIGHT)))
    fig.add_trace(go.Scatter(x=years, y=nm, mode="lines+markers",
                             name="Net Margin",
                             line=dict(color=GREEN, width=2.5),
                             marker=dict(size=8, color=GREEN)))

    layout = _base_layout(
        title=f"{d['name']} — Margin Trends",
        yaxis=dict(title="Margin (%)", tickformat=".1f", showgrid=True,
                   gridcolor=GRID, tickfont=dict(color=GOLD_LIGHT),
                   title_font=dict(color=GOLD)),
        height=380,
    )
    fig.update_layout(**layout)
    return fig


# ── FCF CHART ─────────────────────────────────────────────────────────────────
def fcf_chart(d):
    sym    = d["currency_sym"]
    years  = _years_labels(d["fcf_hist"])
    fcf_v  = [v / 1e9 if v else 0 for v in _values(d["fcf_hist"])]
    ocf_v  = [(d["ocf_hist"].get(int(y), 0) or 0) / 1e9 for y in years]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=ocf_v, name="Operating CF",
                         marker=dict(color=GOLD_DIM, opacity=0.75,
                                     line=dict(color=GOLD, width=0.5))))
    fig.add_trace(go.Bar(x=years, y=fcf_v, name="Free Cash Flow",
                         marker=dict(color=GOLD, opacity=0.9,
                                     line=dict(color=GOLD_LIGHT, width=0.5))))

    layout = _base_layout(
        title=f"{d['name']} — Cash Flow ({sym}B)",
        barmode="group",
        yaxis=dict(title=f"{sym}B", showgrid=True,
                   gridcolor=GRID, tickfont=dict(color=GOLD_LIGHT),
                   title_font=dict(color=GOLD)),
        height=380,
    )
    fig.update_layout(**layout)
    return fig


# ── PRICE CHART ───────────────────────────────────────────────────────────────
def price_chart(d):
    hist = d["hist_1y"]
    if hist.empty:
        fig = go.Figure()
        fig.add_annotation(text="No price data available", showarrow=False,
                           font=dict(size=16, color=GOLD))
        fig.update_layout(**_base_layout(height=420))
        return fig

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist["Open"], high=hist["High"],
        low=hist["Low"],   close=hist["Close"],
        name="Price",
        increasing=dict(line=dict(color=GREEN), fillcolor=GREEN),
        decreasing=dict(line=dict(color=RED),   fillcolor=RED),
    ))

    if len(hist) >= 50:
        hist["MA50"] = hist["Close"].rolling(50).mean()
        fig.add_trace(go.Scatter(x=hist.index, y=hist["MA50"],
                                 mode="lines", name="50-Day MA",
                                 line=dict(color=GOLD, width=1.5)))
    if len(hist) >= 200:
        hist["MA200"] = hist["Close"].rolling(200).mean()
        fig.add_trace(go.Scatter(x=hist.index, y=hist["MA200"],
                                 mode="lines", name="200-Day MA",
                                 line=dict(color=GOLD_DIM, width=1.5, dash="dot")))

    layout = _base_layout(
        title=f"{d['name']} — 1-Year Price Chart",
        yaxis=dict(title=f"Price ({d['currency']})", showgrid=True,
                   gridcolor=GRID, tickfont=dict(color=GOLD_LIGHT),
                   title_font=dict(color=GOLD)),
        xaxis_rangeslider_visible=False,
        height=420,
    )
    fig.update_layout(**layout)
    return fig


# ── SCENARIO CHART ────────────────────────────────────────────────────────────
def scenario_chart(d):
    scenarios = d.get("scenarios")
    price     = d.get("price")
    if not scenarios or not price:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient data for scenario analysis",
                           showarrow=False, font=dict(size=16, color=GOLD))
        fig.update_layout(**_base_layout(height=380))
        return fig

    labels = ["Current", "Bear Case", "Base Case", "Bull Case"]
    values = [price,
              scenarios["bear"]["target"],
              scenarios["base"]["target"],
              scenarios["bull"]["target"]]
    colors = [GRAY, RED, GOLD, GREEN]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(color=colors, opacity=0.9,
                    line=dict(color=GOLD_LIGHT, width=0.5)),
        text=[f"{d['currency_sym']}{v:.2f}" for v in values],
        textposition="outside",
        textfont=dict(color=GOLD_LIGHT),
        width=0.5,
    ))
    fig.add_hline(y=price, line_dash="dash", line_color=GRAY,
                  annotation_text=f"Current: {d['currency_sym']}{price:.2f}",
                  annotation_font_color=GOLD_LIGHT,
                  annotation_position="right")

    layout = _base_layout(
        title=f"{d['name']} — Scenario Analysis (12-Month Targets)",
        yaxis=dict(title=f"Price ({d['currency_sym']})", showgrid=True,
                   gridcolor=GRID, tickfont=dict(color=GOLD_LIGHT),
                   title_font=dict(color=GOLD)),
        height=380,
    )
    fig.update_layout(**layout)
    return fig


# ── RADAR CHART ───────────────────────────────────────────────────────────────
def score_radar_chart(d):
    categories = ["Business Quality", "Balance Sheet",
                  "Cash Flow", "Moat", "Management"]
    values     = [d["business_quality_score"], d["balance_sheet_score"],
                  d["cashflow_quality_score"], d["moat_score"], d["mgmt_score"]]
    cats_c = categories + [categories[0]]
    vals_c = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_c, theta=cats_c,
        fill="toself",
        fillcolor=f"rgba(200,169,81,0.18)",
        line=dict(color=GOLD, width=2.5),
        marker=dict(color=GOLD, size=8),
        name=d["ticker"],
    ))

    fig.update_layout(
        polar=dict(
            bgcolor=CARD_BG,
            radialaxis=dict(
                visible=True, range=[0, 10],
                tickfont=dict(size=9, color=GOLD_DIM),
                gridcolor=GRID, linecolor=GRID,
            ),
            angularaxis=dict(
                tickfont=dict(color=GOLD_LIGHT, size=11),
                gridcolor=GRID, linecolor=GRID,
            ),
        ),
        title=dict(text=f"{d['name']} — Quality Scores Radar",
                   font=dict(color=GOLD, size=14)),
        showlegend=False,
        paper_bgcolor=CARD_BG,
        font=dict(family="Arial", size=12, color=GOLD_LIGHT),
        height=380,
    )
    return fig


# ── VALUATION BAR CHART ───────────────────────────────────────────────────────
def valuation_bar_chart(d):
    metrics = ["P/E", "Forward P/E", "EV/EBITDA", "P/S", "P/B"]
    vals    = [d.get("trailing_pe"), d.get("forward_pe"), d.get("ev_to_ebitda"),
               d.get("price_to_sales"), d.get("price_to_book")]

    filtered = [(m, v) for m, v in zip(metrics, vals) if v is not None]
    if not filtered:
        fig = go.Figure()
        fig.add_annotation(text="Valuation data unavailable", showarrow=False,
                           font=dict(color=GOLD))
        fig.update_layout(**_base_layout(height=380))
        return fig

    labels, values = zip(*filtered)
    bar_colors = [GOLD if i % 2 == 0 else GOLD_DIM for i in range(len(labels))]

    fig = go.Figure(go.Bar(
        x=list(labels), y=list(values),
        marker=dict(color=bar_colors, opacity=0.9,
                    line=dict(color=GOLD_LIGHT, width=0.5)),
        text=[f"{v:.1f}x" for v in values],
        textposition="outside",
        textfont=dict(color=GOLD_LIGHT),
        width=0.5,
    ))

    layout = _base_layout(
        title=f"{d['name']} — Current Valuation Multiples",
        yaxis=dict(title="Multiple (x)", showgrid=True,
                   gridcolor=GRID, tickfont=dict(color=GOLD_LIGHT),
                   title_font=dict(color=GOLD)),
        height=380,
    )
    fig.update_layout(**layout)
    return fig

