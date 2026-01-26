import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import time

# =========================================================
# 1. 페이지 설정
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e6e6e6;
        padding: 15px;
        border-radius: 10px;
    }
    div[data-testid="stMetric"] label { color: #666666 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #000000 !important; }
    button[data-baseweb="tab"] { font-size: 16px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 데이터 처리 & 검색 로직
# =========================================================
@st.cache_data(ttl=86400)
def get_sp500_data():
    try:
        # S&P 500 리스트 (섹터 정보 포함)
        df = fdr.StockListing('S&P500')
        return df
    except:
        return None

@st.cache_data(ttl=86400)
def get_korean_name_map():
    return {
        '애플': 'AAPL', '아이폰': 'AAPL', '마이크로소프트': 'MSFT', '마소': 'MSFT',
        '구글': 'GOOGL', '알파벳': 'GOOGL', '아마존': 'AMZN', '테슬라': 'TSLA',
        '엔비디아': 'NVDA', '메타': 'META', '넷플릭스': 'NFLX', '암드': 'AMD',
        '인텔': 'INTC', '퀄컴': 'QCOM', '코카콜라': 'KO', '펩시': 'PEP',
        '스타벅스': 'SBUX', '맥도날드': 'MCD', '디즈니': 'DIS', '나이키': 'NKE',
        '리얼티인컴': 'O', '슈드': 'SCHD', '큐큐큐': 'QQQ', '스파이': 'SPY',
        '제피': 'JEPI', '속슬': 'SOXL', '티큐': 'TQQQ'
    }

def find_ticker(user_input, df_sp500):
    user_input = user_input.strip()
    upper_input = user_input.upper()
    
    k_map = get_korean_name_map()
    if user_input in k_map: return k_map[user_input]
        
    if df_sp500 is not None:
        if upper_input in df_sp500['Symbol'].values: return upper_input
        match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False)]
        if not match.empty: return match.iloc[0]['Symbol']

    return upper_input

def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        if current_price == 0: return None, None

        data = {
            'Price': current_price,
            'TargetPrice': info.get('targetMeanPrice', 0),
            'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
            'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
            'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
            'DIV': round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0,
            'Name': info.get('shortName', ticker),
            'MarketCap': info.get('marketCap', 0) # 시총 정보 추가
        }
        history = stock.history(period="1y")
        return data, history
    except:
        return None, None

# =========================================================
# 3. 채점 로직 (버핏 공식)
# =========================================================
def calculate_us_score(data):
    score = 0
    report = []
    
    roe = data['ROE']; per = data['PER']; pbr = data['PBR']; div = data['DIV']
    
    if roe >= 20: score += 50; report.append("✅ [수익성] ROE 20% 이상 (매우 우수)")
    elif roe >= 15: score += 30; report.append("✅ [수익성] ROE 15% 이상 (우수)")
    elif roe >= 10: score += 10;
    
    if 0 < pbr <= 1.5: score += 20; report.append("✅ [자산] PBR 1.5배 이하 (저평가)")
    elif 0 < pbr <= 4.0: score += 10;
    
    if 0 < per <= 15: score += 20; report.append("✅ [밸류] PER 15배 이하 (저평가)")
    elif 0 < per <= 25: score += 10;
    
    if div >= 1.5: score += 10; report.append("✅ [배당] 1.5% 이상")
    
    margin_rate = 0
    margin_text = "-"
    if data['TargetPrice'] > 0 and data['Price'] > 0:
        margin_rate = ((data['TargetPrice'] - data['Price']) / data['Price']) * 100
        if margin_rate > 0: margin_text = f"+{margin_rate:.1f}%"
        else: margin_text = f"{margin_rate:.1f}%"

    return score, report, margin_text, margin_rate

# =========================================================
# 4. 메인 화면
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")
st.markdown("### 💡 복잡한 분석은 끝! 종목만 넣으면 점수가 나옵니다.")
st.warning("⚠️ 투자 참고용이며, 모든 책임은 본인에게 있습니다.")

sp500_df = get_sp500_data()

tab1, tab2, tab3 = st.tabs(["🔍 종목 진단", "📋 S&P 500 리스트", "💎 업종별 보물찾기"])

