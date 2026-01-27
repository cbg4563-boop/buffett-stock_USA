import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # NameError 방지
import time  # 데이터 로딩 안정성 확보

# =========================================================
# 1. 페이지 설정
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

# 스타일 (표 가독성 향상)
st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    .stDataFrame { border: 2px solid #635bff; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 데이터 및 로직 함수
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

def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        if price == 0: return None
        return {
            'Price': price,
            'TargetPrice': info.get('targetMeanPrice', 0),
            'ROE': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
            'PER': round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else 0,
            'PBR': round(info.get('priceToBook', 0), 2) if info.get('priceToBook') else 0,
            'DIV': round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0,
            'Name': info.get('shortName', ticker)
        }
    except: return None

def calculate_us_score(data):
    score = 0
    roe, per, pbr, div = data['ROE'], data['PER'], data['PBR'], data['DIV']
    if roe >= 15: score += 50
    if 0 < pbr <= 2.0: score += 20
    if 0 < per <= 20: score += 20
    if div >= 1.0: score += 10
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, f"{m_rate:.1f}%"

# =========================================================
# 3. 메인 화면 레이아웃
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

tab1, tab2, tab3 = st.tabs(["🔍 종목 개별 진단", "📋 S&P 500 리스트", "💎 분야별 TOP 5 랭킹"])

# --- [1] 개별 진단 ---
with tab1:
    search_input = st.text_input("종목 티커 입력 (예: AAPL, TSLA)", "")
    if search_input:
        with st.spinner("분석 중..."):
            d = get_stock_info(search_input.upper())
            if d:
                score, m_text = calculate_us_score(d)
                st.metric(f"{d['Name']} 점수", f"{score}점", delta=f"안전마진 {m_text}")
                st.write(f"현재가: ${d['Price']} | ROE: {d['ROE']}% | PER: {d['PER']}배 | PBR: {d['PBR']}배")
            else: st.error("정보를 찾을 수 없습니다.")

# --- [2] 리스트 ---
with tab2:
    df = get_sp500_data()
    if df is not None: st.dataframe(df[['Symbol', 'Name', 'Sector']], use_container_width=True)

# --- [3] 분야별 TOP 5 (사장님 요청: 표 형태로 점수 순 출력) ---
with tab3:
    st.subheader("🏆 업종별 워렌 버핏 점수 TOP 5")
    st.caption("해당 분야의 종목들을 실시간으로 분석하여 점수가 가장 높은 5개를 표로 보여줍니다.")

    df = get_sp500_data()
    if df is not None:
        sector_map = get_sector_map()
        sectors = sorted(df['Sector'].unique())
        sector_options = [f"{s} ({sector_map.get(s, '기타')})" for s in sectors]
        
        selected_sector = st.selectbox("분석할 분야를 선택하세요", sector_options)
        pure_sector = selected_sector.split(' (')[0]
        
        if st.button(f"🚀 {pure_sector} 분야 TOP 5 추출"):
            targets = df[df['Sector'] == pure_sector].head(20) # 속도를 위해 20개 스캔
            results = []
            
            bar = st.progress(0)
            status = st.empty()
            
            for i, row in enumerate(targets.itertuples()):
                status.text(f"🔍 {row.Symbol} 채점 중... ({i+1}/{len(targets)})")
                time.sleep(0.3) # 야후 차단 방지
                
                d = get_stock_info(row.Symbol)
                if d:
                    score, m_text = calculate_us_score(d)
                    results.append({
                        '순위': 0,
                        '티커': row.Symbol,
                        '종목명': d['Name'],
                        '버핏 점수': score,
                        '안전마진': m_text,
                        '현재가': f"${d['Price']}",
                        'ROE': f"{d['ROE']}%",
                        'PER': f"{d['PER']}배"
                    })
                bar.progress((i + 1) / len(targets))
            
            status.empty()
            if results:
                # 점수 순 정렬 후 TOP 5 자르기
                final_df = pd.DataFrame(results).sort_values('버핏 점수', ascending=False).head(5)
                final_df['순위'] = range(1, len(final_df) + 1)
                
                st.success(f"✅ {pure_sector} 분야 분석 완료!")
                st.table(final_df.set_index('순위')) # 사장님이 원하신 '표' 형태
            else:
                st.error("데이터 수집 실패. 잠시 후 다시 시도해주세요.")

# =========================================================
# 5. 수익화 사이드바
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    tab_card, tab_kakao = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with tab_card:
        st.markdown(f'<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with tab_kakao:
        qr_file = "kakao_qr.png.jpg"
        if os.path.exists(qr_file):
            st.image(qr_file, use_container_width=True)
            st.caption("예금주: 최*환")
    st.markdown("---")
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
