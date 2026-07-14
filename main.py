import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="주식 데이터 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 주식 데이터 분석 대시보드")
st.caption("Yahoo Finance 데이터를 활용한 인터랙티브 주가 분석 도구")

# ─────────────────────────────────────────────
# 사이드바 - 사용자 입력
# ─────────────────────────────────────────────
st.sidebar.header("⚙️ 설정")

ticker_input = st.sidebar.text_input(
    "종목 티커 입력 (쉼표로 여러 개 구분 가능)",
    value="AAPL",
    help="예: AAPL, TSLA, 005930.KS (삼성전자), 035420.KS (네이버)",
)
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

period_options = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
    "전체": "max",
}
period_label = st.sidebar.selectbox("조회 기간", list(period_options.keys()), index=3)
period = period_options[period_label]

interval_options = {
    "1일": "1d",
    "1주": "1wk",
    "1달": "1mo",
}
interval_label = st.sidebar.selectbox("데이터 간격", list(interval_options.keys()), index=0)
interval = interval_options[interval_label]

st.sidebar.markdown("---")
st.sidebar.subheader("📊 이동평균선")
show_ma = st.sidebar.checkbox("이동평균선 표시", value=True)
ma_short = st.sidebar.number_input("단기 이동평균 (일)", min_value=2, max_value=100, value=20)
ma_long = st.sidebar.number_input("장기 이동평균 (일)", min_value=5, max_value=300, value=60)

st.sidebar.markdown("---")
st.sidebar.subheader("📉 보조 지표")
show_volume = st.sidebar.checkbox("거래량 표시", value=True)
show_rsi = st.sidebar.checkbox("RSI 표시", value=True)
rsi_period = st.sidebar.number_input("RSI 기간", min_value=5, max_value=50, value=14)

chart_type = st.sidebar.radio("차트 유형", ["캔들스틱", "라인"], index=0)

st.sidebar.markdown("---")
run_button = st.sidebar.button("🔍 데이터 불러오기", use_container_width=True, type="primary")


# ─────────────────────────────────────────────
# 데이터 로딩 함수
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    df = df.rename(columns={date_col: "Date"})
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ─────────────────────────────────────────────
# 메인 화면
# ─────────────────────────────────────────────
if not tickers:
    st.info("왼쪽 사이드바에서 티커를 입력해주세요.")
    st.stop()

tab_names = ["📊 개별 분석"] + (["🔀 종목 비교"] if len(tickers) > 1 else [])
tabs = st.tabs(tab_names)

