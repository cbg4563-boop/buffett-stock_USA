import streamlit as st
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr

# --- 페이지 설정 ---
st.set_page_config(
    page_title="워렌 버핏의 미국 주식 계산기",
    page_icon="🗽",
    layout="wide"
)

# --- 스타일 (모바일 다크모드 완벽 대응) ---
st.markdown("""
<style>
    /* 1. 메트릭 카드: 배경 흰색, 글씨 검은색 강제 고정 */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e6e6e6;
        padding: 15px;
        border-radius: 10px;
    }
    div[data-testid="stMetric"] label {
        color: #666666 !important; /* 제목: 회색 */
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #000000 !important; /* 숫자: 검은색 */
    }
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        color: inherit !important; /* 등락폭 색상은 유지 */
    }

    /* 2. 탭 스타일 */
    button[data-baseweb="tab"] {
        font-size: 16px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 🔍 데이터 및 한글 매핑 (확장됨)
# ---------------------------------------------------------
@st.cache_data(ttl=86400)
def get_korean_name_map():
    # 티커: [한글 키워드들...]
    return {
        'AAPL': ['애플', '아이폰'], 
        'MSFT': ['마이크로소프트', '마소'], 
        'GOOGL': ['구글', '알파벳'], 
        'AMZN': ['아마존'],
        'TSLA': ['테슬라'], 
        'NVDA': ['엔비디아'], 
        'META': ['메타', '페이스북'], 
        'NFLX': ['넷플릭스'],
        'AMD': ['AMD', '암드'], 
        'INTC': ['인텔'], 
        'QCOM': ['퀄컴'], 
        'AVGO': ['브로드컴'], 
        'ARM': ['암', 'ARM'],
        'TXN': ['텍사스', '텍사스인스트루먼트'], 
        'MU': ['마이크론'], 
        'KO': ['코카콜라'], 
        'PEP': ['펩시'],
        'SBUX': ['스타벅스'], 
        'MCD': ['맥도날드'], 
        'DIS': ['디즈니'], 
        'NKE': ['나이키'],
        'JNJ': ['존슨앤존슨'], 
        'PFE': ['화이자'], 
        'MRK': ['머크'], 
        'LLY': ['일라이릴리'],
        'WMT': ['월마트'], 
        'COST': ['코스트코'], 
        'TGT': ['타겟'], 
        'HD': ['홈디포'],
        'JPM': ['JP모건'], 
        'BAC': ['뱅크오브아메리카'], 
        'V': ['비자'], 
        'MA': ['마스터카드'],
        'BRK.B': ['버크셔해서웨이', '버크셔'], 
        'O': ['리얼티인컴', '월배당'], 
        'AMT': ['아메리칸타워'],
        'PLTR': ['팔란티어'], 
        'IONQ': ['아이온큐'], 
        'RIVN': ['리비안'], 
        'LCID': ['루시드'],
        'TSM': ['TSMC'], 
        'ASML': ['ASML'], 
        'GME': ['게임스탑'], 
        'AMC': ['AMC'],
        'SOXL': ['반도체 3배', 'SOXL'], 
        'TQQQ': ['나스닥 3배', 'TQQQ'], 
        'JEPI': ['JEPI', '제피'],
        'SCHD': ['슈드', 'SCHD'], 
        'SPY': ['S&P500', '스파이'], 
        'QQQ': ['나스닥', '큐큐큐'], 
        'VOO': ['S&P500', 'VOO']
    }

# 한글 이름 찾기 헬퍼 함수
def get_kor_name_by_ticker(ticker, default_eng_name):
    k_map = get_korean_name_map()
    if ticker in k_map:
        return k_map[ticker][0] # 첫 번째 한글명 반환
    return default_eng_name

def get_stock_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'regularMarketPrice' not in info and 'currentPrice' not in info:
            return None, None

        price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        target_price = info.get('targetMeanPrice', 0) # 애널리스트 목표가 (내재가치 대용)
        
        roe = info.get('returnOnEquity', 0)
        per = info.get('trailingPE', 0)
        pbr = info.get('priceToBook', 0)
        div = info.get('dividendYield', 0)
        
        data = {
            'Price': price,
            'TargetPrice': target_price, # 목표주가 추가
            'ROE': round(roe * 100, 2) if roe else 0,
            'PER': round(per, 2) if per else 0,
            'PBR': round(pbr, 2) if pbr else 0,
            'DIV': round(div * 100, 2) if div else 0,
            'Name': info.get('shortName', ticker),
            'Industry': info.get('industry', 'ETF/Others')
        }
        
        history = stock.history(period="1y")
        return data, history
    except:
        return None, None

@st.cache_data(ttl=86400)
def get_sp500_list():
    try:
        df = fdr.StockListing('S&P500')
        # 한글명 컬럼 추가
        k_map = get_korean_name_map()
        # Symbol이 맵에 있으면 한글명, 없으면 영문 Name 사용
        df['종목명'] = df.apply(lambda row: k_map[row['Symbol']][0] if row['Symbol'] in k_map else row['Name'], axis=1)
        return df
    except:
        return None

# ---------------------------------------------------------
# 2. 📊 채점 및 안전마진 계산 로직
# ---------------------------------------------------------
def calculate_us_score(data):
    score = 0
    report = []
    
    roe = data['ROE']
    per = data['PER']
    pbr = data['PBR']
    div = data['DIV']
    
    # 채점 로직
    if roe >= 20: score += 50; report.append("✅ [수익성] ROE 20% 이상 (괴물급)")
    elif roe >= 15: score += 30; report.append("✅ [수익성] ROE 15% 이상 (우수)")
    elif roe >= 10: score += 10;
    
    if 0 < pbr <= 1.5: score += 20; report.append("✅ [자산] PBR 1.5배 이하 (저평가)")
    elif 0 < pbr <= 4.0: score += 10;
    
    if 0 < per <= 15: score += 20; report.append("✅ [밸류] PER 15배 이하 (저평가)")
    elif 0 < per <= 25: score += 10;
    
    if div >= 1.5: score += 10; report.append("✅ [배당] 1.5% 이상")
    
    # [추가] 안전마진 계산 (목표주가 vs 현재가)
    safety_margin_text = ""
    margin_rate = 0
    
    if data['TargetPrice'] and data['Price']:
        # (목표가 - 현재가) / 현재가 * 100
        if data['TargetPrice'] > 0:
            margin_rate = ((data['TargetPrice'] - data['Price']) / data['Price']) * 100
            
            if margin_rate > 0:
                safety_margin_text = f"💰 안전마진: +{margin_rate:.1f}% (저평가)"
            else:
                safety_margin_text = f"⚠️ 고평가: {margin_rate:.1f}% (목표가 초과)"
    else:
        safety_margin_text = "데이터 부족으로 계산 불가"

    return score, report, safety_margin_text, margin_rate

# ---------------------------------------------------------
# 3. 🖥️ 메인 화면 구성
# ---------------------------------------------------------

st.title("🗽 워렌 버핏의 미국 주식 계산기")
st.markdown("### 💡 미국 주식 적정주가 & 안전마진 계산기")
st.caption("Data: Yahoo Finance | 기준: US Market Standard")
st.warning("⚠️ **[면책 조항]** 본 서비스는 투자 참고용이며, 데이터 오류가 있을 수 있습니다. 모든 투자의 책임은 본인에게 있습니다.")

sp500_df = get_sp500_list()
korean_map = get_korean_name_map()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 종목 진단", "🏆 S&P 500 리스트", "🚀 대장주 Top 5"])

# --- 탭 1: 검색 (한글 완벽 지원) ---
with tab1:
    st.subheader("종목 진단")
    st.write("티커(AAPL) 또는 한글(애플, 슈드)로 검색하세요.")
    
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        # form을 써서 엔터키로 검색 가능하게 함
        with st.form(key='search_form'):
            search_input = st.text_input("종목 검색", placeholder="예: 삼성전자 말고 애플, TSLA", label_visibility="collapsed")
            submit_button = st.form_submit_button(label='검색')

    if submit_button and search_input:
        user_input = search_input.upper().strip()
        target_ticker = user_input # 기본은 입력값 그대로
        
        # [핵심] 한글 검색 로직 강화
        # 1. 딕셔너리 키(티커)와 일치하는지 확인
        if user_input in korean_map:
            target_ticker = user_input
        else:
            # 2. 딕셔너리 값(한글 리스트) 중에 포함되는지 확인
            found = False
            for ticker, keywords in korean_map.items():
                if any(k in user_input for k in keywords): # '애플' 입력 시 keywords 리스트 확인
                    target_ticker = ticker
                    found = True
                    break
            
            # 3. 못 찾았지만 영어가 아니라면? (경고)
            if not found and not user_input.isascii():
                st.error("지원하지 않는 한글 종목명이거나, 티커를 입력해야 합니다.")
                st.stop()
        
        with st.spinner(f"🇺🇸 {target_ticker} 데이터 분석 중..."):
            data, history = get_stock_info(target_ticker)
            
        if data:
            score, report, margin_text, margin_rate = calculate_us_score(data)
            
            st.divider()
            c1, c2 = st.columns([1, 2])
            
            with c1:
                st.subheader("버핏 점수")
                if score >= 80: st.success(f"# 💎 {score}점\n**강력 매수**")
                elif score >= 60: st.info(f"# 🥇 {score}점\n**매수 추천**")
                elif score >= 40: st.warning(f"# ✋ {score}점\n**관망**")
                else: st.error(f"# 🧱 {score}점\n**주의**")
                
                # [핵심] 안전마진 시각화
                st.markdown("---")
                if margin_rate > 10:
                    st.success(f"**{margin_text}**") # 초록색
                elif margin_rate > 0:
                    st.info(f"**{margin_text}**") # 파란색
                else:
                    st.error(f"**{margin_text}**") # 빨간색
                
                if data['TargetPrice'] > 0:
                    st.caption(f"적정가(목표): ${data['TargetPrice']:,.2f}")

            with c2:
                # 한글 이름 표시
                kor_name = get_kor_name_by_ticker(target_ticker, data['Name'])
                st.subheader(f"{kor_name} ({target_ticker})")
                st.write(f"업종: {data['Industry']}")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("현재가", f"${data['Price']:,.2f}")
                m2.metric("ROE", f"{data['ROE']}%")
                m3.metric("PER", f"{data['PER']}배")
                m4.metric("PBR", f"{data['PBR']}배")
            
            st.subheader("📉 최근 1년 주가 흐름")
            if history is not None and not history.empty:
                st.line_chart(history['Close'], color="#004e92")

            st.subheader("📝 투자 포인트")
            if report:
                for r in report: st.markdown(f"- {r}")
            else:
                st.info("버핏 기준 저평가 요인 부족")

        else:
            st.error(f"'{target_ticker}' 종목을 찾을 수 없습니다.")

# --- 탭 2: 리스트 (한글 적용) ---
with tab2:
    st.subheader("S&P 500 종목 리스트")
    if sp500_df is not None:
        # 보기 좋게 컬럼 순서 변경 및 한글명 맨 앞으로
        df_display = sp500_df[['Symbol', '종목명', 'Sector', 'Industry']].copy()
        df_display.columns = ['티커', '종목명', '섹터', '산업'] # 헤더도 한글로
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.error("리스트 로딩 실패")

# --- 탭 3: 스캔 (한글 적용) ---
with tab3:
    st.subheader("USA S&P 500 대장주 Top 5 (실시간 분석)")
    if st.button("🚀 스캔 시작"):
        if sp500_df is not None:
            # 상위 20개만
            targets = sp500_df.head(20)
            results = []
            bar = st.progress(0)
            
            total = len(targets)
            for i, row in enumerate(targets.itertuples()):
                ticker = row.Symbol
                k_name = row.종목명 # 미리 만들어둔 한글명
                
                d, _ = get_stock_info(ticker)
                if d:
                    s, _, m_text, m_rate = calculate_us_score(d)
                    results.append({
                        '종목명': k_name, # 한글명 사용
                        '티커': ticker,
                        '점수': s,
                        '안전마진': f"{m_rate:.1f}%" if m_rate else "-",
                        '현재가': f"${d['Price']:,.2f}",
                        'ROE': f"{d['ROE']}%",
                        'PER': d['PER']
                    })
                bar.progress((i+1)/total)
            bar.empty()
            
            if results:
                df_res = pd.DataFrame(results).sort_values('점수', ascending=False).head(5)
                df_res.index = range(1, 6)
                st.balloons()
                st.success("✅ 분석 완료!")
                st.dataframe(df_res, use_container_width=True)
        else:
            st.error("데이터 로딩 실패")

# =========================================================
# 💸 [수익화 파트] 사이드바 (최종_진짜_완성.ver)
# =========================================================
with st.sidebar:
    st.markdown("---")
    
    # 1. 개발자 후원 (탭으로 분리: 카드 vs 카카오)
    st.header("☕ 개발자 후원")
    st.caption("서버비 유지에 큰 힘이 됩니다! 🙇‍♂️")
    
    # 탭 만들기 (여기서 에러 안 나게 수정함)
    tab_card, tab_kakao = st.tabs(["💳 카드/페이", "🟡 카카오송금"])
    
    # [탭 1] Buy Me a Coffee (카드/페이팔)
    with tab_card:
        st.write(" ")
        my_coffee_link = "https://buymeacoffee.com/cbg4563t" 
        st.markdown(f"""
        <a href="{my_coffee_link}" target="_blank">
            <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 45px !important;width: 100% !important;" >
        </a>
        """, unsafe_allow_html=True)
        st.caption("해외 결제 / 간편 후원")

    # [탭 2] 카카오페이 QR (송금)
    with tab_kakao:
        st.write(" ")
        # GitHub에 'kakao_qr.png' 파일이 없으면 에러가 납니다.
        # 파일이 있는지 확인하는 안전장치 추가
        import os
        if os.path.exists("kakao_qr.png.jpg"):
            st.image("kakao_qr.png.jpg", caption="카메라 스캔 → 바로 송금", use_container_width=True)
            st.caption("예금주: 최*환") 
        else:
            st.error("QR 이미지가 없습니다. GitHub에 업로드해주세요.")

    st.markdown("---")

    # 2. 쿠팡 파트너스 (책 추천)
    st.info("📚 **워렌 버핏 방식을 따르고 싶다면 무조건 읽어야 하는 인생 책**")
    st.markdown("[👉 **'워렌 버핏 바이블 완결판' 최저가**](https://link.coupang.com/a/dz5HhD)")






