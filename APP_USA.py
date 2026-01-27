import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
import os    # [해결] NameError 방지
import time  # [해결] 야후 차단 방지용 대기 시간

# =========================================================
# 1. 페이지 설정
# =========================================================
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

# 표 디자인 강화
st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e6e6e6; padding: 15px; border-radius: 10px; }
    .stDataFrame { border: 2px solid #004e92; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 데이터 수집 및 점수 계산 로직 (안정성 강화)
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

def get_stock_info_stable(ticker):
    """데이터 수집 실패를 최소화하는 안정화 함수"""
    try:
        stock = yf.Ticker(ticker)
        # 데이터를 한 번에 가져오지 못할 경우를 대비해 핵심 정보만 추출
        info = stock.fast_info
        detailed_info = stock.info
        
        price = detailed_info.get('currentPrice', detailed_info.get('regularMarketPrice', 0))
        if price == 0: return None
        
        return {
            'Price': price,
            'TargetPrice': detailed_info.get('targetMeanPrice', 0),
            'ROE': round(detailed_info.get('returnOnEquity', 0) * 100, 2) if detailed_info.get('returnOnEquity') else 0,
            'PER': round(detailed_info.get('trailingPE', 0), 2) if detailed_info.get('trailingPE') else 0,
            'PBR': round(detailed_info.get('priceToBook', 0), 2) if detailed_info.get('priceToBook') else 0,
            'Name': detailed_info.get('shortName', ticker)
        }
    except:
        return None

def calculate_score(data):
    """버핏식 가치투자 점수 계산 (100점 만점)"""
    score = 0
    if data['ROE'] >= 15: score += 50
    if 0 < data['PBR'] <= 2.0: score += 30
    if 0 < data['PER'] <= 20: score += 20
    
    m_rate = ((data['TargetPrice'] - data['Price']) / data['Price'] * 100) if data['TargetPrice'] > 0 else 0
    return score, f"{m_rate:.1f}%"

# =========================================================
# 3. 메인 화면 구성
# =========================================================
st.title("🗽 워렌 버핏의 미국 주식 계산기")

tab1, tab2, tab3 = st.tabs(["🔍 종목 진단", "📋 S&P 500 리스트", "🏆 분야별 TOP 5 랭킹"])

# --- [1] 종목 진단 ---
with tab1:
    search_ticker = st.text_input("분석할 티커 입력 (예: TSLA, AAPL)", "")
    if search_ticker:
        with st.spinner("데이터 분석 중..."):
            d = get_stock_info_stable(search_ticker.upper())
            if d:
                score, m_text = calculate_score(d)
                st.subheader(f"📊 {d['Name']} 분석 결과")
                col1, col2 = st.columns(2)
                col1.metric("버핏 점수", f"{score}점")
                col2.metric("안전마진 (목표가 대비)", m_text)
                st.write(f"현재가: ${d['Price']} | ROE: {d['ROE']}% | PER: {d['PER']}배 | PBR: {d['PBR']}배")
            else: st.error("해당 종목의 데이터를 가져올 수 없습니다.")

# --- [2] 리스트 ---
with tab2:
    df = get_sp500_data()
    if df is not None:
        st.dataframe(df[['Symbol', 'Name', 'Sector']], use_container_width=True, hide_index=True)

# --- [3] 분야별 TOP 5 (사장님 요청: 표 형태 출력)
with tab3:
    st.subheader("💎 분야별 저평가 우량주 TOP 5")
    st.info("선택한 업종의 종목들을 실시간으로 채점하여 가장 점수가 높은 5개를 뽑아냅니다.")

    sp500 = get_sp500_data()
    if sp500 is not None:
        s_map = get_sector_map()
        sector_list = sorted(sp500['Sector'].unique())
        options = [f"{s} ({s_map.get(s, '기타')})" for s in sector_list]
        
        selected = st.selectbox("분석할 업종 선택", options)
        target_sector = selected.split(' (')[0]
        
        if st.button(f"🚀 {target_sector} TOP 5 추출 시작"):
            # 해당 섹터 종목 추출 (상위 20개로 안정적 분석)
            sector_stocks = sp500[sp500['Sector'] == target_sector].head(20)
            results = []
            
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, row in enumerate(sector_stocks.itertuples()):
                status.text(f"🔍 {row.Symbol} 채점 중... ({i+1}/{len(sector_stocks)})")
                
                # [핵심] 야후 차단 방지: 요청 사이마다 미세한 휴식 시간 추가
                time.sleep(0.5)
                
                data = get_stock_info_stable(row.Symbol)
                if data:
                    score, m_text = calculate_score(data)
                    results.append({
                        '티커': row.Symbol,
                        '종목명': data['Name'],
                        '버핏 점수': score,
                        '안전마진': m_text,
                        'ROE': f"{data['ROE']}%",
                        'PER': f"{data['PER']}배",
                        '현재가': f"${data['Price']}"
                    })
                progress_bar.progress((i + 1) / len(sector_stocks))
            
            status.empty()
            if results:
                # 점수 순으로 정렬하여 상위 5개만 표로 출력
                rank_df = pd.DataFrame(results).sort_values('버핏 점수', ascending=False).head(5)
                rank_df.index = range(1, len(rank_df) + 1)
                rank_df.index.name = "순위"
                
                st.success(f"✅ {target_sector} 분야 분석 완료!")
                st.table(rank_df) # 사장님이 원하신 깔끔한 표 형태
            else:
                st.error("데이터 수집에 실패했습니다. 야후 서버가 일시적으로 차단했을 수 있으니 1분 후 다시 시도해주세요.")

# =========================================================
# 5. 수익화 사이드바
# =========================================================
with st.sidebar:
    st.markdown("---")
    st.header("☕ 개발자 후원")
    
    t_card, t_kakao = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    with t_card:
        st.markdown(f'<a href="https://buymeacoffee.com/jh.choi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" style="width:100%"></a>', unsafe_allow_html=True)
    with t_kakao:
        qr_path = "kakao_qr.png.jpg"
        if os.path.exists(qr_path): # [해결] NameError 안 남
            st.image(qr_path, use_container_width=True)
            st.caption("예금주: 최*환")
    
    st.markdown("---")
    # 사장님 요청 도서 추천 문구
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")
