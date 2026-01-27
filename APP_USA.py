import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # [해결] NameError 방지
import time  # [해결] 수집 실패 방지용 딜레이

# =========================================================
# 1. 페이지 설정 및 내비게이션 상태 초기화
# =========================================================
st.set_page_config(page_title="워렌 버핏 주식매매 기준 계산기", page_icon="🗽", layout="wide")

# 메뉴 리스트 (이름 변경 금지)
menu_list = ["🔍 종목 진단", "📋 S&P 500 리스트", "🏆 분야별 워렌 버핏 점수 TOP 5 랭킹"]

# [해결] ValueError 방지를 위한 안전한 초기화
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
# 2. 강력한 데이터 수집 및 검색 로직
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

def find_ticker_fast(user_input, df_sp500):
    """한글/영어 이름을 티커로 즉시 변환"""
    user_input = user_input.strip()
    if not user_input: return ""
    
    # 한글 매핑 (사장님 요청 반영)
    k_map = {'애플': 'AAPL', '테슬라': 'TSLA', '마소': 'MSFT', '구글': 'GOOGL', '엔비디아': 'NVDA', '아마존': 'AMZN'}
    if user_input in k_map: return k_map[user_input]
    
    if df_sp500 is not None:
        upper_in = user_input.upper()
        if upper_in in df_sp500['Symbol'].values: return upper_in
        # 이름 포함 검색
        match = df_sp500[df_sp500['Name'].str.contains(user_input, case=False, na=False)]
        if not match.empty: return match.iloc[0]['Symbol']
    return user_input.upper()

def get_stock_data_with_retry(ticker, retries=3):
    """[핵심] 수집 실패 시 최대 3번까지 재시도하는 무적 로직"""
    for i in range(retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            # 가격 데이터가 없으면 실패로 간주
            price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            if price > 0:
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
            time.sleep(1) # 실패 시 1초 쉬고 재시도
        except:
            time.sleep(1)
            continue
    return None, None

# =========================================================
# 3. 메인 내비게이션
# =========================================================
st.title("🗽 워렌 버핏 주식매매 기준 계산기")

# [해결] ValueError 방지: 안전하게 현재 인덱스 찾기
try:
    current_idx = menu_list.index(st.session_state['nav_choice'])
except:
    current_idx = 0

choice = st.radio("메뉴", menu_list, index=current_idx, horizontal=True, label_visibility="collapsed")
st.session_state['nav_choice'] = choice

sp500_df = get_sp500_data()
sector_map = get_sector_map()
st.markdown("---")

# =========================================================
# 4. 기능별 구현
# =========================================================

# --- [1] 종목 진단 (검색 및 그래프 복구) ---
if choice == menu_list[0]:
    t_val = st.session_state['search_ticker']
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1:
            in_txt = st.text_input("종목명 또는 티커 입력", value=t_val, placeholder="예: 애플, TSLA, NVDA", label_visibility="collapsed")
        with c2:
            btn = st.form_submit_button("🔍 진단하기")

    if (btn and in_txt) or (t_val and in_txt):
        if t_val: st.session_state['search_ticker'] = ""
        ticker = find_ticker_fast(in_txt, sp500_df)
        
        with st.spinner(f"🇺🇸 {ticker} 데이터를 가져오는 중..."):
            data, history = get_stock_data_with_retry(ticker)
            if data:
                # 점수 계산
                score = 0
                if data['ROE'] >= 15: score += 50
                if 0 < data['PBR'] <= 2.0: score += 30
                if 0 < data['PER'] <= 20: score += 20
                m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
                
                # [해결] DeltaGenerator 에러 방지 (정석 출력)
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.subheader("종합 점수")
                    if score >= 60: st.success(f"# 💎 {score}점")
                    else: st.warning(f"# ✋ {score}점")
                    st.metric("안전마진", f"{m_rate:.1f}%", delta=f"{m_rate:.1f}%")
                with col_b:
                    st.subheader(f"{data['Name']} ({ticker})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("현재가", f"${data['Price']}")
                    m2.metric("ROE", f"{data['ROE']}%")
                    m3.metric("PER", f"{data['PER']}배")
                    m4.metric("PBR", f"{data['PBR']}배")
                
                # [복구] 그래프 출력
                if not history.empty:
                    st.subheader("📈 최근 1년 주가 흐름")
                    st.line_chart(history['Close'], color="#004e92")
            else:
                st.error("데이터 수집에 실패했습니다. 티커가 정확한지 확인하시거나 잠시 후 다시 시도해 주세요.")

# --- [3] 분야별 TOP 5 (표 전용) ---
elif choice == menu_list[2]:
    st.subheader("🏆 분야별 워렌 버핏 점수 TOP 5")
    if sp500_df is not None:
        sects = sorted(sp500_df['Sector'].unique())
        opts = [f"{s} ({sector_map.get(s, '기타')})" for s in sects]
        sel = st.selectbox("분석할 업종을 선택하세요", opts)
        pure_s = sel.split(' (')[0]
        
        if st.button(f"🚀 {pure_s} TOP 5 추출"):
            targets = sp500_df[sp500_df['Sector'] == pure_s].head(20)
            res = []
            p_bar = st.progress(0)
            for i, row in enumerate(targets.itertuples()):
                time.sleep(0.5) # 차단 방지
                d, _ = get_stock_data_with_retry(row.Symbol, retries=1)
                if d:
                    s = 0
                    if d['ROE'] >= 15: s += 50
                    if 0 < d['PBR'] <= 2.0: s += 30
                    if 0 < d['PER'] <= 20: s += 20
                    m_t = f"{((d['TargetPrice']-d['Price'])/d['Price']*100):.1f}%" if d['TargetPrice'] > 0 else "-"
                    res.append({'티커': row.Symbol, '종목명': d['Name'], '점수': s, '안전마진': m_t, '현재가': f"${d['Price']}"})
                p_bar.progress((i+1)/len(targets))
            
            if res:
                final = pd.DataFrame(res).sort_values('점수', ascending=False).head(5)
                final.index = range(1, len(final) + 1)
                st.table(final) # 사장님 요청: 표만 깔끔하게 노출
            else:
                st.error("데이터 수집 실패")

elif choice == menu_list[1]:
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# =========================================================
# 5. 수익화 사이드바
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    t1, t2 = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with t1:
        st.markdown(f'<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with t2:
        qr = "kakao_qr.png.jpg"
        if os.path.exists(qr):
            st.image(qr, use_container_width=True)
            st.caption("예금주: 최*환") # 마스킹 완료
    st.markdown("---")
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
