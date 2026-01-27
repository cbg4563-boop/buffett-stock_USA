import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # 사이드바 에러 방지
import time  # 야후 차단 방지

# =========================================================
# 1. 페이지 설정 및 내비게이션 상태 관리
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

# [핵심] 탭 이동과 검색어를 제어하기 위한 세션 상태
if 'active_tab' not in st.session_state:
    st.session_state['active_tab'] = "🔍 종목 진단"
if 'target_ticker' not in st.session_state:
    st.session_state['target_ticker'] = ""

st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] > div:has(input[type="radio"]) {
        background-color: #f8f9fb; padding: 15px; border-radius: 15px; border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 데이터 처리 & 스마트 검색 로직 [해결] 한글/영어 검색
# =========================================================
@st.cache_data(ttl=86400)
def get_sp500_data():
    try: return fdr.StockListing('S&P500')
    except: return None

def get_sector_map():
    return {
        'Energy': '에너지', 'Materials': '소재/화학', 'Industrials': '산업재',
        'Consumer Discretionary': '경기소비재', 'Consumer Staples': '필수소비재',
        'Health Care': '헬스케어', 'Financials': '금융',
        'Information Technology': 'IT/기술', 'Communication Services': '통신서비스',
        'Utilities': '유틸리티', 'Real Estate': '부동산'
    }

@st.cache_data(ttl=86400)
def get_korean_name_map():
    # 사장님이 요청하신 한글 검색 지원용 맵핑
    return {
        '애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '구글': 'GOOGL', '아마존': 'AMZN',
        '엔비디아': 'NVDA', '메타': 'META', '페이스북': 'META', '넷플릭스': 'NFLX', 
        '인텔': 'INTC', '코카콜라': 'KO', '펩시': 'PEP', '스타벅스': 'SBUX', '디즈니': 'DIS'
    }

def find_ticker(user_input, df_sp500):
    user_input = user_input.strip()
    # 1. 한글 이름 확인
    k_map = get_korean_name_map()
    if user_input in k_map: return k_map[user_input]
    
    if df_sp500 is not None:
        upper_input = user_input.upper()
        # 2. 티커로 직접 검색 (AAPL)
        if upper_input in df_sp500['Symbol'].values: return upper_input
        # 3. 영어 이름으로 검색 (Apple -> AAPL)
        match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False)]
        if not match.empty: return match.iloc[0]['Symbol']
        
    return user_input.upper()

def get_stock_info(ticker):
    # [해결] 데이터 수집 실패 방지를 위한 예외 처리 및 대기 시간
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
            'DIV': round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0,
            'Name': info.get('shortName', ticker)
        }
        history = stock.history(period="1y")
        return data, history
    except:
        return None, None

def calculate_score(data):
    score = 0
    roe, per, pbr, div = data['ROE'], data['PER'], data['PBR'], data['DIV']
    if roe >= 15: score += 50
    if 0 < pbr <= 2.0: score += 20
    if 0 < per <= 20: score += 20
    if div >= 1.0: score += 10
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, f"{m_rate:.1f}%", m_rate

# =========================================================
# 3. 메인 화면 구성
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

# 탭 대신 라디오 내비게이션 (강제 이동을 위함)
menu = ["🔍 종목 진단", "📋 S&P 500 리스트", "🏆 분야별 TOP 5 랭킹"]
choice = st.radio("메뉴", menu, index=menu.index(st.session_state['active_tab']), horizontal=True, label_visibility="collapsed")
st.session_state['active_tab'] = choice

sp500_df = get_sp500_data()
sector_map = get_sector_map()

st.markdown("---")

# --- [1] 종목 진단 (한글/영어 완벽 검색) ---
if choice == "🔍 종목 진단":
    search_q = st.session_state['target_ticker']
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1: input_text = st.text_input("종목명(애플), 영어(Apple), 티커(AAPL) 입력", value=search_q, placeholder="예: 애플, 테슬라, NVDA", label_visibility="collapsed")
        with c2: search_btn = st.form_submit_button("🔍 계산")

    if (search_btn and input_text) or (search_q and input_text):
        if search_q: st.session_state['target_ticker'] = ""
        ticker = find_ticker(input_text, sp500_df)
        with st.spinner(f"🇺🇸 {ticker} 정밀 분석 중..."):
            data, history = get_stock_info(ticker)
            if data:
                score, m_text, m_rate = calculate_score(data)
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.subheader("종합 점수")
                    if score >= 60: st.success(f"# 💎 {score}점")
                    else: st.warning(f"# ✋ {score}점")
                    st.metric("안전마진", m_text, delta=f"{m_rate:.1f}%")
                with col_b:
                    st.subheader(f"{data['Name']} ({ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${data['Price']}")
                    m2.metric("ROE", f"{data['ROE']}%")
                    m3.metric("PER", f"{data['PER']}배")
                    m4.metric("PBR", f"{data['PBR']}배")
                st.line_chart(history['Close'], color="#004e92")
            else: st.error("데이터 수집 실패. 잠시 후 다시 시도하세요.")

# --- [3] 분야별 TOP 5 (사장님 요청: 표 형태 출력)
elif choice == "🏆 분야별 TOP 5 랭킹":
    st.subheader("💎 업종별 워렌 버핏 점수 TOP 5")
    if sp500_df is not None:
        sectors = sorted(sp500_df['Sector'].unique())
        options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        selected = st.selectbox("업종 선택", options)
        pure_sector = selected.split(' (')[0]
        
        if st.button(f"🚀 {pure_sector} TOP 5 추출"):
            targets = sp500_df[sp500_df['Sector'] == pure_sector].head(25)
            results = []
            bar = st.progress(0)
            status = st.empty()
            
            for i, row in enumerate(targets.itertuples()):
                status.text(f"🔍 {row.Symbol} 분석 중... ({i+1}/{len(targets)})")
                time.sleep(0.5) # [해결] 야후 차단 방지 대기 시간
                
                d, _ = get_stock_info(row.Symbol)
                if d:
                    s, m_t, _ = calculate_score(d)
                    results.append({'티커': row.Symbol, '종목명': d['Name'], '점수': s, '안전마진': m_t, 'ROE': f"{d['ROE']}%", '현재가': f"${d['Price']}"})
                bar.progress((i + 1) / len(targets))
            
            status.empty()
            if results:
                # [해결] 점수 순 표 형태 출력
                final_df = pd.DataFrame(results).sort_values('점수', ascending=False).head(5)
                final_df.index = range(1, len(final_df) + 1)
                st.success("✅ 분석 완료!")
                st.table(final_df) 
            else: st.error("데이터 수집 실패. 잠시 후 다시 시도하세요.")

elif choice == "📋 S&P 500 리스트":
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# =========================================================
# 5. 수익화 사이드바 [해결] 예금주 최*환 수정
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    tab_card, tab_kakao = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with tab_card:
        st.markdown(f'<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with tab_kakao:
        qr_file = "kakao_qr.png.jpg"
        if os.path.exists(qr_file):
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최*환") # [요청] 예금주 이름 마스킹 수정 완료
    st.markdown("---")
    # [요청] 워렌 버핏 바이블 문구 반영
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
