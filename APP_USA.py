# --- 스타일 (커스텀 CSS) ---
st.markdown("""
<style>
    /* 메트릭 카드 꾸미기 */
    div[data-testid="stMetric"] {
        background-color: #f9f9f9;
        border: 1px solid #e6e6e6;
        padding: 15px;
        border-radius: 10px;
        color: #333;
    }
    /* 탭 폰트 사이즈 키우기 */
    button[data-baseweb="tab"] {
        font-size: 18px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 🔍 데이터 및 한글 매핑
# ---------------------------------------------------------
@st.cache_data(ttl=86400)
def get_korean_name_map():
    return {
        'AAPL': '애플', 'MSFT': '마이크로소프트 마소', 'GOOGL': '구글 알파벳', 'AMZN': '아마존',
        'TSLA': '테슬라', 'NVDA': '엔비디아', 'META': '메타 페이스북', 'NFLX': '넷플릭스',
        'AMD': 'AMD 암드', 'INTC': '인텔', 'QCOM': '퀄컴', 'AVGO': '브로드컴', 'ARM': '암 ARM',
        'TXN': '텍사스', 'MU': '마이크론', 'KO': '코카콜라', 'PEP': '펩시',
        'SBUX': '스타벅스', 'MCD': '맥도날드', 'DIS': '디즈니', 'NKE': '나이키',
        'JNJ': '존슨앤존슨', 'PFE': '화이자', 'MRK': '머크', 'LLY': '일라이릴리',
        'WMT': '월마트', 'COST': '코스트코', 'TGT': '타겟', 'HD': '홈디포',
        'JPM': 'JP모건', 'BAC': '뱅크오브아메리카', 'V': '비자', 'MA': '마스터카드',
        'BRK.B': '버크셔해서웨이', 'O': '리얼티인컴 월배당', 'AMT': '아메리칸타워',
        'PLTR': '팔란티어', 'IONQ': '아이온큐', 'RIVN': '리비안', 'LCID': '루시드',
        'TSM': 'TSMC', 'ASML': 'ASML', 'GME': '게임스탑', 'AMC': 'AMC',
        'SOXL': '반도체 3배(SOXL)', 'TQQQ': '나스닥 3배(TQQQ)', 'JEPI': 'JEPI 제피',
        'SCHD': '슈드 SCHD', 'SPY': 'S&P500(SPY)', 'QQQ': '나스닥(QQQ)', 'VOO': 'S&P500(VOO)'
    }

def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'regularMarketPrice' not in info and 'currentPrice' not in info:
            return None, None

        price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        roe = info.get('returnOnEquity', 0)
        per = info.get('trailingPE', 0)
        pbr = info.get('priceToBook', 0)
        div = info.get('dividendYield', 0)
        
        data = {
            'Price': price,
            'ROE': round(roe * 100, 2) if roe else 0,
            'PER': round(per, 2) if per else 0,
            'PBR': round(pbr, 2) if pbr else 0,
            'DIV': round(div * 100, 2) if div else 0,
            'Name': info.get('shortName', ticker),
            'Industry': info.get('industry', 'ETF/Others')
        }
        
        # 1년치 주가 차트 데이터
        history = stock.history(period="1y")
        
        return data, history
    except:
        return None, None

@st.cache_data(ttl=86400)
def get_sp500_list():
    try:
        return fdr.StockListing('S&P500')
    except:
        return None

# ---------------------------------------------------------
# 2. 📊 채점 로직
# ---------------------------------------------------------
def calculate_us_score(data):
    score = 0
    report = []
    
    roe = data['ROE']
    per = data['PER']
    pbr = data['PBR']
    div = data['DIV']
    
    if roe >= 20: score += 50; report.append("✅ [수익성] ROE 20% 이상 (괴물급)")
    elif roe >= 15: score += 30; report.append("✅ [수익성] ROE 15% 이상 (우수)")
    elif roe >= 10: score += 10;
    
    if 0 < pbr <= 1.5: score += 20; report.append("✅ [자산] PBR 1.5배 이하 (저평가)")
    elif 0 < pbr <= 4.0: score += 10;
    
    if 0 < per <= 15: score += 20; report.append("✅ [밸류] PER 15배 이하 (저평가)")
    elif 0 < per <= 25: score += 10;
    
    if div >= 1.5: score += 10; report.append("✅ [배당] 1.5% 이상")
    
    return score, report

# ---------------------------------------------------------
# 3. 🖥️ 메인 화면 구성 (이미지 내용 반영)
# ---------------------------------------------------------

# 1. 메인 타이틀
st.title("🗽 워렌 버핏의 미국 주식 채점표 (US Edition)")

# 2. 사이트 소개 (이미지 텍스트 그대로)
st.markdown("### 💡 이 사이트는 무엇인가요?")
st.write("""
워렌 버핏(Warren Buffett)의 투자 철학을 기반으로 미국 주식(S&P 500, 나스닥)의 적정 주가를 분석해주는 계산기입니다. 
애플(AAPL), 테슬라(TSLA), 엔비디아(NVDA) 등 전 종목의 PER, ROE, PBR을 실시간으로 진단하여 매수/매도 타이밍을 점수로 알려드립니다.
""")

st.write(" ") # 공백

# 3. 서브 타이틀 & 캡션
st.header("🗽 미국주식 워렌버핏식 계산기 (US Stocks)")
st.caption("Data: Yahoo Finance | 기준: US Market Standard")

# 4. 경고 문구 (노란 박스)
st.warning("⚠️ **[면책 조항]** 본 서비스는 투자 참고용이며, 데이터 오류가 있을 수 있습니다. 모든 투자의 책임은 본인에게 있습니다.")

st.write("---")

sp500_df = get_sp500_list()
korean_map = get_korean_name_map()

# 5. 탭 구성 (이름 수정)
tab1, tab2, tab3 = st.tabs(["🔍 종목 진단", "🏆 S&P 500 리스트", "🚀 저평가 기업 Top 5"])

# --- 탭 1: 검색 ---
with tab1:
    st.subheader("종목 진단")
    st.write("티커(AAPL) 또는 한글 별명(애플, 슈드, 반도체 등)으로 검색하세요.")
    
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_input = st.text_input("종목 검색", placeholder="예: TSLA, 엔비디아, 코카콜라", label_visibility="collapsed").upper()
    with col_btn:
        st.write("") 

    if search_input:
        target_ticker = search_input
        for ticker, keywords in korean_map.items():
            if search_input in keywords or search_input == ticker:
                target_ticker = ticker
                break
        
        with st.spinner(f"🇺🇸 {target_ticker} 데이터 분석 중..."):
            data, history = get_stock_info(target_ticker)
            
        if data:
            score, report = calculate_us_score(data)
            
            # 1. 점수판 영역
            st.divider()
            c1, c2 = st.columns([1, 2])
            
            with c1:
                st.subheader("버핏 점수")
                if score >= 80: 
                    st.success(f"# 💎 {score}점\n**강력 매수 (Strong Buy)**")
                elif score >= 60: 
                    st.info(f"# 🥇 {score}점\n**매수 추천 (Buy)**")
                elif score >= 40: 
                    st.warning(f"# ✋ {score}점\n**관망 (Hold)**")
                else: 
                    st.error(f"# 🧱 {score}점\n**주의 (Avoid)**")

            with c2:
                st.subheader(f"{data['Name']} ({target_ticker})")
                st.write(f"업종: {data['Industry']}")
                
                # 주요 지표 카드형
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("현재가", f"${data['Price']:,.2f}")
                m2.metric("ROE (수익성)", f"{data['ROE']}%", delta_color="normal")
                m3.metric("PER (밸류)", f"{data['PER']}배")
                m4.metric("PBR (자산)", f"{data['PBR']}배")
            
            # 2. 차트 영역
            st.subheader("📉 최근 1년 주가 흐름")
            if history is not None and not history.empty:
                st.line_chart(history['Close'], color="#004e92")
            else:
                st.caption("차트 데이터를 불러올 수 없습니다.")

            # 3. 리포트
            st.subheader("📝 투자 포인트")
            if report:
                for r in report: 
                    st.markdown(f"- {r}")
            else:
                st.info("💡 현재 버핏 기준으로는 저평가 요인이 부족합니다. (성장주이거나 고평가 구간)")

        else:
            st.error(f"'{target_ticker}' 종목을 찾을 수 없습니다.")

# --- 탭 2: 리스트 ---
with tab2:
    st.subheader("S&P 500 종목 리스트")
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)
    else:
        st.error("리스트 로딩 실패")

# --- 탭 3: 스캔 ---
with tab3:
    st.subheader("🇺🇸 저평가 기업 발굴 (S&P 500 Top 5)")
    st.write("S&P 500 상위 20개 대형주를 실시간으로 스캔합니다.")
    
    if st.button("🚀 스캔 시작"):
        if sp500_df is not None:
            targets = sp500_df['Symbol'].head(20).tolist()
            results = []
            bar = st.progress(0)
            
            for i, t in enumerate(targets):
                d, _ = get_stock_info(t)
                if d:
                    s, _ = calculate_us_score(d)
                    results.append({'티커': t, '기업명': d['Name'], '점수': s, 
                                    '현재가': f"${d['Price']:,.2f}", 'ROE': f"{d['ROE']}%", 
                                    'PER': d['PER'], 'PBR': d['PBR']})
                bar.progress((i+1)/len(targets))
            bar.empty()
            
            if results:
                df_res = pd.DataFrame(results).sort_values('점수', ascending=False).head(5)
                df_res.index = range(1, 6)
                st.balloons()
                st.success("✅ 분석 완료! 현재 가장 매력적인 대장주입니다.")
                st.dataframe(df_res, use_container_width=True)
        else:
            st.error("데이터 로딩 실패")
