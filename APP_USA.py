import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import time

# =========================================================
# 1. 페이지 및 스타일 설정 (기본 세팅)
# =========================================================
st.set_page_config(page_title="워렌 버핏의 미국 주식 계산기", page_icon="🗽", layout="wide")

# CSS 스타일: 표와 버튼, 메트릭 디자인을 깔끔하게
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
# 2. 데이터 수집 및 스마트 검색 로직 (핵심)
# =========================================================

@st.cache_data(ttl=86400)
def get_sp500_data():
    """S&P 500 종목 리스트를 가져옵니다. 실패 시 None 반환"""
    try:
        df = fdr.StockListing('S&P500')
        # 데이터프레임 컬럼 정리 (Symbol, Name, Sector 필수)
        return df[['Symbol', 'Name', 'Sector']]
    except:
        return None

def get_sector_map():
    """업종 영문 -> 한글 매핑"""
    return {
        'Energy': '에너지', 'Materials': '소재/화학', 'Industrials': '산업재',
        'Consumer Discretionary': '경기소비재', 'Consumer Staples': '필수소비재',
        'Health Care': '헬스케어', 'Financials': '금융',
        'Information Technology': 'IT/기술', 'Communication Services': '통신서비스',
        'Utilities': '유틸리티', 'Real Estate': '부동산'
    }

def find_ticker_smart(user_input, df_sp500):
    """
    [핵심 수정] Avery Dennison Corporation 처럼 긴 이름도 
    S&P 500 리스트에서 검색해서 티커(AVY)를 찾아내는 함수
    """
    user_input = user_input.strip()
    if not user_input: return ""
    
    # 1. 자주 쓰는 한글 별칭 매핑
    k_map = {'애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '엔비디아': 'NVDA', 
             '아마존': 'AMZN', '구글': 'GOOGL', '메타': 'META', '클로락스': 'CLX'}
    if user_input in k_map: return k_map[user_input]
    
    if df_sp500 is not None:
        upper_in = user_input.upper()
        
        # 2. 티커(Symbol)가 정확히 일치하는지 확인 (예: AVY)
        if upper_in in df_sp500['Symbol'].values:
            return upper_in
            
        # 3. 회사 이름(Name)에 검색어가 포함되는지 확인 (대소문자 무시)
        # 예: "Avery"라고 치면 "Avery Dennison Corp"를 찾음
        match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False)]
        
        if not match.empty:
            # 가장 첫 번째로 검색된 종목의 티커를 반환
            found_ticker = match.iloc[0]['Symbol']
            found_name = match.iloc[0]['Name']
            return found_ticker
            
    # 리스트에 없으면 입력한 그대로 반환 (야후가 알아서 찾도록)
    return user_input.upper()

def get_stock_data(ticker):
    """야후 파이낸스에서 데이터 가져오기 (재시도 로직 포함)"""
    for i in range(2): # 최대 2번 시도
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 현재가가 없으면 데이터 없는 것으로 간주
            price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            if price and price > 0:
                data = {
                    'Price': price,
                    'TargetPrice': info.get('targetMeanPrice', 0),
                    'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
                    'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
                    'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
                    'Name': info.get('shortName', ticker) # 종목명
                }
                history = stock.history(period="1y")
                return data, history
            time.sleep(0.5) # 실패 시 잠깐 대기
        except:
            time.sleep(0.5)
            continue
    return None, None

def calculate_score(data):
    """워렌 버핏 점수 계산기"""
    score = 0
    if data['ROE'] >= 15: score += 50
    if 0 < data['PBR'] <= 1.5: score += 30 # 기준 약간 강화
    if 0 < data['PER'] <= 20: score += 20
    
    # 안전마진 (목표가 대비 현재가)
    margin = 0
    if data['TargetPrice'] > 0:
        margin = ((data['TargetPrice'] - data['Price']) / data['Price']) * 100
        
    return score, f"{margin:.1f}%"

# =========================================================
# 3. 메인 내비게이션 및 화면 구성
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

# 메뉴 선택 (오류 방지)
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
# [탭 1] 종목 진단 (Avery Dennison 해결 완료)
# ---------------------------------------------------------
if choice == "🔍 종목 진단":
    # 랭킹 탭에서 넘어온 값이 있으면 입력창에 채움
    default_val = st.session_state['search_ticker']
    
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            input_txt = st.text_input("종목명(영문/한글) 또는 티커", value=default_val, placeholder="예: Avery, 애플, TSLA")
        with c2:
            search_btn = st.form_submit_button("🔍 진단")
            
    # 검색 실행 조건
    if (search_btn and input_txt) or (default_val and input_txt):
        # 검색어 초기화 (다음 검색을 위해)
        if default_val: st.session_state['search_ticker'] = ""
        
        # 1. 스마트 검색으로 티커 찾기
        target_ticker = find_ticker_smart(input_txt, sp500_df)
        
        # 2. 데이터 가져오기
        with st.spinner(f"🇺🇸 {target_ticker} 데이터 분석 중..."):
            d, history = get_stock_data(target_ticker)
            
            if d:
                # 점수 계산
                score, m_text = calculate_score(d)
                
                # 결과 출력
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.subheader("종합 점수")
                    if score >= 80: st.success(f"💎 {score}점 (강력추천)")
                    elif score >= 50: st.info(f"🙂 {score}점 (양호)")
                    else: st.warning(f"🤔 {score}점 (관망)")
                    st.metric("안전마진 (상승여력)", m_text)
                    
                with col2:
                    st.subheader(f"{d['Name']} ({target_ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${d['Price']}")
                    m2.metric("ROE", f"{d['ROE']}%")
                    m3.metric("PER", f"{d['PER']}배")
                    m4.metric("PBR", f"{d['PBR']}배")
                
                # 차트
                if history is not None and not history.empty:
                    st.subheader("📈 최근 1년 주가 흐름")
                    st.line_chart(history['Close'], color="#004e92")
            else:
                st.error(f"'{target_ticker}'에 대한 데이터를 가져오지 못했습니다. 종목명을 다시 확인해주세요.")

