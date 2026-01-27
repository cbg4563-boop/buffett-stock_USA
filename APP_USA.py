import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import time
import os

# =========================================================
# 1. 페이지 설정
# =========================================================
st.set_page_config(page_title="워렌 버핏 주식매매 기준준 계산기", page_icon="🗽", layout="wide")

# 스타일 설정
st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] > div:has(input[type="radio"]) {
        background-color: #f8f9fb; padding: 15px; border-radius: 15px; border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# 메뉴 및 세션 상태 초기화
menu_list = ["🔍 종목 진단", "📋 S&P 500 리스트", "🏆 분야별 TOP 5 랭킹"]
if 'nav_choice' not in st.session_state: st.session_state['nav_choice'] = menu_list[0]
if 'search_ticker' not in st.session_state: st.session_state['search_ticker'] = ""

# =========================================================
# 2. 데이터 처리 및 초정밀 검색 로직
# =========================================================

@st.cache_data(ttl=86400)
def get_sp500_data():
    try:
        df = fdr.StockListing('S&P500')
        return df[['Symbol', 'Name', 'Sector']]
    except:
        return None

def get_sector_map():
    return {
        'Energy': '에너지', 'Materials': '소재/화학', 'Industrials': '산업재',
        'Consumer Discretionary': '경기소비재', 'Consumer Staples': '필수소비재',
        'Health Care': '헬스케어', 'Financials': '금융',
        'Information Technology': 'IT/기술', 'Communication Services': '통신서비스',
        'Utilities': '유틸리티', 'Real Estate': '부동산'
    }

def find_ticker_smart(user_input, df_sp500):
    """
    [핵심 수정] 팔란티어 등 한국인이 자주 찾는 종목 대거 추가
    """
    user_input = user_input.strip()
    if not user_input: return ""
    
    # 1. 한글 별칭 확인 (여기에 팔란티어 추가함)
    k_map = {
        '애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '마이크로소프트': 'MSFT',
        '엔비디아': 'NVDA', '아마존': 'AMZN', '구글': 'GOOGL', '알파벳': 'GOOGL',
        '메타': 'META', '페이스북': 'META', '넷플릭스': 'NFLX', 
        '팔란티어': 'PLTR', '팔랜티어': 'PLTR', # [추가] 사장님 요청
        '아이온큐': 'IONQ', '유니티': 'U', '로블록스': 'RBLX', '코인베이스': 'COIN',
        '스타벅스': 'SBUX', '코카콜라': 'KO', '펩시': 'PEP', '코스트코': 'COST',
        '맥도날드': 'MCD', '디즈니': 'DIS', '나이키': 'NKE',
        '에이엠디': 'AMD', '암드': 'AMD', '인텔': 'INTC', '퀄컴': 'QCOM',
        '마이크론': 'MU', '브로드컴': 'AVGO', '어도비': 'ADBE',
        '버크셔': 'BRK-B', '제이피모건': 'JPM', '비자': 'V', '마스터카드': 'MA',
        '존슨앤존슨': 'JNJ', '일라이릴리': 'LLY', '화이자': 'PFE'
    }
    
    if user_input in k_map: return k_map[user_input]
    
    if df_sp500 is not None:
        input_lower = user_input.lower()
        
        # 2. 티커(Symbol) 직접 검색
        symbol_match = df_sp500[df_sp500['Symbol'].str.lower() == input_lower]
        if not symbol_match.empty:
            return symbol_match.iloc[0]['Symbol']
            
        # 3. 회사 이름(Name) 정밀 검색 (복붙 대응)
        name_match = df_sp500[df_sp500['Name'].str.lower() == input_lower]
        if not name_match.empty:
            return name_match.iloc[0]['Symbol']
            
        # 4. 이름 포함 검색
        contains_match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False, regex=False)]
        if not contains_match.empty:
            return contains_match.iloc[0]['Symbol']

    # 못 찾으면 입력값 그대로 반환
    return user_input.upper()

def get_stock_data(ticker):
    # 재시도 로직
    for i in range(2):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            if price and price > 0:
                data = {
                    'Price': price,
                    'TargetPrice': info.get('targetMeanPrice', 0),
                    'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
                    'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
                    'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
                    'Name': info.get('shortName', ticker)
                }
                history = stock.history(period="1y")
                return data, history
            time.sleep(0.5)
        except:
            time.sleep(0.5)
            continue
    return None, None

def calculate_score(data):
    score = 0
    if data['ROE'] >= 15: score += 50
    if 0 < data['PBR'] <= 2.0: score += 30 
    if 0 < data['PER'] <= 20: score += 20
    
    margin = 0
    if data['TargetPrice'] > 0:
        margin = ((data['TargetPrice'] - data['Price']) / data['Price']) * 100
    return score, f"{margin:.1f}%"

# =========================================================
# 3. 메인 화면 로직
# =========================================================
st.title("🗽 워렌 버핏 주식매매 기준 계산기")
st.markdown("### 💡 복잡한 분석은 끝! 종목만 넣으면 점수가 나옵니다.")
st.markdown("#### 💡 S&P500에 있는 기업들만 검색 가능해요")
st.warning("⚠️ 투자 참고용이며, 모든 책임은 본인에게 있습니다.")

