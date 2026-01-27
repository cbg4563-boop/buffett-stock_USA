import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import time

# =========================================================
# 1. 페이지 설정
# =========================================================
st.set_page_config(page_title="워렌 버핏의 미국 주식 계산기", page_icon="🗽", layout="wide")

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
    [핵심 수정] 복사 붙여넣기 완벽 대응
    사용자가 입력한 값이 리스트에 있는 이름과 똑같으면 바로 티커를 뱉어냅니다.
    """
    user_input = user_input.strip()
    if not user_input: return ""
    
    # 1. 한글 별칭 확인
    k_map = {'애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '엔비디아': 'NVDA', '아마존': 'AMZN', '구글': 'GOOGL', '메타': 'META'}
    if user_input in k_map: return k_map[user_input]
    
    if df_sp500 is not None:
        # 대소문자 구분 없이 비교하기 위해 입력값을 소문자로 변환
        input_lower = user_input.lower()
        
        # 2. 티커(Symbol) 직접 검색 (예: AVY)
        # Symbol 컬럼에 정확히 일치하는 게 있는지 확인
        symbol_match = df_sp500[df_sp500['Symbol'].str.lower() == input_lower]
        if not symbol_match.empty:
            return symbol_match.iloc[0]['Symbol']
            
        # 3. [이게 중요] 회사 이름(Name) 정밀 검색 (복붙 대응)
        # 사용자가 "Avery Dennison Corporation"을 넣었을 때 정확히 찾기
        name_match = df_sp500[df_sp500['Name'].str.lower() == input_lower]
        if not name_match.empty:
            return name_match.iloc[0]['Symbol']
            
        # 4. 이름에 포함된 경우 (예: "Avery"만 쳐도 찾기)
        # regex=False로 설정해서 특수문자 오류 방지
        contains_match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False, regex=False)]
        if not contains_match.empty:
            return contains_match.iloc[0]['Symbol']

    # 못 찾으면 입력값 그대로 반환 (야후에 맡김)
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
st.title("🗽 워렌 버핏의 미국 주식 계산기")

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
# [탭 1] 종목 진단 (복붙 검색 해결)
# ---------------------------------------------------------
if choice == "🔍 종목 진단":
    default_val = st.session_state['search_ticker']
    
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_txt = st.text_input("기업명(복붙 가능) 또는 티커 입력", value=default_val, placeholder="예: Avery Dennison Corporation, AAPL")
        with c2:
            search_btn = st.form_submit_button("🔍 진단")
            
    if (search_btn and input_txt) or (default_val and input_txt):
        if default_val: st.session_state['search_ticker'] = ""
        
        # [수정된 검색 로직 사용]
        target_ticker = find_ticker_smart(input_txt, sp500_df)
        
        with st.spinner(f"🇺🇸 '{input_txt}' -> '{target_ticker}' 변환 및 분석 중..."):
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
                st.caption("※ 랭킹의 종목명을 정확히 복사했는지 확인해주세요.")

# ---------------------------------------------------------
# [탭 2] S&P 500 리스트
# ---------------------------------------------------------
elif choice == "📋 S&P 500 리스트":
    st.subheader("📋 S&P 500 전체 종목")
    if sp500_df is not None:
        display_df = sp500_df.rename(columns={'Symbol': '티커', 'Name': '종목명', 'Sector': '업종'})
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# [탭 3] 분야별 TOP 5 (한글명 + 전수조사)
# ---------------------------------------------------------
elif choice == "🏆 분야별 TOP 5 랭킹":
    st.subheader("🏆 분야별 저평가 우량주 TOP 5")
    
    if sp500_df is not None:
        sectors = sorted(sp500_df['Sector'].unique())
        # 한글 매핑 적용
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        
        selected_option = st.selectbox("분석할 업종을 선택하세요", sector_options)
        pure_sector = selected_option.split(' (')[0]
        
        if st.button(f"🚀 {pure_sector} 전 종목 분석 시작"):
            # 해당 업종 전 종목 가져오기
            targets = sp500_df[sp500_df['Sector'] == pure_sector]
            total = len(targets)
            
            results = []
            p_bar = st.progress(0)
            status = st.empty()
            
            for i, row in enumerate(targets.itertuples()):
                # S&P500 리스트에 있는 '정확한 이름'을 사용
                ticker = row.Symbol
                name_in_list = row.Name 
                
                status.text(f"🔍 ({i+1}/{total}) {name_in_list} 분석 중...")
                
                d, _ = get_stock_data(ticker)
                if d:
                    s, m_t = calculate_score(d)
                    results.append({
                        '티커': ticker,
                        '종목명': name_in_list, # 리스트에 있는 이름 그대로 사용 (복붙 검색 용이)
                        '점수': s,
                        '안전마진': m_t,
                        '현재가': f"${d['Price']}",
                        'ROE': f"{d['ROE']}%"
                    })
                p_bar.progress((i+1)/total)
                time.sleep(0.1) # 속도 조절
            
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
        import os
        if os.path.exists("kakao_qr.png.jpg"):
            st.image("kakao_qr.png.jpg", use_container_width=True)
            st.caption("예금주: 최*환")
            
    st.markdown("---")
    st.info("📚 **워렌 버핏 투자법 완벽 가이드**")
    st.markdown("[👉 **'워렌 버핏 바이블' 최저가 보기**](https://link.coupang.com/a/dz5HhD)")
