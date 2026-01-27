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
# 처음 접속할 때만 초기값을 설정합니다.
if 'nav_choice' not in st.session_state:
    st.session_state['nav_choice'] = "🔍 종목 진단"
if 'search_ticker' not in st.session_state:
    st.session_state['search_ticker'] = ""

# CSS 스타일 적용
st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    /* 메뉴 선택 바 스타일 */
    div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] > div:has(input[type="radio"]) {
        background-color: #f8f9fb; padding: 15px; border-radius: 15px; border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 데이터 처리 함수 (S&P 500 리스트 및 종목 정보)
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
        # 회사 이름에 입력어가 포함된 경우 티커 반환
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
    # 버핏식 가치 투자 기준 채점
    if roe >= 15: score += 50; report.append("✅ [수익성] ROE 15% 이상 (우수)")
    if 0 < pbr <= 2.0: score += 20; report.append("✅ [자산] PBR 2배 이하 (저평가)")
    if 0 < per <= 20: score += 20; report.append("✅ [밸류] PER 20배 이하 (적정)")
    if div >= 1.0: score += 10; report.append("✅ [배당] 배당 수익률 1% 이상")
    # 안전마진 계산 (목표가 대비)
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, report, f"{m_rate:.1f}%", m_rate

# =========================================================
# 3. 메인 내비게이션 (라디오 버튼 형태의 탭)
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

menu_list = ["🔍 종목 진단", "📋 S&P 500 리스트", "💎 업종별 보물찾기"]
# 세션 상태에 저장된 메뉴를 선택합니다.
current_selection = st.radio("메뉴", menu_list, index=menu_list.index(st.session_state['nav_choice']), horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = current_selection

st.markdown("---")

# =========================================================
# 4. 기능별 페이지 구현
# =========================================================

# --- [메뉴 1] 종목 진단 ---
if current_selection == "🔍 종목 진단":
    # 다른 탭에서 넘어온 티커가 있는지 확인합니다.
    auto_ticker = st.session_state['search_ticker']
    
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            # 넘어온 티커가 있으면 기본값으로 넣어줍니다.
            search_input = st.text_input("종목 입력", value=auto_ticker, placeholder="예: Apple, 테슬라, NVDA", label_visibility="collapsed")
        with c2:
            submit_btn = st.form_submit_button("🔍 계산하기")

    # 버튼을 눌렀거나, 다른 탭에서 티커를 들고 넘어온 경우 바로 분석 시작
    if submit_btn or (auto_ticker != ""):
        # 분석을 시작하면 세션에 저장된 티커는 비워줍니다 (다음에 또 켜지는 것 방지)
        st.session_state['search_ticker'] = ""
        
        target_ticker = find_ticker(search_input, get_sp500_data())
        with st.spinner(f"🇺🇸 {target_ticker} 분석 중..."):
            data, history = get_stock_info(target_ticker)
            if data:
                score, report, m_text, m_rate = calculate_us_score(data)
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.subheader("종합 점수")
                    if score >= 60: st.success(f"# 💎 {score}점")
                    else: st.warning(f"# ✋ {score}점")
                    st.metric("안전마진 (상승여력)", m_text, delta=f"{m_rate:.1f}%")
                with col_b:
                    st.subheader(f"{data['Name']} ({target_ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${data['Price']}")
                    m2.metric("ROE (수익성)", f"{data['ROE']}%")
                    m3.metric("PER (수익배수)", f"{data['PER']}배")
                    m4.metric("PBR (장부가치)", f"{data['PBR']}배")
                st.line_chart(history['Close'], color="#004e92")
                st.subheader("📝 버핏 리포트")
                for r in report: st.write(r)
            else:
                st.error("데이터를 불러올 수 없습니다. 티커를 다시 확인해 주세요.")

# --- [메뉴 2] 리스트 ---
elif current_selection == "📋 S&P 500 리스트":
    st.subheader("📋 S&P 500 전체 종목")
    df = get_sp500_data()
    if df is not None:
        st.dataframe(df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# --- [메뉴 3] 보물찾기 (강력한 이동 기능 탑재) ---
elif current_selection == "💎 업종별 보물찾기":
    st.subheader("💎 업종별 저평가 우량주 발굴")
    
    # [항목 설명 추가] 사장님이 말씀하신 부족한 설명을 채웠습니다.
    with st.expander("ℹ️ 표 항목 상세 설명 (무엇을 보나요?)"):
        st.write("""
        * **티커(Ticker)**: 미국 시장의 종목 고유 코드입니다.
        * **점수(Score)**: ROE, PER, PBR 등을 종합하여 버핏식으로 계산한 점수입니다 (100점 만점).
        * **현재가(Price)**: 1주당 현재 시장 가격입니다 (달러 기준).
        * **안전마진(Margin)**: 전문가들이 예상한 목표 주가와 현재 주가의 차이입니다. 플러스일수록 저평가 상태입니다.
        """)

    df = get_sp500_data()
    if df is not None:
        sector_map = get_sector_map()
        sectors = sorted(df['Sector'].unique())
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        selected_sector = st.selectbox("업종 선택", sector_options)
        pure_sector_name = selected_sector.split(' (')[0]
        
        if st.button(f"🚀 {pure_sector_name} 종목 전수 채점 시작"):
            # 성능을 위해 해당 업종의 상위 25개 종목을 분석합니다.
            targets = df[df['Sector'] == pure_sector_name].head(25)
            results = []
            bar = st.progress(0)
            
            for i, row in enumerate(targets.itertuples()):
                time.sleep(0.3) # 서버 차단 방지용 미세 대기
                d, _ = get_stock_info(row.Symbol)
                if d:
                    s, _, m_text, _ = calculate_us_score(d)
                    results.append({'티커': row.Symbol, '종목명': d['Name'], '점수': s, '현재가': f"${d['Price']}", '안전마진': m_text})
                bar.progress((i+1)/len(targets))
            
            if results:
                # 점수 높은 순으로 정렬
                df_res = pd.DataFrame(results).sort_values('점수', ascending=False)
                st.success(f"✅ 총 {len(results)}개 종목 분석이 완료되었습니다!")
                
                # 랭킹 리스트 출력
                for row in df_res.head(10).to_dict('records'):
                    with st.container():
                        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
                        col1.write(f"**{row['티커']}**")
                        col2.write(row['종목명'])
                        col3.write(f"**{row['점수']}점**")
                        
                        # [핵심] 진단하기 버튼 클릭 시 로직
                        if col4.button(f"🔍 진단하기", key=f"btn_nav_{row['티커']}"):
                            # 1. 이동할 종목을 저장
                            st.session_state['search_ticker'] = row['티커']
                            # 2. 이동할 메뉴를 선택
                            st.session_state['nav_choice'] = "🔍 종목 진단"
                            # 3. 화면 새로고침 (즉시 이동)
                            st.rerun()
                        st.markdown("---")

# =========================================================
# 5. 수익화 사이드바 (최종 복구)
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
        if os.path.exists(qr_file): #
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최*환")
        else:
            st.error("QR 이미지 파일을 확인해 주세요.")

    st.markdown("---")
    # 사장님이 요청하신 문구 반영
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
