import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os
import time

# =========================================================
# 1. 페이지 설정 및 내비게이션 상태 초기화
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

# [핵심] 탭 이동과 검색어를 제어하기 위한 세션 상태
if 'nav_choice' not in st.session_state:
    st.session_state['nav_choice'] = "🔍 종목 진단"
if 'search_ticker' not in st.session_state:
    st.session_state['search_ticker'] = ""

st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    /* 내비게이션 메뉴 스타일 */
    div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] > div:has(input[type="radio"]) {
        background-color: #f8f9fb; padding: 15px; border-radius: 15px; border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 필수 데이터 및 로직 (동일)
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

def find_ticker(user_input, df_sp500):
    user_input = user_input.strip()
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
    if roe >= 15: score += 50; report.append("✅ [수익성] ROE 15% 이상")
    if 0 < pbr <= 2.0: score += 20; report.append("✅ [자산] PBR 2배 이하")
    if 0 < per <= 20: score += 20; report.append("✅ [밸류] PER 20배 이하")
    if div >= 1.0: score += 10; report.append("✅ [배당] 1% 이상")
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, report, f"{m_rate:.1f}%", m_rate

# =========================================================
# 3. 메인 메뉴 (라디오 버튼 내비게이션)
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

# 세션 상태에 따라 현재 메뉴 인덱스 결정
menu_list = ["🔍 종목 진단", "📋 S&P 500 리스트", "💎 업종별 보물찾기"]
current_idx = menu_list.index(st.session_state['nav_choice'])

choice = st.radio("메뉴", menu_list, index=current_idx, horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = choice # 메뉴 변경 시 저장

st.markdown("---")

# =========================================================
# 4. 기능별 페이지 구성
# =========================================================

# --- [1] 종목 진단 ---
if choice == "🔍 종목 진단":
    # 랭킹에서 넘어온 종목 확인
    ticker_to_search = st.session_state['search_ticker']
    
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_text = st.text_input("종목 입력", value=ticker_to_search, placeholder="예: Apple, 테슬라", label_visibility="collapsed")
        with c2:
            search_btn = st.form_submit_button("🔍 계산하기")

    # 버튼 클릭 혹은 자동 진단 시 실행
    if (search_btn and input_text) or (ticker_to_search and input_text):
        if ticker_to_search:
            st.session_state['search_ticker'] = "" # 사용 후 초기화
            
        ticker = find_ticker(input_text, get_sp500_data())
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
                st.line_chart(history['Close'], color="#004e92")
                for r in report: st.write(r)
            else: st.error("종목 정보를 가져올 수 없습니다.")

# --- [2] 리스트 ---
elif choice == "📋 S&P 500 리스트":
    st.subheader("📋 S&P 500 종목 현황")
    df = get_sp500_data()
    if df is not None:
        st.dataframe(df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# --- [3] 보물찾기 (수정 완료) ---
elif choice == "💎 업종별 보물찾기":
    st.subheader("💎 업종별 저평가 우량주 발굴")
    
    # [설명 추가] 열 설명 가이드
    with st.expander("ℹ️ 랭킹 항목 설명"):
        st.write("""
        * **티커**: 미국 시장 종목 코드 (예: AAPL)
        * **점수**: ROE, PBR, PER, 배당을 기준으로 매긴 워렌 버핏식 점수 (100점 만점)
        * **현재가**: 실시간 기준 1주당 가격 (USD)
        * **안전마진**: 전문가 목표주가 대비 현재 상승 여력 (데이터 부족 시 '-' 표시)
        """)

    df = get_sp500_data()
    if df is not None:
        sector_map = get_sector_map()
        sectors = sorted(df['Sector'].unique())
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        selected = st.selectbox("업종 선택", sector_options)
        real_sector = selected.split(' (')[0]
        
        if st.button(f"🚀 {real_sector} 분석 시작"):
            targets = df[df['Sector'] == real_sector].head(25)
            results = []
            bar = st.progress(0)
            for i, row in enumerate(targets.itertuples()):
                time.sleep(0.3) # 야후 차단 방지
                d, _ = get_stock_info(row.Symbol)
                if d:
                    s, _, m_text, _ = calculate_us_score(d)
                    results.append({'티커': row.Symbol, '종목명': d['Name'], '점수': s, '현재가': f"${d['Price']}", '안전마진': m_text})
                bar.progress((i+1)/len(targets))
            
            if results:
                df_res = pd.DataFrame(results).sort_values('점수', ascending=False)
                st.success(f"✅ {len(results)}개 종목 분석 완료!")
                
                # 버튼을 포함한 랭킹 리스트 출력
                for row in df_res.head(10).to_dict('records'):
                    with st.container():
                        c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                        c1.write(f"**{row['티커']}**")
                        c2.write(row['종목명'])
                        c3.write(f"**{row['점수']}점**")
                        # [버그 수정] 버튼 클릭 시 세션 상태 업데이트 후 앱 강제 리런
                        if c4.button(f"🔍 진단하기", key=f"rank_{row['티커']}"):
                            st.session_state['search_ticker'] = row['티커'] # 종목명 저장
                            st.session_state['nav_choice'] = "🔍 종목 진단" # 탭 이동
                            st.rerun()
                        st.markdown("---")

# =========================================================
# 5. 수익화 사이드바 (동일)
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    t1, t2 = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with t1:
        my_link = "https://buymeacoffee.com/jh.choi" 
        st.markdown(f'<a href="{my_link}" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with t2:
        qr_file = "kakao_qr.png.jpg"
        if os.path.exists(qr_file):
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최주환")
    st.markdown("---")
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
