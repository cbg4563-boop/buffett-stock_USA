import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr

# --- 페이지 설정 ---
st.set_page_config(
    page_title="천조국 버핏 채점표 (US Edition)",
    page_icon="🗽",
    layout="wide"
)

# --- 스타일 ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 🔍 데이터 및 한글 매핑 설정
# ---------------------------------------------------------

# 한국인이 좋아하는 주식 별명 사전
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

# 야후 파이낸스 데이터 가져오기
def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'regularMarketPrice' not in info and 'currentPrice' not in info:
            return None

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
        return data
    except:
        return None

# S&P 500 리스트 (랭킹용)
@st.cache_data(ttl=86400)
def get_sp500_list():
    try:
        return fdr.StockListing('S&P500')
    except:
        return None

# ---------------------------------------------------------
# 2. 📊 미국 시장 맞춤형 채점 로직
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
# 3. 🖥️ 메인 화면
# ---------------------------------------------------------

st.title("🗽 천조국 주식 채점표 (US Stocks)")
st.caption("Data: Yahoo Finance | 기준: US Market Standard")

st.warning("⚠️ **[면책 조항]** 본 서비스는 투자 참고용이며, 데이터 오류가 있을 수 있습니다. 모든 투자의 책임은 본인에게 있습니다.")

sp500_df = get_sp500_list()
korean_map = get_korean_name_map()

tab1, tab2, tab3 = st.tabs(["🔍 종목 검색", "🏆 S&P 500 리스트", "🚀 대장주 Top 5"])

# --- 탭 1: 검색 ---
with tab1:
    st.subheader("종목 정밀 진단")
    st.write("티커(AAPL) 또는 한글 별명(애플, 슈드, 반도체 등)으로 검색하세요.")
    
    search_input = st.text_input("종목 입력", placeholder="예: TSLA, 엔비디아, 코카콜라").upper()
    
    if search_input:
        target_ticker = search_input
        for ticker, keywords in korean_map.items():
            if search_input in keywords or search_input == ticker:
                target_ticker = ticker
                break
        
        if st.button("진단하기 (Analyze)"):
            with st.spinner(f"🇺🇸 Wall Street 접속 중... ({target_ticker})"):
                data = get_stock_info(target_ticker)
            
            if data:
                score, report = calculate_us_score(data)
                
                if score >= 80: verdict = "💎 Strong Buy (강력 매수)"; color = "green"
                elif score >= 60: verdict = "🥇 Buy (매수 추천)"; color = "blue"
                elif score >= 40: verdict = "✋ Hold (관망)"; color = "orange"
                else: verdict = "🧱 Sell / Avoid (주의)"; color = "gray"
                
                st.divider()
                
                c1, c2 = st.columns([1.5, 2.5])
                with c1:
                    st.metric("버핏 점수", f"{score}점")
                    if color == "green": st.success(verdict)
                    elif color == "blue": st.info(verdict)
                    elif color == "orange": st.warning(verdict)
                    else: st.error(verdict)
                
                with c2:
                    cc1, cc2 = st.columns(2)
                    cc1.metric("현재가", f"${data['Price']:,.2f}")
                    cc1.metric("ROE", f"{data['ROE']}%")
                    cc2.metric("PER", f"{data['PER']}배")
                    cc2.metric("PBR", f"{data['PBR']}배")
                    st.caption(f"배당수익률: {data['DIV']}%")
                
                st.write("---")
                if report:
                    for r in report: st.write(r)
                else:
                    st.info("특이사항 없음 (성장주거나 고평가 구간)")
            else:
                st.error(f"'{target_ticker}' 종목을 찾을 수 없습니다.")

# --- 탭 2: 리스트 ---
with tab2:
    st.subheader("S&P 500 종목 리스트")
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True)
    else:
        st.error("리스트 로딩 실패")

# --- 탭 3: 스캔 ---
with tab3:
    st.subheader("🇺🇸 S&P 500 대장주 Top 5 발굴")
    if st.button("🚀 스캔 시작"):
        if sp500_df is not None:
            targets = sp500_df['Symbol'].head(20).tolist()
            results = []
            bar = st.progress(0)
            
            for i, t in enumerate(targets):
                d = get_stock_info(t)
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
                st.success("✅ 분석 완료!")
                st.dataframe(df_res, use_container_width=True)
        else:
            st.error("데이터 로딩 실패")
