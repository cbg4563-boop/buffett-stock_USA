import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # [해결] NameError 방지
import time  # [해결] 야후 차단 및 수집 실패 방지

# =========================================================
# 1. 페이지 설정 및 상태 초기화
# =========================================================
st.set_page_config(page_title="워렌 버핏의 미국 주식 계산기", page_icon="🗽", layout="wide")

menu_list = ["🔍 종목 진단", "📋 S&P 500 리스트", "🏆 분야별 TOP 5 랭킹"]

if 'nav_choice' not in st.session_state:
    st.session_state['nav_choice'] = menu_list[0]
if 'search_ticker' not in st.session_state:
    st.session_state['search_ticker'] = ""

st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] > div:has(input[type="radio"]) {
        background-color: #f8f9fb; padding: 15px; border-radius: 15px; border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 스마트 검색 및 재시도 수집 로직
# =========================================================
@st.cache_data(ttl=86400)
def get_sp500_data():
    try: return fdr.StockListing('S&P500')
    except: return None

@st.cache_data(ttl=86400)
def get_korean_map():
    # [기능] 주요 종목 한글 매핑
    return {'애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '엔비디아': 'NVDA', '클로락스': 'CLX', '코카콜라': 'KO'}

def find_ticker_smart(user_input, df_sp500):
    """[해결] Clorox Company 검색 시 CLX를 찾아내는 지능형 검색"""
    user_input = user_input.strip()
    if not user_input: return ""
    
    # 1. 한글 매핑 확인
    k_map = get_korean_map()
    if user_input in k_map: return k_map[user_input]
    
    if df_sp500 is not None:
        upper_in = user_input.upper()
        # 2. 티커 완전 일치 확인 (CLX)
        if upper_in in df_sp500['Symbol'].values: return upper_in
        # 3. 이름 부분 일치 검색 (Clorox -> The Clorox Company)
        match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False)]
        if not match.empty: return match.iloc[0]['Symbol']
        
    return user_input.upper()

def get_stock_with_retry(ticker):
    """[해결] 데이터 수집 실패 시 재시도 로직"""
    for i in range(2):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            if price > 0:
                data = {
                    'Price': price, 'TargetPrice': info.get('targetMeanPrice', 0),
                    'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
                    'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
                    'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
                    'Name': info.get('shortName', ticker)
                }
                history = stock.history(period="1y")
                return data, history
            time.sleep(0.5)
        except:
            time.sleep(0.5)
    return None, None

# =========================================================
# 3. 메인 화면 구성
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

try:
    current_idx = menu_list.index(st.session_state['nav_choice'])
except:
    current_idx = 0

choice = st.radio("메뉴", menu_list, index=current_idx, horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = choice

sp500_df = get_sp500_data()
st.markdown("---")

# --- [1] 종목 진단 (검색 및 그래프 복구) ---
if choice == menu_list[0]:
    t_val = st.session_state['search_ticker']
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            in_txt = st.text_input("종목명(Clorox) 또는 티커(CLX) 입력", value=t_val, placeholder="예: 애플, TSLA, NVDA", label_visibility="collapsed")
        with c2:
            btn = st.form_submit_button("🔍 진단하기")

    if (btn and in_txt) or (t_val and in_txt):
        if t_val: st.session_state['search_ticker'] = ""
        ticker = find_ticker_smart(in_txt, sp500_df)
        
        with st.spinner(f"🇺🇸 {ticker} 데이터 수집 중..."):
            data, history = get_stock_with_retry(ticker)
            if data:
                score = 0
                if data['ROE'] >= 15: score += 50
                if 0 < data['PBR'] <= 2.0: score += 30
                if 0 < data['PER'] <= 20: score += 20
                m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
                
                # [해결] DeltaGenerator 에러 방지용 정석 출력
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.subheader("종합 점수")
                    if score >= 60: st.success(f"# 💎 {score}점")
                    else: st.warning(f"# ✋ {score}점")
                    st.metric("안전마진", f"{m_rate:.1f}%", delta=f"{m_rate:.1f}%")
                with col_b:
                    st.subheader(f"{data['Name']} ({ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${data['Price']}")
                    m2.metric("ROE", f"{data['ROE']}%")
                    m3.metric("PER", f"{data['PER']}배")
                    m4.metric("PBR", f"{data['PBR']}배")
                
                if not history.empty:
                    st.subheader("📈 최근 1년 주가 흐름")
                    st.line_chart(history['Close'], color="#004e92")
            else:
                st.error("데이터 수집에 실패했습니다. 잠시 후 다시 시도해 주세요.")

# --- [3] 분야별 TOP 5 (표 전용) ---
elif choice == menu_list[2]:
    st.subheader("🏆 분야별 워렌 버핏 점수 TOP 5")
    if sp500_df is not None:
        sects = sorted(sp500_df['Sector'].unique())
        sel = st.selectbox("분석할 업종을 선택하세요", sects)
        
        if st.button(f"🚀 {sel} TOP 5 분석 시작"):
            targets = sp500_df[sp500_df['Sector'] == sel].head(20)
            res = []
            p_bar = st.progress(0)
            for i, row in enumerate(targets.itertuples()):
                time.sleep(0.4) 
                d, _ = get_stock_with_retry(row.Symbol)
                if d:
                    s = 0
                    if d['ROE'] >= 15: s += 50
                    if 0 < d['PBR'] <= 2.0: s += 30
                    if 0 < d['PER'] <= 20: s += 20
                    m_t = f"{((d['TargetPrice']-d['Price'])/d['Price']*100):.1f}%" if d['TargetPrice'] > 0 else "-"
                    res.append({'티커': row.Symbol, '종목명': d['Name'], '점수': s, '안전마진': m_t, '현재가': f"${d['Price']}"})
                p_bar.progress((i+1)/len(targets))
            
            if res:
                final = pd.DataFrame(res).sort_values('점수', ascending=False).head(5)
                final.index = range(1, len(final) + 1)
                st.table(final)
            else: st.error("데이터 수집 실패")

elif choice == menu_list[1]:
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# =========================================================
# 5. 수익화 사이드바
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    t1, t2 = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with t1:
        st.markdown(f'<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with t2:
        qr = "kakao_qr.png.jpg"
        if os.path.exists(qr):
            st.image(qr, use_container_width=True)
            st.caption("예금주: 최*환")
    st.markdown("---")
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
