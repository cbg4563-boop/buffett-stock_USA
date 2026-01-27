import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # [해결] NameError: os를 찾지 못하던 문제 수정
import time  # [해결] 데이터 수집 실패 방지를 위한 대기 시간 추가

# =========================================================
# 1. 페이지 설정 및 상태 초기화
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

# [해결] ValueError 방지를 위해 메뉴 이름을 정확히 일치시킵니다.
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
# 2. 스마트 검색 및 데이터 처리 로직
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
    # [기능] 한글 종목명 검색 지원
    return {
        '애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '구글': 'GOOGL', '아마존': 'AMZN',
        '엔비디아': 'NVDA', '메타': 'META', '페이스북': 'META', '넷플릭스': 'NFLX', 
        '인텔': 'INTC', '코카콜라': 'KO', '펩시': 'PEP', '스타벅스': 'SBUX', '디즈니': 'DIS'
    }

def find_ticker(user_input, df_sp500):
    user_input = user_input.strip()
    k_map = get_korean_name_map()
    if user_input in k_map: return k_map[user_input]
    if df_sp500 is not None:
        upper_input = user_input.upper()
        if upper_input in df_sp500['Symbol'].values: return upper_input
        # [기능] 영어 이름으로 검색 가능하게 수정
        match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False)]
        if not match.empty: return match.iloc[0]['Symbol']
    return user_input.upper()

def get_stock_info(ticker):
    # [해결] 데이터 로딩 안정성 강화: 1년치 주가 그래프 데이터 포함
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
        # [복구] 주가 그래프를 위한 히스토리 데이터
        history = stock.history(period="1y")
        return data, history
    except:
        return None, None

def calculate_score(data):
    score = 0
    roe, per, pbr = data['ROE'], data['PER'], data['PBR']
    if roe >= 15: score += 50
    if 0 < pbr <= 2.0: score += 30
    if 0 < per <= 20: score += 20
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, f"{m_rate:.1f}%", m_rate

# =========================================================
# 3. 메인 내비게이션 (라디오 버튼)
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

# [해결] ValueError 방지: 세션 상태를 이용한 인덱스 관리
choice = st.radio("메뉴", menu_list, index=menu_list.index(st.session_state['nav_choice']), horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = choice

sp500_df = get_sp500_data()
sector_map = get_sector_map()

st.markdown("---")

# =========================================================
# 4. 기능별 페이지 구현
# =========================================================

# --- [1] 종목 진단 (그래프 복구 완료) ---
if choice == "🔍 종목 진단":
    ticker_to_search = st.session_state['search_ticker']
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_text = st.text_input("한글/영어/티커를 입력하세요", value=ticker_to_search, placeholder="예: 애플, 테슬라, NVDA", label_visibility="collapsed")
        with c2:
            search_btn = st.form_submit_button("🔍 계산하기")

    if (search_btn and input_text) or (ticker_to_search and input_text):
        if ticker_to_search: st.session_state['search_ticker'] = ""
        ticker = find_ticker(input_text, sp500_df)
        with st.spinner(f"🇺🇸 {ticker} 데이터 및 그래프 불러오는 중..."):
            data, history = get_stock_info(ticker)
            if data:
                score, m_text, m_rate = calculate_score(data)
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.subheader("종합 점수")
                    st.success(f"# 💎 {score}점") if score >= 60 else st.warning(f"# ✋ {score}점")
                    st.metric("안전마진", m_text, delta=f"{m_rate:.1f}%")
                with col_b:
                    st.subheader(f"{data['Name']} ({ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${data['Price']}")
                    m2.metric("ROE", f"{data['ROE']}%")
                    m3.metric("PER", f"{data['PER']}배")
                    m4.metric("PBR", f"{data['PBR']}배")
                
                # [복구] 1년 주가 흐름 그래프
                st.subheader("📈 1년 주가 흐름")
                if not history.empty:
                    st.line_chart(history['Close'], color="#004e92")
                else:
                    st.info("차트 데이터를 불러올 수 없습니다.")
            else:
                st.error("데이터 수집 실패. 잠시 후 다시 시도하세요.")

# --- [3] 분야별 TOP 5 (표 형태 출력) ---
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
            status = st.empty()
            
            for i, row in enumerate(targets.itertuples()):
                status.text(f"🔍 {row.Symbol} 분석 중... ({i+1}/{len(targets)})")
                time.sleep(0.5) # [해결] 데이터 수집 실패 방지를 위한 딜레이
                
                d, _ = get_stock_info(row.Symbol)
                if d:
                    s, m_t, _ = calculate_score(d)
                    results.append({'순위': 0, '티커': row.Symbol, '종목명': d['Name'], '점수': s, '안전마진': m_t, '현재가': f"${d['Price']}", 'ROE': f"{d['ROE']}%"})
                bar.progress((i+1)/len(targets))
            
            status.empty()
            if results:
                # [기능] 점수 순으로 정렬하여 표 형태로 출력
                final_df = pd.DataFrame(results).sort_values('점수', ascending=False).head(5)
                final_df['순위'] = range(1, len(final_df) + 1)
                st.success("✅ 분석 완료!")
                st.table(final_df.set_index('순위'))
                
                # [기능] 진단 버튼 대신 하단 바로가기 (안정성 강화)
                st.markdown("#### 🔍 상세 진단")
                cols = st.columns(5)
                for idx, row in enumerate(final_df.to_dict('records')):
                    if cols[idx].button(f"{row['티커']} 분석", key=f"btn_{row['티커']}"):
                        st.session_state['search_ticker'] = row['티커']
                        st.session_state['nav_choice'] = "🔍 종목 진단"
                        st.rerun()
            else: st.error("데이터 수집 실패. 잠시 후 다시 시도하세요.")

elif choice == "📋 S&P 500 리스트":
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# =========================================================
# 5. 수익화 사이드바 (예금주 최*환 수정)
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    tab_card, tab_kakao = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with tab_card:
        st.markdown(f'<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with tab_kakao:
        qr_file = "kakao_qr.png.jpg"
        if os.path.exists(qr_file): #
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최*환") # [요청] 최*환 수정 완료
    st.markdown("---")
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
    st.caption("※ 파트너스 활동으로 수수료가 발생할 수 있습니다.")