# --- [탭 1] 종목 진단 ---
with tab1:
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1: input_text = st.text_input("종목 검색", placeholder="예: Apple, 테슬라, KO", label_visibility="collapsed")
        with c2: search_btn = st.form_submit_button("🔍 계산")

    if search_btn and input_text:
        ticker = find_ticker(input_text, sp500_df)
        with st.spinner(f"🇺🇸 '{ticker}' 분석 중..."):
            data, history = get_stock_info(ticker)
            
        if data:
            score, report, m_text, m_rate = calculate_us_score(data)
            st.divider()
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.subheader("종합 점수")
                if score >= 80: st.success(f"# 💎 {score}점\n**강력 매수**")
                elif score >= 60: st.info(f"# 🥇 {score}점\n**매수 추천**")
                elif score >= 40: st.warning(f"# ✋ {score}점\n**관망**")
                else: st.error(f"# 🧱 {score}점\n**주의**")
                st.markdown("---")
                if m_rate > 0: st.success(f"**💰 안전마진: {m_text}**")
                else: st.error(f"**⚠️ 안전마진: {m_text}**")
            with col_b:
                st.subheader(f"{data['Name']} ({ticker})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("현재가", f"${data['Price']:,.2f}")
                c2.metric("ROE", f"{data['ROE']}%")
                c3.metric("PER", f"{data['PER']}배")
                c4.metric("PBR", f"{data['PBR']}배")
            
            st.subheader("📉 1년 주가 차트")
            if history is not None: st.line_chart(history['Close'], color="#004e92")
            st.subheader("📝 상세 리포트")
            if report:
                for r in report: st.write(r)
            else: st.info("💡 저평가 요인이 부족합니다.")
        else: st.error(f"❌ '{ticker}' 데이터를 찾을 수 없습니다.")

# --- [탭 2] 리스트 ---
with tab2:
    st.subheader("S&P 500 종목 리스트")
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# --- [탭 3] 업종별 보물찾기 (핵심 기능 변경) ---
with tab3:
    st.subheader("💎 숨겨진 '100점' 주식 찾기")
    st.markdown("""
    시가총액 순위가 아닙니다. **실시간으로 계산기를 돌려 '점수가 높은 순서'대로 보여줍니다.**
    S&P 500 전 종목을 대상으로 하되, 속도를 위해 **업종(Sector)**을 선택해주세요.
    """)
    
    if sp500_df is not None:
        # 섹터 선택 상자
        sectors = sorted(sp500_df['Sector'].unique())
        selected_sector = st.selectbox("탐색할 업종을 선택하세요:", sectors)
        
        if st.button(f"🚀 '{selected_sector}' 분야 채점 시작"):
            # 해당 섹터 종목만 필터링
            targets = sp500_df[sp500_df['Sector'] == selected_sector]
            
            # 너무 많으면 50개로 제한 (서버 보호)
            if len(targets) > 50:
                st.info(f"💡 종목이 많아 상위 50개만 우선 분석합니다. (총 {len(targets)}개)")
                targets = targets.head(50)
            
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total = len(targets)
            for i, row in enumerate(targets.itertuples()):
                ticker = row.Symbol
                name = row.Name
                
                # 실시간 데이터 가져오기
                d, _ = get_stock_info(ticker)
                
                if d:
                    s, _, m_text, m_rate = calculate_us_score(d)
                    results.append({
                        '종목명': name,
                        '티커': ticker,
                        '점수': s,       # 핵심: 점수
                        '현재가': f"${d['Price']:,.2f}",
                        '안전마진': m_text,
                        'ROE': f"{d['ROE']}%",
                        'PER': d['PER']
                    })
                
                # 진행상황 업데이트
                progress = (i + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"🔍 {ticker} 채점 중... ({i+1}/{total})")
            
            progress_bar.empty()
            status_text.empty()
            
            if results:
                # [핵심] 점수(s) 높은 순서로 정렬!!!
                df_res = pd.DataFrame(results).sort_values(by='점수', ascending=False)
                df_res.index = range(1, len(df_res) + 1) # 1위부터 순위 매기기
                
                # 1등 강조
                top_stock = df_res.iloc[0]
                st.balloons()
                st.success(f"🏆 **1위 발견!** : {top_stock['종목명']} ({top_stock['점수']}점)")
                
                st.markdown("### 📊 채점 결과 랭킹 (Top 10)")
                st.dataframe(df_res.head(10), use_container_width=True)
            else:
                st.error("데이터를 가져오지 못했습니다.")

# =========================================================
# 5. 수익화 사이드바
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    st.caption("서버비 유지에 큰 힘이 됩니다! 🙇‍♂️")
    
    t1, t2 = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    
    with t1:
        st.write(" ")
        my_link = "https://buymeacoffee.com/jh.choi" 
        st.markdown(f"""
        <a href="{my_link}" target="_blank">
            <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 45px !important;width: 100% !important;" >
        </a>
        """, unsafe_allow_html=True)

    with t2:
        st.write(" ")
        import os
        if os.path.exists("kakao_qr.png"):
            st.image("kakao_qr.png", caption="📷 스캔하면 바로 송금됩니다", use_container_width=True)
            st.caption("예금주: 최주환") 
        else:
            st.warning("QR 이미지가 없습니다.")

    # 2. 쿠팡 파트너스 (책 추천)
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
        
