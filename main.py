import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="인터랙티브 주식 분석기", layout="wide")
st.title("📈 인터랙티브 주식 데이터 분석기")

# 사이드바 입력 및 설정
st.sidebar.header("설정")
ticker = st.sidebar.text_input("주식 티커 입력 (예: AAPL, TSLA, 005930.KS)", "AAPL")
start_date = st.sidebar.date_input("시작일", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("종료일", datetime.today())

# 데이터 불러오기
@st.cache_data
def load_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    return df

try:
    data = load_data(ticker, start_date, end_date)
    
    if not data.empty:
        # 주요 지표 카드 표시
        latest_close = float(data['Close'].iloc[-1].iloc[0] if hasattr(data['Close'].iloc[-1], 'iloc') else data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2].iloc[0] if hasattr(data['Close'].iloc[-2], 'iloc') else data['Close'].iloc[-2])
        change = latest_close - prev_close
        pct_change = (change / prev_close) * 100

        col1, col2, col3 = st.columns(3)
        col1.metric("최종 종가", f"${latest_close:,.2f}")
        col2.metric("전일 대비 변동", f"${change:,.2f}", f"{pct_change:+.2f}%")
        col3.metric("거래량", f"{int(data['Volume'].iloc[-1]):,}")

        # 인터랙티브 캔들스틱 차트 생성
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'].values.flatten(),
            high=data['High'].values.flatten(),
            low=data['Low'].values.flatten(),
            close=data['Close'].values.flatten(),
            name="주가"
        ))
        
        # 이동평균선(SMA) 추가
        data['SMA20'] = data['Close'].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=data.index, 
            y=data['SMA20'].values.flatten(), 
            line=dict(color='orange', width=1.5), 
            name='20일 이평선'
        ))

        fig.update_layout(
            title=f"{ticker} 주가 분석 (캔들스틱 & 20일 이평선)",
            yaxis_title="가격 (USD)",
            xaxis_title="날짜",
            xaxis_rangeslider_visible=True,
            template="plotly_dark",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # 데이터 테이블 출력
        with st.expander("원본 데이터 보기"):
            st.dataframe(data.tail(100), use_container_width=True)
            
    else:
        st.error("데이터를 불러오지 못했습니다. 티커명을 확인해 주세요.")
except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