try:
    current_idx = menu_list.index(st.session_state['nav_choice'])
except:
    current_idx = 0

choice = st.radio("메뉴", menu_list, index=current_idx, horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = choice

sp500_df = get_sp500_data()
sector_map = get_sector_map()
st.markdown("---")

# ---------------------------------------------------------
# [탭 1] 종목 진단 (팔란티어 해결)
# ---------------------------------------------------------
if choice == "🔍 종목 진단":
    default_val = st.session_state['search_ticker']
    
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_txt = st.text_input("기업명(한글/영어) 또는 티커 입력", value=default_val, placeholder="예: 팔란티어, AAPL, Avery Dennison")
        with c2:
            search_btn = st.form_submit_button("🔍 진단")
            
    if (search_btn and input_txt) or (default_val and input_txt):
        if default_val: st.session_state['search_ticker'] = ""
        
        # [수정] 팔란티어 -> PLTR 변환 성공
        target_ticker = find_ticker_smart(input_txt, sp500_df)
        
        with st.spinner(f"🇺🇸 '{input_txt}' -> '{target_ticker}' 분석 중..."):
            d, history = get_stock_data(target_ticker)
            
            if d:
                score, m_text = calculate_score(d)
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.subheader("종합 점수")
                    if score >= 80: st.success(f"💎 {score}점")
                    elif score >= 50: st.info(f"🙂 {score}점")
                    else: st.warning(f"🤔 {score}점")
                    st.metric("안전마진", m_text)
                with col2:
                    st.subheader(f"{d['Name']} ({target_ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${d['Price']}")
                    m2.metric("ROE", f"{d['ROE']}%")
                    m3.metric("PER", f"{d['PER']}배")
                    m4.metric("PBR", f"{d['PBR']}배")
                
                if history is not None and not history.empty:
                    st.subheader("📈 주가 흐름")
                    st.line_chart(history['Close'], color="#004e92")
            else:
                st.error(f"데이터를 찾을 수 없습니다. (입력값: {input_txt} -> 변환시도: {target_ticker})")
                st.caption("※ 정확한 티커(예: PLTR)를 입력하거나, 유명한 한글 종목명인지 확인해주세요.")

# ---------------------------------------------------------
# [탭 2] S&P 500 리스트
# ---------------------------------------------------------
elif choice == "📋 S&P 500 리스트":
    st.subheader("📋 S&P 500 전체 종목")
    if sp500_df is not None:
        display_df = sp500_df.rename(columns={'Symbol': '티커', 'Name': '종목명', 'Sector': '업종'})
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# [탭 3] 분야별 TOP 5
# ---------------------------------------------------------
elif choice == "🏆 분야별 TOP 5 랭킹":
    st.subheader("🏆 분야별 저평가 우량주 TOP 5")
    
    if sp500_df is not None:
        sectors = sorted(sp500_df['Sector'].unique())
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        
        selected_option = st.selectbox("분석할 업종을 선택하세요", sector_options)
        pure_sector = selected_option.split(' (')[0]
        
        if st.button(f"🚀 {pure_sector} 전 종목 분석 시작"):
            targets = sp500_df[sp500_df['Sector'] == pure_sector]
            total = len(targets)
            
            results = []
            p_bar = st.progress(0)
            status = st.empty()
            
            for i, row in enumerate(targets.itertuples()):
                ticker = row.Symbol
                name_in_list = row.Name 
                
                status.text(f"🔍 ({i+1}/{total}) {name_in_list} 분석 중...")
                
                d, _ = get_stock_data(ticker)
                if d:
                    s, m_t = calculate_score(d)
                    results.append({
                        '티커': ticker,
                        '종목명': name_in_list,
                        '점수': s,
                        '안전마진': m_t,
                        '현재가': f"${d['Price']}",
                        'ROE': f"{d['ROE']}%"
                    })
                p_bar.progress((i+1)/total)
                time.sleep(0.1)
            
            p_bar.empty()
            status.empty()
            
            if results:
                df_res = pd.DataFrame(results).sort_values('점수', ascending=False).head(5)
                df_res.reset_index(drop=True, inplace=True)
                df_res.index = df_res.index + 1
                st.success(f"✅ 분석 완료!")
                st.table(df_res)
            else:
                st.warning("데이터 수집 실패")

# =========================================================
# 4. 사이드바
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    t1, t2 = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with t1:
        st.markdown('<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with t2:
        if os.path.exists("kakao_qr.png.jpg"):
            st.image("kakao_qr.png.jpg", use_container_width=True)
            st.caption("예금주: 최*환")
            
    st.markdown("---")
    st.info("📚 **워렌 버핏 투자법 완벽 가이드**")
    st.markdown("[👉 **'워렌 버핏 바이블' 최저가 보기**](https://link.coupang.com/a/dz5HhD)")


