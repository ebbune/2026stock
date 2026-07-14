import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="한국 AI·반도체 주식 분석기", layout="wide")
st.title("🇰🇷 한국 대표 AI & 반도체 주식 분석기")

# 한국 대표 AI, 반도체, HBM(고대역폭 메모리) 관련주 딕셔너리
KOREA_TECH_STOCKS = {
    "삼성전자 (005930.KS)": "005930.KS",
    "SK하이닉스 (000660.KS)": "000660.KS",
    "한미반도체 (042700.KS)": "042700.KS",
    "리노공업 (058470.KQ)": "058470.KQ",
    "HPSP (403870.KQ)": "403870.KQ",
    "이수페타시스 (007660.KS)": "007660.KS"
}

# 사이드바 설정
st.sidebar.header("주식 및 기간 선택")
selected_stock_name = st.sidebar.selectbox("분석할 종목을 선택하세요", list(KOREA_TECH_STOCKS.keys()))
ticker = KOREA_TECH_STOCKS[selected_stock_name]

start_date = st.sidebar.date_input("조회 시작일", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("조회 종료일", datetime.today())

# 데이터 캐싱 및 로드
@st.cache_data
def load_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    return df

try:
    data = load_data(ticker, start_date, end_date)
    
    if not data.empty:
        # 주요 지표 카드 생성
        latest_close = float(data['Close'].iloc[-1].iloc[0] if hasattr(data['Close'].iloc[-1], 'iloc') else data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2].iloc[0] if hasattr(data['Close'].iloc[-2], 'iloc') else data['Close'].iloc[-2])
        change = latest_close - prev_close
        pct_change = (change / prev_close) * 100

        col1, col2, col3 = st.columns(3)
        col1.metric("현재가 (종가)", f"{latest_close:,.0f} 원")
        col2.metric("전일 대비 변동", f"{change:+,.0f} 원", f"{pct_change:+.2f}%")
        col3.metric("최근 거래량", f"{int(data['Volume'].iloc[-1]):,} 주")

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
        
        # 이동평균선(20일 및 60일) 계산 및 추가
        data['SMA20'] = data['Close'].rolling(window=20).mean()
        data['SMA60'] = data['Close'].rolling(window=60).mean()
        
        fig.add_trace(go.Scatter(
            x=data.index, 
            y=data['SMA20'].values.flatten(), 
            line=dict(color='orange', width=1.5), 
            name='20일 이평선'
        ))
        fig.add_trace(go.Scatter(
            x=data.index, 
            y=data['SMA60'].values.flatten(), 
            line=dict(color='cyan', width=1.5), 
            name='60일 이평선'
        ))

        fig.update_layout(
            title=f"{selected_stock_name} 상세 주가 트렌드",
            yaxis_title="가격 (KRW)",
            xaxis_title="날짜",
            xaxis_rangeslider_visible=True,
            template="plotly_dark",
            height=650
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # 원본 데이터 테이블 표시
        with st.expander("데이터프레임 원본 보기 (최근 100영업일)"):
            st.dataframe(data.tail(100), use_container_width=True)
            
    else:
        st.error("해당 종목의 데이터를 찾을 수 없습니다.")
except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
