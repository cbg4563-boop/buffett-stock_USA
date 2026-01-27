import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import time

# =========================================================
# 1. 페이지 설정 및 세션 상태 초기화
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

# [핵심] 다른 탭에서 종목을 클릭했을 때, 검색창에 자동 입력하기 위한 변수 설정
if 'target_ticker' not in st.session_state:
    st.session_state['target_ticker'] = ""

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
    
    /* 랭킹 리스트의 버튼 스타일 */
    div.stButton > button:first-child {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 데이터 처리 & 번역 & 검색 로직
# =========================================================
@st.cache_data(ttl=86400)
def get_sp500_data():
    try:
        df = fdr.StockListing('S&P500')
        return df
    except:
        return None

# [핵심] 업종 한글 번역 맵핑
def get_sector_map():
    return {
        'Energy': '에너지',
        'Materials': '소재/화학',
        'Industrials': '산업재 (기계/항공)',
        'Consumer Discretionary': '경기소비재 (자동차/유통)',
        'Consumer Staples': '필수소비재 (음식료/생필품)',
        'Health Care': '헬스케어 (제약/바이오)',
        'Financials': '금융 (은행/보험)',
        'Information Technology': 'IT/기술 (반도체/SW)',
        'Communication Services': '통신서비스 (미디어/인터넷)',
        'Utilities': '유틸리티 (전력/가스)',
        'Real Estate': '부동산 (리츠)'
    }

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
            'MarketCap': info.get('marketCap', 0)
        }
        history = stock.history(period="1y")
        return data, history
    except:
        return None, None

# =========================================================
# 3. 채점 로직
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
sector_map = get_sector_map()

tab1, tab2, tab3 = st.tabs(["🔍 종목 진단", "📋 S&P 500 리스트", "💎 업종별 보물찾기"])

# --- [탭 1] 종목 진단 (자동 실행 기능 추가) ---
with tab1:
    # 세션 상태에 저장된 종목이 있으면 그걸 기본값으로 사용
    default_ticker = st.session_state.get('target_ticker', '')
    
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_text = st.text_input("종목 검색", value=default_ticker, placeholder="예: Apple, 테슬라", label_visibility="collapsed")
        with c2:
            search_btn = st.form_submit_button("🔍 계산")

    # 버튼을 누르거나, 다른 탭에서 종목을 보내왔을 때(default_ticker가 있을 때) 실행
    if (search_btn and input_text) or (default_ticker and input_text):
        ticker = find_ticker(input_text, sp500_df)
        
        # 중복 실행 방지 및 사용자 알림
        if default_ticker:
            st.info(f"🚀 '{default_ticker}' 종목을 자동으로 불러왔습니다.")
            st.session_state['target_ticker'] = "" # 한번 썼으면 초기화 (새로고침 시 무한루프 방지)

        with st.spinner(f"🇺🇸 '{ticker}' 정밀 분석 중..."):
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
        # 데이터프레임 보여줄 때도 한글 업종명 추가해서 보여주기
        show_df = sp500_df[['Symbol', 'Name', 'Sector']].copy()
        show_df['Sector_KR'] = show_df['Sector'].map(sector_map).fillna(show_df['Sector'])
        st.dataframe(show_df, use_container_width=True, hide_index=True)

# --- [탭 3] 업종별 보물찾기 (한글 표시 + 클릭 시 이동) ---
with tab3:
    st.subheader("💎 숨겨진 '100점' 주식 찾기")
    st.markdown("원하는 업종을 고르면, 계산기가 실시간으로 채점하여 **1등**을 찾아줍니다.")
    
    if sp500_df is not None:
        # [핵심] 1. 한글이 포함된 업종 리스트 만들기
        sectors_raw = sorted(sp500_df['Sector'].unique())
        # "Energy (에너지)" 형태로 변환
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors_raw]
        
        selected_option = st.selectbox("탐색할 업종을 선택하세요:", sector_options)
        
        # "Energy (에너지)" -> "Energy"만 추출해서 검색에 사용
        real_sector = selected_option.split(' (')[0]
        
        if st.button(f"🚀 '{real_sector}' 분야 채점 시작"):
            targets = sp500_df[sp500_df['Sector'] == real_sector]
            
            if len(targets) > 50:
                st.info(f"💡 종목이 많아 시가총액 상위 50개만 우선 분석합니다. (총 {len(targets)}개)")
                targets = targets.head(50)
            
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total = len(targets)
            for i, row in enumerate(targets.itertuples()):
                ticker = row.Symbol
                d, _ = get_stock_info(ticker)
                
                if d:
                    s, _, m_text, _ = calculate_us_score(d)
                    results.append({
                        '티커': ticker,
                        '종목명': d['Name'],
                        '점수': s,
                        '현재가': f"${d['Price']:,.2f}",
                        '안전마진': m_text,
                        'ROE': f"{d['ROE']}%"
                    })
                
                progress_bar.progress((i + 1) / total)
                status_text.text(f"🔍 {ticker} 채점 중... ({i+1}/{total})")
            
            progress_bar.empty()
            status_text.empty()
            
            if results:
                # 점수순 정렬
                df_res = pd.DataFrame(results).sort_values(by='점수', ascending=False)
                
                st.balloons()
                st.success(f"✅ 분석 완료! **'{real_sector}'** 분야 순위입니다.")
                
                # [핵심] 2. 결과를 단순 표가 아니라 '버튼이 있는 리스트'로 출력
                st.markdown("### 📊 랭킹 Top 10 (버튼을 누르면 상세 진단)")
                
                # 헤더 출력
                h1, h2, h3, h4, h5 = st.columns([1, 2, 2, 2, 2])
                h1.markdown("**순위**")
                h2.markdown("**종목**")
                h3.markdown("**점수**")
                h4.markdown("**현재가**")
                h5.markdown("**상세보기**")
                st.markdown("---")

                # 상위 10개만 루프 돌며 출력
                for idx, row in enumerate(df_res.head(10).to_dict('records')):
                    c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 2])
                    
                    with c1: st.write(f"**{idx+1}위**")
                    with c2: st.write(f"**{row['티커']}**")
                    with c3: 
                        if row['점수'] >= 80: st.success(f"{row['점수']}점")
                        elif row['점수'] >= 60: st.info(f"{row['점수']}점")
                        else: st.write(f"{row['점수']}점")
                    with c4: st.write(row['현재가'])
                    
                    # [핵심] 3. 상세보기 버튼 구현
                    with c5:
                        if st.button(f"🔍 진단하기", key=f"btn_{row['티커']}"):
                            # 버튼 누르면 세션 상태에 저장하고 앱 리로드
                            st.session_state['target_ticker'] = row['티커']
                            st.rerun() 
                            # 리로드되면 -> Tab 1 코드가 실행되면서 -> target_ticker를 감지하고 -> 자동 분석 시작
            else:
                st.error("데이터 로딩 실패")

# =========================================================
# 5. 수익화 사이드바 (최종 수정 완료)
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
        if os.path.exists(qr_file): # NameError 해결
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최주환")
        else:
            st.error("QR 이미지가 없습니다.")
    st.markdown("---")
    # 문구 수정 완료
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")

