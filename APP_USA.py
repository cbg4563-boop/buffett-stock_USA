import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # [해결] NameError 차단
import time  # [해결] 데이터 수집 차단 방지

# =========================================================
# 1. 페이지 설정 및 내비게이션 상태 초기화
# =========================================================
st.set_page_config(
    page_title="워렌 버핏 주식매매 기준 계산기",
    page_icon="🗽",
    layout="wide"
)

# 메뉴 목록 정의 (토씨 하나 틀리면 안 됩니다)
menu_list = ["🔍 종목 진단", "📋 S&P 500 리스트", "🏆 분야별 TOP 5 랭킹"]

# 세션 상태 초기화 [해결] ValueError 방지
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
# 2. 스마트 검색 엔진 (한글/영어/티커 완벽 대응)
# =========================================================
@st.cache_data(ttl=86400)
def get_sp500_data():
    try: return fdr.StockListing('S&P500')
    except: return None

@st.cache_data(ttl=86400)
def get_korean_name_map():
    # [해결] 한글로 검색해도 티커를 찾아주는 마법 사전
    return {
        '애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '마이크로소프트': 'MSFT',
        '구글': 'GOOGL', '알파벳': 'GOOGL', '아마존': 'AMZN', '엔비디아': 'NVDA',
        '메타': 'META', '페이스북': 'META', '넷플릭스': 'NFLX', '인텔': 'INTC',
        '코카콜라': 'KO', '펩시': 'PEP', '스타벅스': 'SBUX', '디즈니': 'DIS'
    }

def find_ticker(user_input, df_sp500):
    user_input = user_input.strip()
    if not user_input: return ""
    
    # 1. 한글 사전에서 먼저 찾기
    k_map = get_korean_name_map()
    if user_input in k_map: return k_map[user_input]
    
    if df_sp500 is not None:
        upper_input = user_input.upper()
        # 2. 티커랑 똑같은지 확인 (AAPL)
        if upper_input in df_sp500['Symbol'].values: return upper_input
        # 3. 영어 회사 이름에 포함되는지 확인 (Apple)
        match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False)]
        if not match.empty: return match.iloc[0]['Symbol']
        
    return user_input.upper()

def get_stock_info(ticker):
    # [해결] 데이터 로딩 안정성 확보 및 그래프 데이터 포함
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        if price == 0: return None, None
        
        data = {
            'Price': price,
            'TargetPrice': info.get('targetMeanPrice', 0),
            'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
            'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
            'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
            'Name': info.get('shortName', ticker)
        }
        history = stock.history(period="1y")
        return data, history
    except:
        return None, None

def calculate_score(data):
    score = 0
    if data['ROE'] >= 15: score += 50
    if 0 < data['PBR'] <= 2.0: score += 30
    if 0 < data['PER'] <= 20: score += 20
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, f"{m_rate:.1f}%", m_rate

# =========================================================
# 3. 메인 내비게이션
# =========================================================
st.title("🗽 워렌 버핏 주식매매 기준 계산기")

# [해결] ValueError 방지: 안전하게 인덱스 추출
try:
    current_idx = menu_list.index(st.session_state['nav_choice'])
except ValueError:
    current_idx = 0

choice = st.radio("메뉴", menu_list, index=current_idx, horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = choice

sp500_df = get_sp500_data()
st.markdown("---")

# =========================================================
# 4. 기능별 페이지 구현
# =========================================================

# --- [1] 종목 진단 (검색 기능 복구) ---
if choice == menu_list[0]:
    # 랭킹에서 넘어온 티커가 있다면 자동으로 입력
    ticker_val = st.session_state['search_ticker']
    
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_text = st.text_input("한글(애플), 영어(Apple), 티커(AAPL) 모두 검색 가능", value=ticker_val, placeholder="예: 테슬라, NVDA, 마소", label_visibility="collapsed")
        with c2:
            search_btn = st.form_submit_button("🔍 계산하기")

    if (search_btn and input_text) or (ticker_val and input_text):
        if ticker_val: st.session_state['search_ticker'] = "" # 사용 후 초기화
        
        target_ticker = find_ticker(input_text, sp500_df)
        with st.spinner(f"🇺🇸 {target_ticker} 분석 중..."):
            data, history = get_stock_info(target_ticker)
            if data:
                score, m_text, m_rate = calculate_score(data)
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.subheader("종합 점수")
                    # [해결] DeltaGenerator 에러 방지
                    if score >= 60:
                        st.success(f"# 💎 {score}점")
                    else:
                        st.warning(f"# ✋ {score}점")
                    st.metric("안전마진", m_text, delta=f"{m_rate:.1f}%")
                with col_b:
                    st.subheader(f"{data['Name']} ({target_ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${data['Price']}")
                    m2.metric("ROE", f"{data['ROE']}%")
                    m3.metric("PER", f"{data['PER']}배")
                    m4.metric("PBR", f"{data['PBR']}배")
                
                if history is not None and not history.empty:
                    st.subheader("📈 1년 주가 흐름")
                    st.line_chart(history['Close'], color="#004e92")
            else:
                st.error("데이터를 불러올 수 없습니다. 티커를 확인하거나 잠시 후 다시 시도하세요.")

# --- [3] 분야별 TOP 5 (표 형태 고정) ---
elif choice == menu_list[2]:
    st.subheader("🏆 분야별 워렌 버핏 점수 TOP 5")
    if sp500_df is not None:
        sectors = sorted(sp500_df['Sector'].unique())
        selected = st.selectbox("업종 선택", sectors)
        
        if st.button(f"🚀 {selected} 분석 시작"):
            targets = sp500_df[sp500_df['Sector'] == selected].head(25)
            results = []
            bar = st.progress(0)
            status = st.empty()
            
            for i, row in enumerate(targets.itertuples()):
                status.text(f"🔍 {row.Symbol} 채점 중... ({i+1}/{len(targets)})")
                time.sleep(0.4) # [해결] 야후 차단 방지
                d, _ = get_stock_info(row.Symbol)
                if d:
                    s, m_t, _ = calculate_score(d)
                    results.append({'티커': row.Symbol, '종목명': d['Name'], '점수': s, '안전마진': m_t, '현재가': f"${d['Price']}", 'ROE': f"{d['ROE']}%"})
                bar.progress((i+1)/len(targets))
            
            status.empty()
            if results:
                # 점수 높은 순으로 표 출력
                final_df = pd.DataFrame(results).sort_values('점수', ascending=False).head(5)
                final_df.insert(0, '순위', range(1, len(final_df) + 1))
                st.success("✅ 분석 완료!")
                st.table(final_df.set_index('순위'))
            else:
                st.error("데이터 수집 실패. 잠시 후 다시 시도하세요.")

# =========================================================
# 5. 사이드바 (최*환 마스킹 완료)
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    tab1, tab2 = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with tab1:
        st.markdown(f'<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with tab2:
        qr_file = "kakao_qr.png.jpg"
        if os.path.exists(qr_file):
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최*환") # 마스킹 완료
    st.markdown("---")
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
