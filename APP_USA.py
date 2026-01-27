import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # [해결] NameError 방지용
import time  # [해결] 야후 차단 방지용 대기 시간 추가

# =========================================================
# 1. 페이지 설정 및 상태 관리
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

if 'active_tab' not in st.session_state:
    st.session_state['active_tab'] = "🔍 종목 진단"
if 'target_ticker' not in st.session_state:
    st.session_state['target_ticker'] = ""

# 스타일 (깔끔한 UI)
st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] > div:has(input[type="radio"]) {
        background-color: #f8f9fb; padding: 15px; border-radius: 15px; border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 핵심 로직 (야후 차단 방지 로직 강화)
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
    # [핵심] 야후 파이낸스 데이터 수집 시도
    try:
        stock = yf.Ticker(ticker)
        # 데이터가 늦게 올 수 있으므로 아주 잠깐 대기
        info = stock.info
        if not info or 'currentPrice' not in info and 'regularMarketPrice' not in info:
            return None, None
            
        price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        data = {
            'Price': price,
            'TargetPrice': info.get('targetMeanPrice', 0),
            'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
            'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
            'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
            'DIV': round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0,
            'Name': info.get('shortName', ticker)
        }
        return data, stock.history(period="1y")
    except:
        return None, None

def calculate_us_score(data):
    score = 0
    report = []
    roe, per, pbr, div = data['ROE'], data['PER'], data['PBR'], data['DIV']
    if roe >= 15: score += 50; report.append("✅ [수익성] ROE 우수")
    if 0 < pbr <= 2.0: score += 20; report.append("✅ [자산] PBR 저평가")
    if 0 < per <= 20: score += 20; report.append("✅ [밸류] PER 적정")
    if div >= 1.0: score += 10; report.append("✅ [배당] 매력적")
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, report, f"{m_rate:.1f}%", m_rate

# =========================================================
# 3. 메인 화면 및 내비게이션
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

menu = ["🔍 종목 진단", "📋 S&P 500 리스트", "💎 업종별 보물찾기"]
choice = st.radio("메뉴", menu, index=menu.index(st.session_state['active_tab']), horizontal=True, label_visibility="collapsed")
st.session_state['active_tab'] = choice

sp500_df = get_sp500_data()
sector_map = get_sector_map()

# --- [메뉴 1] 종목 진단 ---
if choice == "🔍 종목 진단":
    search_query = st.session_state['target_ticker']
    with st.form(key='search_form'):
        c1, c2 = st.columns([4, 1])
        with c1: input_text = st.text_input("종목 입력", value=search_query, placeholder="예: Apple, 테슬라", label_visibility="collapsed")
        with c2: search_btn = st.form_submit_button("🔍 계산")

    if (search_btn and input_text) or (search_query and input_text):
        if search_query: st.session_state['target_ticker'] = ""
        ticker = find_ticker(input_text, sp500_df)
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
            else: st.error("종목 정보를 가져오지 못했습니다. 잠시 후 다시 시도하세요.")

# --- [메뉴 2] 리스트 ---
elif choice == "📋 S&P 500 리스트":
    if sp500_df is not None:
        st.dataframe(sp500_df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# --- [메뉴 3] 보물찾기 (강화 버전) ---
elif choice == "💎 업종별 보물찾기":
    st.subheader("💎 업종별 저평가 우량주 발굴")
    if sp500_df is not None:
        sectors_raw = sorted(sp500_df['Sector'].unique())
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors_raw]
        selected = st.selectbox("업종 선택", sector_options)
        real_sector = selected.split(' (')[0]
        
        if st.button(f"🚀 {real_sector} 분석 시작"):
            targets = sp500_df[sp500_df['Sector'] == real_sector].head(25) # 안정성을 위해 개수 조절
            results = []
            bar = st.progress(0)
            status = st.empty()
            
            for i, row in enumerate(targets.itertuples()):
                ticker = row.Symbol
                status.text(f"🔍 {ticker} 채점 중... ({i+1}/{len(targets)})")
                
                # [중요] 야후 차단 방지: 0.3초씩 쉬어가며 요청
                time.sleep(0.3)
                
                d, _ = get_stock_info(ticker)
                if d:
                    s, _, m_text, _ = calculate_us_score(d)
                    results.append({'티커': ticker, '종목명': d['Name'], '점수': s, '현재가': f"${d['Price']}", '안전마진': m_text})
                
                bar.progress((i + 1) / len(targets))
            
            status.empty()
            if results:
                df_res = pd.DataFrame(results).sort_values('점수', ascending=False)
                st.success(f"✅ {len(results)}개 종목 분석 완료!")
                for row in df_res.head(10).to_dict('records'):
                    with st.container():
                        c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                        c1.write(f"**{row['티커']}**")
                        c2.write(row['종목명'])
                        c3.write(f"**{row['점수']}점**")
                        if c4.button(f"🔍 진단", key=f"btn_v2_{row['티커']}"):
                            st.session_state['target_ticker'] = row['티커']
                            st.session_state['active_tab'] = "🔍 종목 진단"
                            st.rerun()
                        st.markdown("---")
            else:
                st.error("데이터 수집에 실패했습니다. 야후 파이낸스 서버가 일시적으로 응답하지 않습니다. 1~2분 후 다시 시도해주세요.")

# =========================================================
# 5. 수익화 사이드바 (최종 수정)
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
        if os.path.exists(qr_file): # [해결] NameError 안 남
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최*환")
        else:
            st.error("QR 파일 없음")

    st.markdown("---")
    # [해결] 쿠팡 파트너스 정상 노출
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