# ---------------------------------------------------------
# [탭 2] S&P 500 리스트
# ---------------------------------------------------------
elif choice == "📋 S&P 500 리스트":
    st.subheader("📋 S&P 500 전체 종목 리스트")
    if sp500_df is not None:
        # 보기 좋게 컬럼명 변경
        display_df = sp500_df.rename(columns={'Symbol': '티커', 'Name': '종목명', 'Sector': '업종'})
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.error("종목 리스트를 불러오는데 실패했습니다.")

# ---------------------------------------------------------
# [탭 3] 분야별 TOP 5 랭킹 (한글 표시 + 전수 조사)
# ---------------------------------------------------------
elif choice == "🏆 분야별 TOP 5 랭킹":
    st.subheader("🏆 분야별 저평가 우량주 TOP 5")
    st.caption("※ 선택한 업종의 **모든 종목**을 실시간으로 분석하므로 시간이 조금 걸릴 수 있습니다.")
    
    if sp500_df is not None:
        # [해결] 한글 업종명 표시 문제 해결
        sectors = sorted(sp500_df['Sector'].unique())
        # "Energy (에너지)" 형태로 리스트 생성
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        
        selected_option = st.selectbox("분석할 업종을 선택하세요", sector_options)
        
        # 선택된 값에서 영문 업종명만 추출 ("Energy (에너지)" -> "Energy")
        pure_sector = selected_option.split(' (')[0]
        
        if st.button(f"🚀 {pure_sector} 전 종목 분석 시작"):
            # [해결] 해당 업종의 '모든' 종목 가져오기 (head 제한 없음)
            targets = sp500_df[sp500_df['Sector'] == pure_sector]
            total_stocks = len(targets)
            
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 루프 시작
            for i, row in enumerate(targets.itertuples()):
                ticker = row.Symbol
                status_text.text(f"🔍 ({i+1}/{total_stocks}) {ticker} 분석 중...")
                
                # 데이터 수집 (딜레이 최소화하되 차단 방지)
                d, _ = get_stock_data(ticker)
                
                if d:
                    s, m_text = calculate_score(d)
                    results.append({
                        '티커': ticker,
                        '종목명': d['Name'],
                        '점수': s,
                        '안전마진': m_text,
                        '현재가': f"${d['Price']}",
                        'ROE': f"{d['ROE']}%",
                        'PER': f"{d['PER']}배"
                    })
                
                # 진행률 업데이트
                progress_bar.progress((i + 1) / total_stocks)
                # 너무 빠르면 차단되므로 0.2초 딜레이 (전수조사라 조금 빠르게)
                time.sleep(0.2)
            
            # 완료 후 처리
            progress_bar.empty()
            status_text.empty()
            
            if results:
                # 점수 높은 순 정렬 -> 상위 5개 추출
                df_results = pd.DataFrame(results).sort_values(by='점수', ascending=False).head(5)
                # 순위 컬럼 만들기
                df_results.reset_index(drop=True, inplace=True)
                df_results.index = df_results.index + 1
                df_results.index.name = '순위'
                
                st.success(f"✅ {pure_sector} 업종 {total_stocks}개 종목 분석 완료!")
                st.table(df_results)
            else:
                st.warning("데이터를 가져오지 못했거나, 해당 업종에 분석 가능한 종목이 없습니다.")

# =========================================================
# 4. 사이드바 (수익화 및 정보)
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    
    t1, t2 = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with t1:
        st.markdown('<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with t2:
        # 이미지 파일이 없어도 에러 안 나도록 처리
        import os
        if os.path.exists("kakao_qr.png.jpg"):
            st.image("kakao_qr.png.jpg", use_container_width=True)
            st.caption("예금주: 최*환")
        else:
            st.text("후원 계좌: 카카오뱅크\n3333-xx-xxxxxx")
            
    st.markdown("---")
    st.info("📚 **워렌 버핏 투자법 완벽 가이드**")
    st.markdown("[👉 **'워렌 버핏 바이블' 최저가 보기**](https://link.coupang.com/a/dz5HhD)")
