import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import time

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

# 스타일 (Radio 버튼을 탭처럼 보이게 만듦)
st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    div[data-testid="stMetric"] label { color: #666666 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #000000 !important; }
    
    /* 라디오 버튼 탭 스타일링 */
    div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] > div:has(input[type="radio"]) {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 데이터 처리 & 로직 (이전과 동일)
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
    return {
        '애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '구글': 'GOOGL', '아마존': 'AMZN',
        '엔비디아': 'NVDA', '메타': 'META', '넷플릭스': 'NFLX', '코카콜라': 'KO'
    }

def find_ticker(user_input, df_sp500):
    user_input = user_input.strip()
    k_map = get_korean_name_map()
    if user_input in k_map: return k_map[user_input]
    if df_sp500 is not None:
        upper_input = user_input.upper()
        if upper_input in df_sp500['Symbol'].values: return upper_input
        match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False)]
        if not match.empty: return match.iloc[0]['Symbol']
    return user_input.upper()

def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        if price == 0: return None, None
        data = {
            'Price': price, 'TargetPrice': info.get('targetMeanPrice', 0),
            'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
            'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
            'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
            'DIV': round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0,
            'Name': info.get('shortName', ticker)
        }
        return data, stock.history(period="1y")
    except: return None, None

def calculate_us_score(data):
    score = 0
    report = []
    roe, per, pbr, div = data['ROE'], data['PER'], data['PBR'], data['DIV']
    if roe >= 15: score += 50; report.append("✅ [수익성] ROE 우수")
    if 0 < pbr <= 2.0: score += 20; report.append("✅ [자산] PBR 저평가")
    if 0 < per <= 20: score += 20; report.append("✅ [밸류] PER 적정")
    if div >= 1.0: score += 10; report.append("✅ [배당] 매력적")
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, report, f"{m_rate:.1f}%", m_rate

# =========================================================
# 3. 내비게이션 메뉴 (탭 역할)
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

# [핵심] 기존 st.tabs 대신 Radio 버튼으로 탭 구현 (강제 이동 가능)
menu = ["🔍 종목 진단", "📋 S&P 500 리스트", "💎 업종별 보물찾기"]
choice = st.radio("메뉴 선택", menu, index=menu.index(st.session_state['active_tab']), horizontal=True, label_visibility="collapsed")
st.session_state['active_tab'] = choice # 현재 선택된 메뉴 저장

sp500_df = get_sp500_data()
sector_map = get_sector_map()

st.markdown("---")

# =========================================================
# 4. 각 메뉴별 화면 구현
# =========================================================

# --- [메뉴 1] 종목 진단 ---
if choice == "🔍 종목 진단":
    search_query = st.session_state['target_ticker']
    
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_text = st.text_input("종목 입력", value=search_query, placeholder="예: Apple, 테슬라", label_visibility="collapsed")
        with c2:
            search_btn = st.form_submit_button("🔍 계산하기")

    # 버튼을 눌렀거나, 보물찾기에서 넘어온 경우 실행
    if search_btn or search_query:
        if search_query:
            st.session_state['target_ticker'] = "" # 사용 후 초기화
        
        ticker = find_ticker(input_text, sp500_df)
        with st.spinner(f"🇺🇸 {ticker} 분석 중..."):
            data, history = get_stock_info(ticker)
            
        if data:
            score, report, m_text, m_rate = calculate_us_score(data)
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
            st.line_chart(history['Close'])
            for r in report: st.write(r)
        else:
            st.error("종목을 찾을 수 없습니다.")

# --- [메뉴 2] 리스트 ---
elif choice == "📋 S&P 500 리스트":
    st.subheader("S&P 500 종목 현황")
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True)

# --- [메뉴 3] 업종별 보물찾기 ---
elif choice == "💎 업종별 보물찾기":
    st.subheader("💎 업종별 저평가 우량주 발굴")
    if sp500_df is not None:
        sectors = sorted(sp500_df['Sector'].unique())
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        selected = st.selectbox("업종 선택", sector_options)
        real_sector = selected.split(' (')[0]
        
        if st.button(f"🚀 {real_sector} 분석 시작"):
            targets = sp500_df[sp500_df['Sector'] == real_sector].head(30)
            results = []
            bar = st.progress(0)
            for i, row in enumerate(targets.itertuples()):
                d, _ = get_stock_info(row.Symbol)
                if d:
                    s, _, m_text, _ = calculate_us_score(d)
                    results.append({'티커': row.Symbol, '종목명': d['Name'], '점수': s, '현재가': f"${d['Price']}", '안전마진': m_text})
                bar.progress((i+1)/len(targets))
            
            if results:
                df_res = pd.DataFrame(results).sort_values('점수', ascending=False)
                for row in df_res.head(10).to_dict('records'):
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                    c1.write(f"**{row['티커']}**")
                    c2.write(row['종목명'])
                    c3.write(f"**{row['점수']}점**")
                    # [핵심] 진단하기 버튼 클릭 시 세션 상태 변경 후 리런
                    if c4.button(f"🔍 진단", key=f"btn_{row['티커']}"):
                        st.session_state['target_ticker'] = row['티커']
                        st.session_state['active_tab'] = "🔍 종목 진단" # 강제 메뉴 이동
                        st.rerun()

# =========================================================
# 5. 수익화 사이드바 (동일)
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 후원")
    my_link = "https://buymeacoffee.com/cbg4563t" 
    st.markdown(f'<a href="{my_link}" target="_blank"> 후원하기 </a>', unsafe_allow_html=True)
    import os
    if os.path.exists("kakao_qr.png.jpg"):
        st.image("kakao_qr.png.jpg", caption="카카오 송금")
        
    # 2. 쿠팡 파트너스 (책 추천)
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
        



