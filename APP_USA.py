import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # [해결] NameError 방지
import time  # [해결] 데이터 수집 실패 방지

# =========================================================
# 1. 페이지 설정 및 내비게이션 상태 초기화
# =========================================================
st.set_page_config(
    page_title="워렌 버핏 주식매매 기준 계산기",
    page_icon="🗽",
    layout="wide"
)

# [해결] ValueError 방지를 위해 메뉴 이름을 정확히 정의합니다.
menu_list = ["🔍 종목 진단", "📋 S&P 500 리스트", "🏆 분야별 TOP 5 랭킹"]

if 'nav_choice' not in st.session_state:
    st.session_state['nav_choice'] = menu_list[0]
if 'search_ticker' not in st.session_state:
    st.session_state['search_ticker'] = ""

# 스타일 설정
st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] > div:has(input[type="radio"]) {
        background-color: #f8f9fb; padding: 15px; border-radius: 15px; border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 필수 데이터 및 로직 함수
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

def get_stock_info(ticker):
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
        return data, stock.history(period="1y")
    except: return None, None

def calculate_score(data):
    score = 0
    if data['ROE'] >= 15: score += 50
    if 0 < data['PBR'] <= 2.0: score += 30
    if 0 < data['PER'] <= 20: score += 20
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, f"{m_rate:.1f}%"

# =========================================================
# 3. 메인 내비게이션
# =========================================================
st.title("🗽 워렌 버핏 주식매매 기준 계산기")

# [해결] ValueError 방지: 메뉴 인덱스 정확히 매칭
try:
    current_index = menu_list.index(st.session_state['nav_choice'])
except ValueError:
    current_index = 0

choice = st.radio("메뉴", menu_list, index=current_index, horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = choice

sp500_df = get_sp500_data()
sector_map = get_sector_map()
st.markdown("---")

# =========================================================
# 4. 기능별 페이지 구현
# =========================================================

# --- [1] 종목 진단 ---
if choice == "🔍 종목 진단":
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1: input_text = st.text_input("종목 티커를 입력하세요 (예: AAPL)", value=st.session_state['search_ticker'])
        with c2: search_btn = st.form_submit_button("🔍 계산하기")
    
    if search_btn and input_text:
        st.session_state['search_ticker'] = ""
        with st.spinner("분석 중..."):
            data, history = get_stock_info(input_text.upper())
            if data:
                score, m_text = calculate_score(data)
                st.metric(f"{data['Name']} 점수", f"{score}점", delta=f"안전마진 {m_text}")
                st.line_chart(history['Close'])
            else: st.error("데이터를 찾을 수 없습니다.")

# --- [2] 리스트 ---
elif choice == "📋 S&P 500 리스트":
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# --- [3] 분야별 TOP 5 (사장님 요청: 버튼 삭제 + 표 복구 버전) ---
elif choice == "🏆 분야별 TOP 5 랭킹":
    st.subheader("🏆 분야별 워렌 버핏 점수 TOP 5")
    
    if sp500_df is not None:
        sectors = sorted(sp500_df['Sector'].unique())
        options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        selected = st.selectbox("업종 선택", options)
        pure_sector = selected.split(' (')[0]
        
        if st.button(f"🚀 {pure_sector} TOP 5 분석 시작"):
            targets = sp500_df[sp500_df['Sector'] == pure_sector].head(25)
            results = []
            bar = st.progress(0)
            
            for i, row in enumerate(targets.itertuples()):
                time.sleep(0.4) 
                d, _ = get_stock_info(row.Symbol)
                if d:
                    score, m_t = calculate_score(d)
                    results.append({
                        '순위': 0, '티커': row.Symbol, '종목명': d['Name'], 
                        '점수': score, '안전마진': m_t, '현재가': f"${d['Price']}", 'ROE': f"{d['ROE']}%"
                    })
                bar.progress((i+1)/len(targets))
            
            if results:
                # [복구] 점수 순으로 정렬하여 표(Table)로 출력
                final_df = pd.DataFrame(results).sort_values('점수', ascending=False).head(5)
                final_df['순위'] = range(1, len(final_df) + 1)
                st.success(f"✅ {pure_sector} 분석 완료!")
                st.table(final_df.set_index('순위')) # 진단하기 버튼 없이 표만 노출
            else:
                st.error("데이터 수집에 실패했습니다. 다시 시도해 주세요.")

# =========================================================
# 5. 수익화 사이드바
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
