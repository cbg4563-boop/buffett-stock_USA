import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # [해결] NameError 차단
import time  # [해결] 데이터 수집 실패(차단) 방지

# =========================================================
# 1. 페이지 설정 및 상태 초기화
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

# [해결] ValueError 방지: 메뉴 이름을 명확히 정의합니다.
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
# 2. 스마트 검색 및 데이터 처리 (한글/영어/그래프 지원)
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
        '애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '마이크로소프트': 'MSFT',
        '구글': 'GOOGL', '아마존': 'AMZN', '엔비디아': 'NVDA', '메타': 'META',
        '넷플릭스': 'NFLX', '코카콜라': 'KO', '펩시': 'PEP', '스타벅스': 'SBUX'
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
            'Price': price,
            'TargetPrice': info.get('targetMeanPrice', 0),
            'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
            'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
            'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
            'Name': info.get('shortName', ticker)
        }
        # [복구] 주가 그래프용 데이터
        history = stock.history(period="1y")
        return data, history
    except:
        return None, None

# =========================================================
# 3. 메인 내비게이션
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

# [해결] ValueError 방지: 메뉴 인덱스 정확히 매칭
current_index = 0
try:
    current_index = menu_list.index(st.session_state['nav_choice'])
except ValueError:
    current_index = 0

choice = st.radio("메뉴", menu_list, index=current_index, horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = choice

sp500_df = get_sp500_data()
sector_map = get_sector_map()
st.markdown("---")

# --- [1] 종목 진단 (그래프 및 한글/영어 검색 복구) ---
if choice == "🔍 종목 진단":
    ticker_to_search = st.session_state['search_ticker']
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_text = st.text_input("종목명(애플), 영어(Apple), 티커(AAPL) 입력", value=ticker_to_search, placeholder="예: 애플, 테슬라, NVDA", label_visibility="collapsed")
        with c2:
            search_btn = st.form_submit_button("🔍 계산하기")

    if (search_btn and input_text) or (ticker_to_search and input_text):
        if ticker_to_search: st.session_state['search_ticker'] = ""
        ticker = find_ticker(input_text, sp500_df)
        with st.spinner(f"🇺🇸 {ticker} 데이터 분석 중..."):
            data, history = get_stock_info(ticker)
            if data:
                # [해결] DeltaGenerator 에러 방지용 if-else 정석 구현
                score = 0
                if data['ROE'] >= 15: score += 50
                if 0 < data['PBR'] <= 2.0: score += 30
                if 0 < data['PER'] <= 20: score += 20
                
                m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
                
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.subheader("종합 점수")
                    if score >= 60:
                        st.success(f"# 💎 {score}점")
                    else:
                        st.warning(f"# ✋ {score}점")
                    st.metric("안전마진", f"{m_rate:.1f}%", delta=f"{m_rate:.1f}%")
                with col_b:
                    st.subheader(f"{data['Name']} ({ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${data['Price']}")
                    m2.metric("ROE", f"{data['ROE']}%")
                    m3.metric("PER", f"{data['PER']}배")
                    m4.metric("PBR", f"{data['PBR']}배")
                
                # [복구] 그래프 노출
                if history is not None and not history.empty:
                    st.subheader("📈 1년 주가 흐름")
                    st.line_chart(history['Close'], color="#004e92")
            else:
                st.error("데이터 수집 실패. 잠시 후 다시 시도하세요. (야후 서버 지연)")

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
                status.text(f"🔍 {row.Symbol} 채점 중... ({i+1}/{len(targets)})")
                time.sleep(0.5) # [해결] 야후 차단 방지
                d, _ = get_stock_info(row.Symbol)
                if d:
                    s = 0
                    if d['ROE'] >= 15: s += 50
                    if 0 < d['PBR'] <= 2.0: s += 30
                    if 0 < d['PER'] <= 20: s += 20
                    m_t = f"{((d['TargetPrice']-d['Price'])/d['Price']*100):.1f}%" if d['TargetPrice']>0 else "-"
                    results.append({'순위': 0, '티커': row.Symbol, '종목명': d['Name'], '점수': s, '안전마진': m_t, '현재가': f"${d['Price']}"})
                bar.progress((i+1)/len(targets))
            
            status.empty()
            if results:
                # [해결] 점수 순 표 출력
                final_df = pd.DataFrame(results).sort_values('점수', ascending=False).head(5)
                final_df['순위'] = range(1, len(final_df) + 1)
                st.success("✅ 분석 완료!")
                st.table(final_df.set_index('순위'))
                
                # 상세 진단 버튼
                cols = st.columns(5)
                for idx, row in enumerate(final_df.to_dict('records')):
                    if cols[idx].button(f"{row['티커']} 진단", key=f"btn_{row['티커']}"):
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
    tab1, tab2 = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with tab1:
        my_link = "https://buymeacoffee.com/jh.choi" 
        st.markdown(f'<a href="{my_link}" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with tab2:
        qr_file = "kakao_qr.png.jpg"
        if os.path.exists(qr_file): # [해결] os 모듈 에러 수정
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최*환") # [요청] 마스킹 완료
    st.markdown("---")
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
