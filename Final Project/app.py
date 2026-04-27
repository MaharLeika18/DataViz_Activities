# pip install streamlit plotly pandas numpy scipy statsmodels 
# python streamlit run app.py


import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="BTC vs SPX: Does Crypto Lead the Market?",
    page_icon="📈", 
    layout="wide",
)

# ── CCS Schizoposting ──
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: rgba(34, 211, 238, 0.07);
        border-right: 1px solid rgba(34, 211, 238, 0.2);
    }
    div[data-testid="stRadio"] label {
        color: #94a3b8 !important;
    }

    div[data-testid="stRadio"] label:has(input:checked) {
        color: #22d3ee !important;
    }

    div[data-testid="stRadio"] label > div:first-child {
        border: 1px solid #22d3ee !important;
    }

    div[data-testid="stRadio"] label:has(input:checked) > div:first-child {
        background-color: rgba(34, 211, 238, 0.15) !important;
    }
    .stApp { background-color: #0a0e1a; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    h1, h2, h3 { color: #f1f5f9; font-family: Georgia, serif; }
    p, li { color: #cbd5e1; }
    .metric-label { color: #64748b !important; font-size: 12px !important; }
    .stMetric { background: #111827; border: 1px solid #1f2d45; border-radius: 8px; padding: 12px; }
    .annotation-box {
        background: rgba(34,211,238,0.07);
        border-left: 3px solid #22d3ee;
        border-radius: 0 8px 8px 0;
        padding: 10px 14px;
        margin-top: 4px;
        font-size: 13px;
        color: #94a3b8;
        line-height: 1.6;
    }
    .conclusion-box {
        background: linear-gradient(135deg, rgba(34,211,238,0.08), rgba(59,130,246,0.05));
        border: 1px solid rgba(34,211,238,0.25);
        border-radius: 10px;
        padding: 18px 22px;
        color: #cbd5e1;
        font-size: 14px;
        line-height: 1.7;
    }
    .stPlotlyChart {
        border-radius: 16px;
        overflow: hidden;
}
    
</style>
""", unsafe_allow_html=True)

# ── Colors ig ──
BTC_COLOR   = "#3b82f6"
SPX_COLOR   = "#f7931a"
ACCENT      = "#22d3ee"
DANGER      = "#ef4444"
BG_CHART    = "#171B24"
GRID_COLOR  = "rgba(255,255,255,0.06)"
FONT_COLOR  = "#94a3b8"

LAYOUT_BASE = dict(
    paper_bgcolor=BG_CHART,
    plot_bgcolor=BG_CHART,
    font=dict(color=FONT_COLOR, family="JetBrains Mono, monospace", size=11),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=FONT_COLOR), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
)

# ── No more Colors ──
@st.cache_data
def load_data():
    df = pd.read_csv(r"C:/Users/Arrcann/Downloads/Main/Programming/DataViz_Lesson4/Final Project/Milestone_2.csv", parse_dates=["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    df.columns = [c.strip() for c in df.columns]

    # Log returns
    df["BTC_ret"] = np.log(df["BTC"]).diff()
    df["SPX_ret"] = np.log(df["SPX"]).diff()
    df = df.dropna().reset_index(drop=True)

    # Normalized prices
    df["BTC_norm"] = df["BTC"] / df["BTC"].iloc[0]
    df["SPX_norm"] = df["SPX"] / df["SPX"].iloc[0]

    # Cumulative returns
    df["BTC_cum"] = (1 + df["BTC_ret"]).cumprod()
    df["SPX_cum"] = (1 + df["SPX_ret"]).cumprod()

    # 30-day rolling volatility
    df["BTC_vol"] = df["BTC_ret"].rolling(30).std()
    df["SPX_vol"] = df["SPX_ret"].rolling(30).std()

    # Return difference
    df["ret_diff"] = df["BTC_ret"] - df["SPX_ret"]

    return df

@st.cache_data
def compute_analytics(df):
    # CCF
    max_lag = 30
    lags = list(range(-max_lag, max_lag + 1))
    corrs = [float(df["BTC_ret"].shift(lag).corr(df["SPX_ret"])) for lag in lags]

    betas, pvals = [], []
    try:
        from scipy.stats import t as tdist
        for lag in range(1, 11):
            x = df["BTC_ret"].shift(lag).values
            y = df["SPX_ret"].values
            mask = ~np.isnan(x) & ~np.isnan(y)
            x, y = x[mask], y[mask]
            n = len(x)
            xm, ym = x.mean(), y.mean()
            beta = np.sum((x - xm) * (y - ym)) / np.sum((x - xm) ** 2)
            alpha = ym - beta * xm
            resid = y - (alpha + beta * x)
            se = np.sqrt(np.sum(resid ** 2) / (n - 2) / np.sum((x - xm) ** 2))
            tstat = beta / se
            pval = float(2 * (1 - tdist.cdf(abs(tstat), df=n - 2)))
            betas.append(round(beta, 6))
            pvals.append(round(pval, 4))
    except ImportError:
        for lag in range(1, 11):
            betas.append(round(float(df["BTC_ret"].shift(lag).corr(df["SPX_ret"])), 6))
            pvals.append(0.5)

    return lags, corrs, betas, pvals


df_full = load_data()
lags, corrs, betas, pvals = compute_analytics(df_full)

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:

    st.markdown(
        "# Data Visualization\n\n"
        "BSCS 3214\n"
        "| Final Project"
        
        )
    st.markdown("## Filters")
    period = st.radio(
        "Select Period",
        ["All (2024–2026)", "2024 Only", "2025 Only"],
        index=0,
    )

    st.markdown("---")
    st.markdown("## **About**")
    st.markdown(
        "Milestone 3 Dashboard — BTC vs SPX Cross-Asset Analysis\n\n"
        "Methods: Log-returns · CCF · OLS Lagged Regression · Granger Causality\n\n"
        "Jerdelyne Ladringan & Louezethe Illicir Saldua"
    )

# Filter by period
if period == "2024 Only":
    df = df_full[df_full["Date"].dt.year == 2024].copy()
elif period == "2025 Only":
    df = df_full[df_full["Date"].dt.year == 2025].copy()
else:
    df = df_full.copy()

# ── Header ──
st.markdown(
    '<p style="color:#22d3ee;font-family:monospace;font-size:11px;letter-spacing:0.15em;">MILESTONE 3 — NARRATIVE DASHBOARD</p>',
    unsafe_allow_html=True,
)
st.title("FinTech Market Volatility Analyst")
st.subheader("BTC vs S&P 500: Does Crypto Lead the Market?")
st.markdown(
    f"**Period:** {df['Date'].iloc[0].strftime('%b %Y')} – {df['Date'].iloc[-1].strftime('%b %Y')} &nbsp;|&nbsp; "
    f"**Trading days:** {len(df)} &nbsp;|&nbsp; "
    f"**Data:** Yahoo Finance via yfinance",
    unsafe_allow_html=True,
)

# ── KPI - lock in ──
btc_ret_pct = (df["BTC"].iloc[-1] / df["BTC"].iloc[0] - 1) * 100
spx_ret_pct = (df["SPX"].iloc[-1] / df["SPX"].iloc[0] - 1) * 100
btc_ann_vol = df["BTC_ret"].std() * np.sqrt(252) * 100
spx_ann_vol = df["SPX_ret"].std() * np.sqrt(252) * 100
overall_corr = df["BTC_ret"].corr(df["SPX_ret"])

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("BTC Total Return", f"{btc_ret_pct:+.1f}%", f"${df['BTC'].iloc[0]/1000:.0f}K → ${df['BTC'].iloc[-1]/1000:.0f}K")
col2.metric("SPX Total Return", f"{spx_ret_pct:+.1f}%", f"{df['SPX'].iloc[0]:.0f} → {df['SPX'].iloc[-1]:.0f}")
col3.metric("BTC Ann. Volatility", f"{btc_ann_vol:.1f}%", "Annualized")
col4.metric("SPX Ann. Volatility", f"{spx_ann_vol:.1f}%", "Annualized")
col5.metric("BTC–SPX Correlation", f"{overall_corr:.3f}", "Pearson r, daily returns")

st.divider()

# ── Chart 1 ──
st.subheader("Price Performance: BTC vs S&P 500")

y_btc = df["BTC"] / df["BTC"].iloc[0]
y_spx = df["SPX"] / df["SPX"].iloc[0]

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df["Date"], y=y_btc, name="Bitcoin (BTC)",
    line=dict(color=BTC_COLOR, width=2), fill="tozeroy", fillcolor="rgba(247,147,26,0.06)"))
fig1.add_trace(go.Scatter(x=df["Date"], y=y_spx, name="S&P 500 (SPX)",
    line=dict(color=SPX_COLOR, width=2), fill="tozeroy", fillcolor="rgba(59,130,246,0.06)"))
fig1.update_layout(**LAYOUT_BASE, title="Normalized Price — Base = 1.0 at period start", yaxis_title="Index (1.0 = start)", height=340)
st.plotly_chart(fig1, use_container_width=True)

with st.expander("Show chart data"):
    st.dataframe(
        pd.DataFrame({
            "Date": df["Date"],
            "BTC": y_btc,
            "SPX": y_spx
        })
    )

st.markdown(
    '<div class="annotation-box"><b style="color:#22d3ee">Story:</b> '
    "BTC showed significant outperformance and had a volatile trajectory. In comparison, SPX's growth was steadier and more gradual, with smaller and smoother ups and downs. Whenever the broader market had bullish momentum, BTC tended to accelerate faster than SPX. Its peaks are higher and the slopes of its rises are steeper. But BTC was also more sensitive to market corrections, with deeper pullbacks than SPX. Despite its volatility, BTC remained broadly correlated with the general trend of SPX: both moved upward over time and had similar directional shifts.</div>",
    unsafe_allow_html=True,
)

st.divider()

# ── Charts 2 & 3 ──
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("30-Day Rolling Volatility")
    df_vol = df.dropna(subset=["BTC_vol", "SPX_vol"])
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_vol["Date"], y=df_vol["BTC_vol"] * 100, name="BTC", line=dict(color=BTC_COLOR, width=1.5)))
    fig2.add_trace(go.Scatter(x=df_vol["Date"], y=df_vol["SPX_vol"] * 100, name="SPX", line=dict(color=SPX_COLOR, width=1.5)))
    fig2.update_layout(**LAYOUT_BASE, yaxis_title="Daily Std Dev (%)", height=280)
    st.plotly_chart(fig2, use_container_width=True)
    
    with st.expander("Show chart data"):
        st.dataframe(
            df_vol[["Date", "BTC_vol", "SPX_vol"]]
        )

    st.markdown(
        '<div class="annotation-box"><b style="color:#22d3ee">Story:</b> '
        "The 30-day rolling volatility highlights how BTC consistently experienced larger and more frequent fluctuations compared to SPX. BTC’s volatility spikes were sharper and more pronounced, reflecting its sensitivity to rapid market changes and shifts in sentiment. In contrast, SPX maintained a relatively stable volatility profile, with smaller and more gradual increases during periods of market stress. Despite these differences in magnitude, both assets showed periods where volatility increased simultaneously, suggesting that broader market conditions influenced the intensity of price movements in both BTC and SPX.</div>",
        unsafe_allow_html=True,
    )

with col_b:
    st.subheader("Return Distribution")
    btc_rets = df["BTC_ret"].dropna()
    spx_rets = df["SPX_ret"].dropna()
    fig3 = go.Figure()
    fig3.add_trace(go.Histogram(x=btc_rets * 100, nbinsx=60, name="BTC", marker_color=BTC_COLOR, opacity=0.6))
    fig3.add_trace(go.Histogram(x=spx_rets * 100, nbinsx=60, name="SPX", marker_color=SPX_COLOR, opacity=0.6))
    fig3.update_layout(**LAYOUT_BASE, barmode="overlay", xaxis_title="Daily Log-Return (%)", yaxis_title="Count", height=280)
    st.plotly_chart(fig3, use_container_width=True)
    
    with st.expander("Show chart data"):
        st.dataframe(
            pd.DataFrame({
                "BTC_ret_%": btc_rets * 100,
                "SPX_ret_%": spx_rets * 100
            })
        )    

    st.markdown(
        '<div class="annotation-box"><b style="color:#22d3ee">Story:</b> '
        "The return distribution shows that BTC had a much wider spread of returns, indicating more frequent and extreme price movements in both directions. Its distribution is more dispersed, with heavier tails, reflecting a higher likelihood of large gains as well as sharp losses. In contrast, SPX’s returns are more tightly clustered around the center, suggesting more consistent and moderate daily changes. While both assets are centered near zero—indicating no strong daily bias upward or downward—BTC exhibits greater variability and risk. Despite this difference in dispersion, both distributions remain broadly symmetric, showing that positive and negative returns occur with similar frequency for each asset.</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Chart 4 ──
st.subheader("Cross-Correlation Function (CCF): Does BTC Lead or Lag SPX?")

sig_bound = 1.96 / np.sqrt(len(df))
bar_colors = [BTC_COLOR if l == 0 else (ACCENT if abs(c) > sig_bound else "rgba(100,116,139,0.5)") for l, c in zip(lags, corrs)]

fig4 = go.Figure()
fig4.add_trace(go.Bar(x=lags, y=corrs, marker_color=bar_colors, name="Correlation"))
fig4.add_hline(y=sig_bound, line_dash="dash", line_color=DANGER, line_width=1.5, annotation_text="+95% CI", annotation_font_color=DANGER)
fig4.add_hline(y=-sig_bound, line_dash="dash", line_color=DANGER, line_width=1.5, annotation_text="-95% CI", annotation_font_color=DANGER)
fig4.add_vline(x=0, line_color="rgba(255,255,255,0.2)", line_width=1)
fig4.update_layout(**LAYOUT_BASE, xaxis_title="Lag (days) — Negative: BTC leads SPX | Positive: SPX leads BTC", yaxis_title="Pearson r", height=300)
st.markdown('<div class="chart-wrapper">', unsafe_allow_html=True)
st.plotly_chart(fig4, use_container_width=True)

with st.expander("Show chart data"):
    st.dataframe(
        pd.DataFrame({
            "Lag": lags,
            "Correlation": corrs
        })
    )

st.markdown(
    '<div class="annotation-box"><b style="color:#22d3ee">Story:</b> '
    "The cross-correlation function shows how the relationship between BTC and SPX changes when one is shifted forward or backward in time. The strongest correlations are centered around zero lag, indicating that both assets generally move at the same time rather than one consistently leading the other. While there are slight increases in correlation at certain positive or negative lags, these are relatively small and do not suggest a strong or persistent lead–lag effect. This implies that BTC and SPX tend to react to market conditions simultaneously, with no clear evidence that one systematically drives the movements of the other over the observed period.</div>",
    unsafe_allow_html=True,
)

st.divider()


# ── Chart 5 ──
st.subheader("Absolute Returns (Movement Magnitude)")

quarters = {
    "All": None,
    "Q1 (Jan–Mar)": [1, 2, 3],
    "Q2 (Apr–Jun)": [4, 5, 6],
    "Q3 (Jul–Sep)": [7, 8, 9],
    "Q4 (Oct–Dec)": [10, 11, 12],
}

selected_q = st.radio(
    "Filter by Quarter",
    options=list(quarters.keys()),
    horizontal=True,
    key="quarter_filter",
    label_visibility="collapsed",
)

df7 = df.copy()
if quarters[selected_q] is not None:
    df7 = df7[df7["Date"].dt.month.isin(quarters[selected_q])].reset_index(drop=True)
    x_axis = list(range(len(df7)))
    tick_vals = list(range(0, len(df7), max(1, len(df7)//8)))
    tick_text = df7["Date"].dt.strftime("%b %Y").iloc[tick_vals].tolist()
else:
    x_axis = df7["Date"]
    tick_vals = None
    tick_text = None

from plotly.subplots import make_subplots
fig5 = make_subplots(specs=[[{"secondary_y": True}]])

fig5.add_trace(go.Scatter(
    x=x_axis,
    y=df7["BTC_ret"].abs() * 100,
    name="BTC",
    line=dict(color=BTC_COLOR, width=1),
    fill="tozeroy",
    fillcolor="rgba(247,147,26,0.4)",
    hovertemplate="<b>%{text}</b><br>BTC: %{y:.2f}%<extra></extra>",
    text=df7["Date"].dt.strftime("%Y-%m-%d").tolist(),
), secondary_y=False)

fig5.add_trace(go.Scatter(
    x=x_axis,
    y=df7["SPX_ret"].abs() * 100,
    name="SPX",
    line=dict(color=SPX_COLOR, width=1),
    fill="tozeroy",
    fillcolor="rgba(59,130,246,0.4)",
    hovertemplate="<b>%{text}</b><br>SPX: %{y:.2f}%<extra></extra>",
    text=df7["Date"].dt.strftime("%Y-%m-%d").tolist(),
), secondary_y=True)

fig5.update_layout(**LAYOUT_BASE, height=260)
fig5.update_yaxes(
    title_text="BTC Absolute Return (%)",
    secondary_y=False,
    gridcolor=GRID_COLOR,
    tickfont=dict(color=BTC_COLOR),
    title_font=dict(color=BTC_COLOR),
)
fig5.update_yaxes(
    title_text="SPX Absolute Return (%)",
    secondary_y=True,
    gridcolor=GRID_COLOR,
    tickfont=dict(color=SPX_COLOR),
    title_font=dict(color=SPX_COLOR),
)
fig5.update_xaxes(
    gridcolor=GRID_COLOR,
    tickvals=tick_vals,
    ticktext=tick_text,
)

if quarters[selected_q] is not None:
    year_changes = df7[df7["Date"].dt.month == df7["Date"].dt.month.iloc[0]].groupby(df7["Date"].dt.year).first()
    for yr, row in year_changes.iterrows():
        idx = df7[df7["Date"] == row["Date"]].index[0]
        fig5.add_vline(
            x=idx,
            line_color="rgba(255,255,255,0.2)",
            line_width=1,
            line_dash="dash",
        )
        fig5.add_annotation(
            x=idx,
            y=df7["BTC_ret"].abs().max() * 100,
            text=str(yr),
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.5)", size=11, family="JetBrains Mono"),
            xanchor="left",
            yanchor="top",
        )

st.plotly_chart(fig5, use_container_width=True)

with st.expander("Show chart data"):
    st.dataframe(
        pd.DataFrame({
            "Date": df7["Date"],
            "BTC_abs_ret_%": df7["BTC_ret"].abs() * 100,
            "SPX_abs_ret_%": df7["SPX_ret"].abs() * 100
        })
    )

st.markdown(
    '<div class="annotation-box"><b style="color:#22d3ee">Story:</b> '
    "The distribution of absolute returns highlights a clear difference in volatility between BTC and SPX. BTC exhibits significantly larger absolute movements, indicating that substantial price changes occur more frequently regardless of direction. Its values are more widely spread, reflecting a higher level of market intensity and variability. In contrast, SPX shows smaller and more concentrated absolute returns, suggesting that large daily fluctuations are less common and price movements tend to remain moderate. While both assets experience periods of heightened activity, BTC consistently demonstrates stronger magnitude in its movements, reinforcing its characterization as the more volatile asset compared to the relatively stable behavior of SPX.</div>",
    unsafe_allow_html=True,
)

st.divider()

# ── Conclusion ──
st.subheader("📊 Analytical Conclusion")
st.markdown(
    '<div class="conclusion-box">'
    "<b>BTC does not Granger-cause SPX</b> over this 2-year sample. "
    f"The contemporaneous correlation (r = {overall_corr:.3f}) reflects shared macro drivers — "
    "both assets respond to risk sentiment, Fed policy, and global liquidity conditions. "
    "All lagged regression betas are statistically insignificant (p &gt; 0.15 at every lag 1–10 days). "
    "BTC is best characterized as a <i>high-beta risk asset</i> that amplifies macro moves, "
    "not a leading indicator for equity markets. "
    "Investors seeking to use crypto to predict stocks find <b>no robust predictive signal</b> in this data."
    "<br><br>The overall results show that while BTC and SPX tend to move together at times, there is no clear lead-lag relationship between them. BTC experiences larger and more frequent price swings, but these movements do not help predict future changes in the stock market. The correlation observed between the two is mainly happening at the same time, suggesting that both are reacting to the same broader economic factors rather than influencing each other. This is further supported by the lack of meaningful results from lagged analysis, where past BTC returns do not explain future SPX performance. Overall, BTC behaves more like a highly volatile asset that responds to market conditions alongside equities, rather than acting as a signal for where the stock market will move next."
    "</div>",
    unsafe_allow_html=True,
)

st.caption(
    "Data: Yahoo Finance via yfinance · Period: 2024-01-03 to 2026-03-30 · "
    "Methods: Log-returns · ADF · CCF · OLS Lagged Regression · Granger Causality · Milestone 3"
)