# ---------- 탭 1: 개별 분석 ----------
with tabs[0]:
    selected_ticker = st.selectbox("분석할 종목 선택", tickers, key="single_select")

    with st.spinner(f"{selected_ticker} 데이터를 불러오는 중..."):
        df = load_data(selected_ticker, period, interval)
        info = load_info(selected_ticker)

    if df.empty:
        st.error(f"'{selected_ticker}' 데이터를 찾을 수 없습니다. 티커를 확인해주세요.")
        st.stop()

    # 지표 계산
    if show_ma:
        df[f"MA{ma_short}"] = df["Close"].rolling(window=ma_short).mean()
        df[f"MA{ma_long}"] = df["Close"].rolling(window=ma_long).mean()
    if show_rsi:
        df["RSI"] = calc_rsi(df["Close"], rsi_period)

    # 상단 요약 지표
    company_name = info.get("longName", selected_ticker)
    currency = info.get("currency", "")
    last_close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else last_close
    change = last_close - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0

    st.subheader(f"{company_name} ({selected_ticker})")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("현재가", f"{last_close:,.2f} {currency}", f"{change:+,.2f} ({change_pct:+.2f}%)")
    c2.metric("52주 최고", f"{info.get('fiftyTwoWeekHigh', float(df['High'].max())):,.2f}")
    c3.metric("52주 최저", f"{info.get('fiftyTwoWeekLow', float(df['Low'].min())):,.2f}")
    c4.metric("거래량", f"{int(df['Volume'].iloc[-1]):,}")
    mcap = info.get("marketCap")
    c5.metric("시가총액", f"{mcap/1e8:,.1f}억" if mcap else "N/A")

    # 차트 구성 (행 개수 동적 결정)
    rows = 1 + (1 if show_volume else 0) + (1 if show_rsi else 0)
    row_heights = [0.6] + [0.2] * (rows - 1) if rows > 1 else [1.0]
    specs_titles = ["가격"]
    if show_volume:
        specs_titles.append("거래량")
    if show_rsi:
        specs_titles.append("RSI")

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.04, row_heights=row_heights,
        subplot_titles=specs_titles,
    )

    # 가격 차트
    if chart_type == "캔들스틱":
        fig.add_trace(
            go.Candlestick(
                x=df["Date"], open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"], name=selected_ticker,
                increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
            ),
            row=1, col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="종가",
                       line=dict(color="#4fc3f7", width=2)),
            row=1, col=1,
        )

    if show_ma:
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df[f"MA{ma_short}"], mode="lines",
                       name=f"MA{ma_short}", line=dict(color="#ffb74d", width=1.3)),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df[f"MA{ma_long}"], mode="lines",
                       name=f"MA{ma_long}", line=dict(color="#ba68c8", width=1.3)),
            row=1, col=1,
        )

    current_row = 1

    # 거래량
    if show_volume:
        current_row += 1
        colors = np.where(df["Close"] >= df["Open"], "#26a69a", "#ef5350")
        fig.add_trace(
            go.Bar(x=df["Date"], y=df["Volume"], name="거래량", marker_color=colors, showlegend=False),
            row=current_row, col=1,
        )

    # RSI
    if show_rsi:
        current_row += 1
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["RSI"], mode="lines", name="RSI",
                       line=dict(color="#4fc3f7", width=1.3), showlegend=False),
            row=current_row, col=1,
        )
        fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", opacity=0.6, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", opacity=0.6, row=current_row, col=1)

    fig.update_layout(
        height=750,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=60, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📄 원본 데이터 보기"):
        st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, f"{selected_ticker}_data.csv", "text/csv")

# ---------- 탭 2: 종목 비교 ----------
if len(tickers) > 1:
    with tabs[1]:
        st.subheader("정규화 수익률 비교 (시작 시점 = 100)")

        compare_fig = go.Figure()
        summary_rows = []

        for t in tickers:
            with st.spinner(f"{t} 불러오는 중..."):
                d = load_data(t, period, interval)
            if d.empty:
                st.warning(f"'{t}' 데이터를 찾을 수 없어 제외합니다.")
                continue
            normalized = d["Close"] / d["Close"].iloc[0] * 100
            compare_fig.add_trace(
                go.Scatter(x=d["Date"], y=normalized, mode="lines", name=t)
            )
            total_return = (d["Close"].iloc[-1] / d["Close"].iloc[0] - 1) * 100
            summary_rows.append({
                "티커": t,
                "시작가": round(float(d["Close"].iloc[0]), 2),
                "현재가": round(float(d["Close"].iloc[-1]), 2),
                "기간 수익률(%)": round(float(total_return), 2),
            })

        compare_fig.update_layout(
            height=550,
            template="plotly_dark",
            hovermode="x unified",
            yaxis_title="정규화 지수 (시작=100)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(compare_fig, use_container_width=True)

        if summary_rows:
            summary_df = pd.DataFrame(summary_rows).sort_values("기간 수익률(%)", ascending=False)
            st.dataframe(
                summary_df.style.background_gradient(subset=["기간 수익률(%)"], cmap="RdYlGn"),
                use_container_width=True,
            )

st.markdown("---")
st.caption("데이터 출처: Yahoo Finance (yfinance) · 투자 판단의 참고용이며 투자 권유가 아닙니다.")
