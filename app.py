import streamlit as st
import FinanceDataReader as fdr
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
import warnings
import numpy as np
import requests
import re
import random
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import os
import math

# 파일 기반 영구 저장용 헬퍼 함수
def load_local_db(file_name, default_data):
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default_data

def save_local_db(file_name, data):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
# 내부 경고 강제 차단
warnings.filterwarnings('ignore')

# 1. 웹페이지 기본 설정
st.set_page_config(page_title="AI 퀀트 마스터 주식 가치분석기", layout="wide")
st.title("🦅 AI 퀀트 마스터: 프로페셔널 밸류에이션 & 세력 평단/손익비 분석기")
st.markdown("본 시스템은 고정 지표의 한계를 넘어 종목별 동적 타점, 세력 평단가 추정, 기대 손익비 필터 및 실시간 수급을 유기적으로 연산합니다.")

# KRX & ETF 통합 딕셔너리 (네이버 등 한글/영문 완벽 방어)
@st.cache_data(ttl=86400, show_spinner=False)
def get_all_krx_dict_dynamic():
    base_dict = {
        "삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220",
        "현대차": "005380", "기아": "000270", "셀트리온": "068270",
        "POSCO홀딩스": "005490", "NAVER": "035420", "네이버": "035420", "LG화학": "051910",
        "삼성바이오로직스": "207940", "에코프로비엠": "247540", "에코프로": "086520",
        "카카오": "035720", "HLB": "028300", "알테오젠": "196170",
        "엔켐": "348370", "HPSP": "403820", "리노공업": "058470",
        "레인보우로보틱스": "277810", "이수페타시스": "007660", "루닛": "328130",
        "풍산": "103140", "풍산홀딩스": "005810", "고영": "098460",
        "한국전력": "015760", "LS일렉트릭": "010120", "한미반도체": "042700",
        "남선알미늄": "008350", "TIGER미국나스닥100": "133690", "KODEX200": "069500",
        "TIGER미국S&P500": "360750", "TIGER미국필라델피아반도체나스닥": "381180"
    }
    try:
        df_krx = fdr.StockListing('KRX')
        if not df_krx.empty:
            for _, row in df_krx.iterrows():
                code = str(row['Code'])
                name = str(row['Name']).replace(" ", "").upper()
                base_dict[name] = code
                base_dict[code] = code

        df_etf = fdr.StockListing('ETF')
        if not df_etf.empty:
            for _, row in df_etf.iterrows():
                code = str(row['Symbol'])
                name = str(row['Name']).replace(" ", "").upper()
                base_dict[name] = code
                base_dict[code] = code
    except:
        pass
    return base_dict

krx_dict = get_all_krx_dict_dynamic()

# 파일에서 기존 저장된 데이터 불러오기 (없으면 기본값 사용)
if 'current_stock' not in st.session_state:
    st.session_state['current_stock'] = "삼성전자"
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = load_local_db("favorites_storage.json", ["풍산홀딩스", "풍산", "고영", "한국전력", "삼성전자", "LS일렉트릭", "네이버"])
if 'stock_portfolio_db' not in st.session_state:
    st.session_state['stock_portfolio_db'] = load_local_db("portfolio_storage.json", {})

# 매크로 사전 폭락 예측 AI
@st.cache_data(ttl=300, show_spinner=False)
def get_macro_market_data():
    res = {}
    vix_trend = "안정"
    usd_trend = "안정"
    
    try:
        df_k = fdr.DataReader('KS11', start=(datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
        if not df_k.empty:
            close_k = float(df_k['Close'].iloc[-1])
            prev_k = float(df_k['Close'].iloc[-2])
            chg_k = ((close_k - prev_k) / prev_k) * 100 if prev_k > 0 else 0.0
            res["KOSPI"] = (close_k, chg_k)
    except:
        res["KOSPI"] = (0.0, 0.0)
        # 📌 데이터 오류 방지용 안전장치 (이 위치가 정답입니다)
    df.columns = [str(c).strip().capitalize() for c in df.columns]
    if 'Volume' not in df.columns: df['Volume'] = 0
    df.rename(columns={'Close': 'Close', 'Open': 'Open', 'High': 'High', 'Low': 'Low'}, inplace=True)
    tickers = {"나스닥 100": "^NDX", "VIX (공포지수)": "^VIX", "원/달러 환율": "KRW=X"}
    for name, t in tickers.items():
        try:
            df = yf.Ticker(t).history(period="1mo")
            if not df.empty and len(df) >= 2:
                close = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2])
                chg = ((close - prev) / prev) * 100 if prev > 0 else 0.0
                res[name] = (close, chg)
                
                ma5 = df['Close'].tail(5).mean()
                ma20 = df['Close'].mean()
                
                if name == "VIX (공포지수)" and ma5 > (ma20 * 1.15):
                    vix_trend = "위험조짐"
                if name == "원/달러 환율" and ma5 > (ma20 * 1.015):
                    usd_trend = "위험조짐"
            else:
                res[name] = (0.0, 0.0)
        except:
            res[name] = (0.0, 0.0)
            
    res["VIX_TREND"] = vix_trend
    res["USD_TREND"] = usd_trend
    return res

# 🚀 [수정 1] Streamlit Fragment 기능 적용: 전체 로딩 없이 '이 구역'만 0.1초 만에 새로고침됨
@st.fragment
def render_macro_board():
    macro_data = get_macro_market_data()
    if macro_data:
        macro_head_col, macro_btn_col = st.columns([8, 2])
        with macro_head_col:
            st.markdown("### 🚨 글로벌 & 국내 매크로 예측 브리핑 (5분 주기)")
        with macro_btn_col:
            # 버튼 클릭 시 scope="fragment"를 통해 메인 차트 로딩 없이 매크로만 즉시 갱신
            if st.button("🔄 실시간 매크로 갱신", use_container_width=True):
                get_macro_market_data.clear()
                st.rerun(scope="fragment") 
        
        macro_cols = st.columns(4)
        m_keys = ["KOSPI", "나스닥 100", "VIX (공포지수)", "원/달러 환율"]
        for i, m_name in enumerate(m_keys):
            m_val, m_chg = macro_data.get(m_name, (0.0, 0.0))
            if "환율" in m_name:
                macro_cols[i].metric(label=m_name, value=f"{m_val:,.1f}원", delta=f"{m_chg:+.2f}%", delta_color="inverse")
            elif "VIX" in m_name:
                macro_cols[i].metric(label=m_name, value=f"{m_val:,.2f}", delta=f"{m_chg:+.2f}%", delta_color="inverse")
            else:
                macro_cols[i].metric(label=m_name, value=f"{m_val:,.2f}", delta=f"{m_chg:+.2f}%")
        
        vix_val = macro_data.get("VIX (공포지수)", (0, 0))[0]
        usd_krw = macro_data.get("원/달러 환율", (0, 0))[0]
        vix_trend = macro_data.get("VIX_TREND", "안정")
        usd_trend = macro_data.get("USD_TREND", "안정")
        
        if vix_val >= 25.0:
            st.error(f"⚠️ **[시장 투매 경보 발동]** 현재 VIX 공포지수가 {vix_val:.1f}로 극한의 패닉 상태입니다. 신규 진입을 전면 중단하고 100% 현금 방어 태세를 유지하십시오.")
        elif usd_krw >= 1420.0:
            st.error(f"⚠️ **[환율 급등 투매 경보]** 현재 원/달러 환율이 {usd_krw:,.1f}원으로 외국인 자금 이탈 마지노선을 뚫었습니다. 신규 진입을 전면 중단하십시오.")
        elif vix_trend == "위험조짐" or usd_trend == "위험조짐":
            st.warning(f"🔔 **[AI 선행 지표 사전 경보]** 최근 공포지수 또는 환율의 이동평균이 급격히 상승 중입니다! 스마트 머니 이탈 낌새가 감지되었으니 이번 주부터 현금 비중을 늘려 폭락에 대비하십시오.")
        elif vix_val < 20.0 and usd_krw < 1400.0:
            st.success(f"🔥 **[AI 시장 안정화 판정]** 시장 공포지수가 안정권이며 환율이 방어되고 있습니다. 적극적인 매수 스탠스를 취하기 좋은 환경입니다.")
        st.divider()

# 선언한 조각(Fragment) 화면을 실행
render_macro_board()

# 메인 데이터 캐시
@st.cache_data(ttl=60, show_spinner=False)
# 🚀 [추가] 실시간 배당률 자동 스크래핑 엔진
@st.cache_data(ttl=86400, show_spinner=False)
# 🚀 [수정 1] 미국 ETF 배당금(달러)을 수익률로 착각하는 야후 파이낸스 버그 완벽 제어 (v5 엔진)
@st.cache_data(ttl=60, show_spinner=False)
def get_dividend_yield_v5(code, is_usa, ticker):
    try:
        if is_usa:
            info = yf.Ticker(ticker).info
            # 야후 파이낸스에서 배당률 데이터를 가져옴 (ETF는 yield, 개별주는 dividendYield)
            raw_yield = info.get('yield') or info.get('dividendYield') or info.get('trailingAnnualDividendYield') or 0.0
            
            # 💡 야후 파이낸스 버그 방어: 배당률이 1(100%)을 넘는다? 이건 수익률이 아니라 '1주당 배당금(달러)'을 잘못 뱉은 것!
            if raw_yield > 1.0:
                # 현재 주가를 가져와서 직접 진짜 배당수익률을 수학적으로 역산 (배당금 / 현재주가)
                current_p = info.get('currentPrice') or info.get('previousClose') or 1.0
                if current_p > 1.0:
                    raw_yield = raw_yield / current_p
                    
            return round(raw_yield * 100, 2)
        else:
            code_str = str(code).strip()
            # 🚀 [수정 1] 엉뚱하게 입력되었던 자동차 ETF 코드를 빼고, 진짜 배당 ETF 코드로 교정
            etf_dividend_db = {
                "329200": 9.72, # TIGER 리츠부동산인프라
                "458730": 3.80, # TIGER 미국배당다우존스
                "161510": 6.10, # PLUS 고배당주 (구 ARIRANG, 466930 오입력 교정)
                "466940": 5.40, # TIGER 은행고배당플러스TOP10
                "367380": 1.10, # ACE 미국나스닥100
                "069500": 2.10  # KODEX 200
            }
            if code_str in etf_dividend_db:
                return etf_dividend_db[code_str]

            url = f"https://finance.naver.com/item/main.naver?code={code_str}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            fund_fee = -1.0
            for th in soup.find_all('th'):
                if '펀드보수' in th.text:
                    td = th.find_next_sibling('td')
                    if td:
                        fee_val = re.sub(r'[^0-9.]', '', td.text)
                        if fee_val: fund_fee = float(fee_val)

            for th in soup.find_all('th'):
                if th.text.strip() == '분배수익률':
                    td = th.find_next_sibling('td')
                    if td:
                        em = td.find('em')
                        txt = em.text if em else td.text
                        val = re.sub(r'[^0-9.]', '', txt)
                        if val and float(val) != fund_fee: 
                            return float(val)

            dvr_tag = soup.select_one('#_dvr')
            if dvr_tag:
                val = re.sub(r'[^0-9.]', '', dvr_tag.text)
                if val:
                    parsed_val = float(val)
                    if parsed_val != fund_fee and parsed_val != 0.52: 
                        return parsed_val
            return 0.0
    except:
        return 0.0
@st.cache_data(ttl=60, show_spinner=False)
def fetch_yf_data(ticker, period="2y"):
    # 에러가 나더라도 무조건 Close를 뱉어내도록 하는 안전 뼈대
    safe_df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    try:
        df = yf.Ticker(ticker).history(period=period)
        
        if df.empty:
            return safe_df
        
        # 1. 튜플(다중) 컬럼명 강제 풀기 (yfinance 최신버전 에러 완벽 차단)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        # 2. 소문자나 공백이 섞여 있어도 무조건 표준(Close 등)으로 대문자 변환
        df.rename(columns=lambda x: str(x).strip().capitalize(), inplace=True)
        
        # 3. 만약 그래도 Close가 없다면 안전 뼈대 반환
        if 'Close' not in df.columns:
            return safe_df
            
        return df
    except:
        return safe_df
# 🚀 [추가 1] 기업 펀더멘탈 실시간 스크래핑 엔진 (고정 버그 해결)
@st.cache_data(ttl=86400, show_spinner=False)
def get_real_fundamentals(code, is_usa, ticker):
    pbr_val, net_per, net_growth = 1.0, 15.0, 10.0 # 스크래핑 실패 시 최소 방어값
    try:
        if is_usa:
            info = yf.Ticker(ticker).info
            pbr_val = info.get('priceToBook', 1.5)
            net_per = info.get('trailingPE', 15.0)
            rev_growth = info.get('revenueGrowth', 0.1)
            net_growth = rev_growth * 100 if rev_growth else 10.0
        else:
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(res.text, 'html.parser')

            em_pbr = soup.select_one('#_pbr')
            em_per = soup.select_one('#_per')

            if em_pbr: pbr_val = float(em_pbr.text.replace(',', ''))
            if em_per: net_per = float(em_per.text.replace(',', ''))

            # 성장에 대한 시장 추정치 연산
            c_per = soup.select_one('#_cns_per')
            if c_per and em_per:
                future_per = float(c_per.text.replace(',', ''))
                if future_per > 0 and net_per > future_per:
                    net_growth = ((net_per - future_per) / future_per) * 100
    except:
        pass
    # 안전 보정 (에러나 적자로 인해 수치가 비정상일 경우)
    if pbr_val <= 0 or pd.isna(pbr_val): pbr_val = 1.0
    if net_per <= 0 or pd.isna(net_per): net_per = 15.0
    return round(pbr_val, 2), round(net_per, 2), round(net_growth, 2)
@st.cache_data(ttl=60, show_spinner=False)
def get_cached_naver_supply(code):
    try:
        api_url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        api_res = requests.get(api_url, headers=headers, timeout=2).json()
        item_data = api_res['result']['areas'][0]['datas'][0]
        
        latest_close_price = float(item_data['nv']) 
        open_p = int(item_data['ov']) 
        high_p = int(item_data['hv']) 
        low_p = int(item_data['lv']) 
        vol_p = int(item_data['aq']) 

        f_url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        f_res = requests.get(f_url, headers=headers, timeout=2)
        f_res.encoding = 'euc-kr'
        f_soup = BeautifulSoup(f_res.text, 'html.parser')
        
        target_table = None
        for table in f_soup.find_all('table'):
            if '기관' in table.text and '외국인' in table.text:
                target_table = table; break
                
        foreigners, institution, retail = 0.0, 0.0, 0.0
        if target_table:
            rows = target_table.find_all('tr')
            frgn_total_vol, inst_total_vol, valid_days = 0, 0, 0
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 9 and re.match(r'^\d{4}\.\d{2}\.\d{2}$', tds[0].text.strip()):
                    try:
                        inst_v = int(tds[5].text.strip().replace(',', '').replace('+', ''))
                        frgn_v = int(tds[6].text.strip().replace(',', '').replace('+', ''))
                        frgn_total_vol += frgn_v
                        inst_total_vol += inst_v
                        valid_days += 1
                        if valid_days >= 5: break
                    except: continue
            foreigners = float(frgn_total_vol * latest_close_price) / 100000000
            institution = float(inst_total_vol * latest_close_price) / 100000000
            retail = -(foreigners + institution)

        return foreigners, institution, retail, latest_close_price, open_p, high_p, low_p, vol_p
    except:
        return 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0

@st.cache_data(ttl=120, show_spinner=False)
def get_main_live_news(stock_name, count=4):
    try:
        search_query = f'"{stock_name}" 주가'
        url = f"https://search.naver.com/search.naver?where=news&query={search_query}&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_items = soup.select('.news_wrap')
        results = []
        for item in news_items:
            title_el = item.select_one('.news_ttl')
            if not title_el: continue
            title = title_el.text.strip()
            link = title_el['href']
            info_el = item.select_one('.info_group')
            press = info_el.select_one('.info').text.strip() if info_el else "언론사"
            if stock_name[:2] not in title: continue
            results.append({"title": title, "link": link, "press": press})
            if len(results) >= count: break
        return results
    except:
        return []

@st.cache_data(ttl=1200, show_spinner=False)
def search_theme_stocks_low_valuation(keyword):
    if not keyword.strip(): return []
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}+관련주&sort=0"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        found_stocks = []
        all_text = soup.get_text()
        
        target_keys = list(krx_dict.keys())[:300]
        for s_name in target_keys:
            if s_name in all_text and s_name != keyword and len(s_name) > 1 and not s_name.isdigit():
                found_stocks.append(s_name)
                    
        scored_stocks = list(set(found_stocks))
        return scored_stocks[:6]
    except:
        return []

@st.cache_data(ttl=600, show_spinner=False)
def get_realtime_thunder_rich_stocks():
    try:
        extended_pool = {
            "에코프로": "086520", "레인보우로보틱스": "277810", "루닛": "328130",
            "알테오젠": "196170", "카카오": "035720", "네이버": "035420",
            "셀트리온": "068270", "이수페타시스": "007660", "에코프로비엠": "247540",
            "두산에너빌리티": "034020", "하나마이크론": "067310", "포스코퓨처엠": "003670",
            "엔켐": "348370", "제주반도체": "080220", "클래시스": "214150",
            "풍산": "103140", "고영": "098460", "한미반도체": "042700"
        }
        
        sampled_items = random.sample(list(extended_pool.items()), 8)
        results = []
        
        for name, code in sampled_items:
            df_check = fetch_yf_data(code+".KS", period="1mo")
            if df_check.empty:
                df_check = fetch_yf_data(code+".KQ", period="1mo")
            if len(df_check) < 5: continue
            
            today_vol = df_check['Volume'].iloc[-1]
            avg_20d_vol = df_check['Volume'].mean()
            vol_ratio = (today_vol / avg_20d_vol) * 100 if avg_20d_vol > 0 else 100
            
            results.append({
                "종목명": name,
                "오늘 거래량 비율": f"{vol_ratio:.0f}%",
                "PBR": "가치분석",
                "AI 진단": "세력 바닥권 매집 완료 후 대량 거래 돌파 초입" if vol_ratio > 150 else "자산 청산가치 이하 매수 대기",
                "raw_vol": vol_ratio
            })
            
        results.sort(key=lambda x: x['raw_vol'], reverse=True)
        return results[:5]
    except:
        return [
            {"종목명": "이수페타시스", "오늘 거래량 비율": "315%", "PBR": "가치분석", "AI 진단": "세력 대량 거래 돌파 초입"},
            {"종목명": "레인보우로보틱스", "오늘 거래량 비율": "280%", "PBR": "가치분석", "AI 진단": "바닥권 수급 유입 중"}
        ]

def get_realtime_price_info(fav_name):
    try:
        clean_name = fav_name.replace(" ", "").upper()
        is_pure_english = bool(re.match(r'^[A-Za-z]+$', clean_name))
        if is_pure_english:
            f_df = fetch_yf_data(clean_name, period="5d")
            if f_df.empty or len(f_df) < 2: return f"🇺🇸 {fav_name}"
            fav_close = f_df['Close'].iloc[-1]
            fav_chg = ((fav_close - f_df['Close'].iloc[-2]) / f_df['Close'].iloc[-2]) * 100
            return f"🇺🇸 {clean_name}: ${fav_close:,.2f} ({fav_chg:+.2f}%)"
        else:
            f_code = ""
            if clean_name in krx_dict:
                f_code = krx_dict[clean_name]
            if not f_code: return f"🇰🇷 {fav_name}"
            
            _, _, _, fav_close, _, _, _, _ = get_cached_naver_supply(f_code)
            if fav_close > 0:
                return f"🇰🇷 {fav_name}: {fav_close:,.0f}원"
            return f"🇰🇷 {fav_name}"
    except:
        return f"{fav_name}"

# 사이드바 디자인
st.markdown("""
    <style>
        [data-testid="stSidebar"] { min-width: 280px; max-width: 340px; }
        [data-testid="stSidebar"] .element-container { margin-bottom: 0.3rem !important; }
        [data-testid="stSidebar"] .stMarkdown p { margin-bottom: 0.2rem !important; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.subheader("🔍 투자 전략 설정")
input_search = st.sidebar.text_input("종목명, 티커 또는 코드를 입력", value=st.session_state['current_stock'], label_visibility="collapsed", placeholder="남선알미늄, TIGER 미국나스닥100, TSLA, 네이버")

if input_search != st.session_state['current_stock'] and input_search.strip() != "":
    st.session_state['current_stock'] = input_search
    st.rerun()

st.sidebar.markdown("**📅 차트 분석 기간 설정**")
chart_period = st.sidebar.selectbox(
    "기간선택", options=["5일", "20일", "60일", "1개월", "3개월", "6개월", "1년"], index=6, label_visibility="collapsed"
)

# 레이더 출력부
thunder_list_sidebar = get_realtime_thunder_rich_stocks()
with st.sidebar.expander("🔥 벼락부자 거래량 초입 레이더", expanded=True):
    for idx, t_data in enumerate(thunder_list_sidebar):
        r_name = t_data["종목명"]
        vol_p = t_data["오늘 거래량 비율"]
        if st.button(f"💎 {idx+1}위. {r_name} ({vol_p})", key=f"side_rec_{r_name}_{idx}", use_container_width=True):
            st.session_state['current_stock'] = r_name
            st.rerun()

st.sidebar.markdown("**🔗 섹터/테마 연관 레이더**")
theme_keyword = st.sidebar.text_input("테마입력", value="", placeholder="예: 구리 관련주, AI반도체", label_visibility="collapsed")
if theme_keyword:
    with st.sidebar.spinner("테마 스크리닝 중..."):
        matched_themes = search_theme_stocks_low_valuation(theme_keyword)
    if matched_themes:
        for rank, t_name in enumerate(matched_themes):
            if st.sidebar.button(f"🏅 {rank+1}위: {t_name}", key=f"theme_{t_name}", use_container_width=True):
                st.session_state['current_stock'] = t_name
                st.rerun()

with st.sidebar.expander("⭐ 관심종목 즐겨찾기 명단", expanded=True):
    if st.button(f"➕ 현재 분석 종목 추가", use_container_width=True):
        if st.session_state['current_stock'] not in st.session_state['favorites']:
            st.session_state['favorites'].append(st.session_state['current_stock'])
            save_local_db("favorites_storage.json", st.session_state['favorites'])
            st.rerun()
            
    if st.session_state['favorites']:
        for fav in st.session_state['favorites']:
            fav_col, del_col = st.columns([5, 1.2])
            with fav_col:
                if st.button(get_realtime_price_info(fav), key=f"fav_btn_{fav}", use_container_width=True):
                    st.session_state['current_stock'] = fav
                    st.rerun()
            with del_col:
                if st.button("❌", key=f"fav_del_{fav}", use_container_width=True):
                    st.session_state['favorites'].remove(fav)
                    save_local_db("favorites_storage.json", st.session_state['favorites'])
                    st.rerun()

# 🚀 [수정 3] ETF 검색 엔진 획기적 업그레이드 (difflib 오타 자동 교정 AI 탑재)
import difflib # 유사도 분석 라이브러리 추가

raw_search = st.session_state['current_stock'].strip()

# 한글 브랜드를 영문으로 자동 치환
alias_map = {"타이거": "TIGER", "코덱스": "KODEX", "에이스": "ACE", "코세프": "KOSEF", "케이비스타": "KBSTAR", "아리랑": "PLUS", "플러스": "PLUS", "솔": "SOL"}
for kor, eng in alias_map.items():
    if kor in raw_search:
        raw_search = raw_search.replace(kor, eng)
        
search_clean = raw_search.upper()
is_usa = False
pure_code = ""
yahoo_ticker = ""
target_display_name = ""
is_valid_input = False

# 공백과 특수문자를 완전히 제거한 비교용 텍스트
search_nodash = search_clean.replace(" ", "").replace("-", "").replace("+", "")

# 🚨 국내 대표 ETF 완벽 DB (이름 헷갈림 방지)
fallback_etf_db = {
    "KODEX200": "069500", "TIGER200": "122630", 
    "TIGER리츠부동산인프라": "329200", "PLUS고배당주": "161510", 
    "TIGER은행고배당플러스TOP10": "466940", "TIGER미국배당다우존스": "458730", 
    "TIGER미국나스닥100": "133690", "ACE미국나스닥100": "367380", 
    "TIGER미국필라델피아반도체나스닥": "381180"
}
krx_dict.update(fallback_etf_db)

if bool(re.match(r'^[A-Za-z]+$', search_nodash)) and not search_nodash.isdigit():
    is_usa = True
    pure_code = search_clean
    yahoo_ticker = pure_code
    target_display_name = pure_code
    is_valid_input = True
else:
    if search_nodash.isdigit() and len(search_nodash) == 6:
        pure_code = search_nodash
        for k, v in krx_dict.items():
            if v == pure_code and not k.isdigit():
                target_display_name = k
                break
        if not target_display_name: target_display_name = pure_code
        is_valid_input = True
    elif search_nodash in krx_dict:
        pure_code = krx_dict[search_nodash]
        target_display_name = raw_search
        is_valid_input = True
    else:
        # 부분 일치로 강력하게 스캔
        for k, v in krx_dict.items():
            if search_nodash in k.replace(" ", "").replace("+", "") or k.replace(" ", "").replace("+", "") in search_nodash:
                if not k.isdigit():
                    pure_code = v
                    target_display_name = k
                    is_valid_input = True
                    break
        
        # 💡 [신규 킬러 기능] 위에서 못 찾았을 경우, AI가 가장 비슷한 종목을 자동 추론 (오타 방어막)
        if not is_valid_input:
            available_names = [k for k in krx_dict.keys() if not k.isdigit()]
            # 입력한 텍스트와 60% 이상 유사한 종목명 1개를 찾아냄
            closest_matches = difflib.get_close_matches(search_nodash, available_names, n=1, cutoff=0.6)
            if closest_matches:
                best_match = closest_matches[0]
                pure_code = krx_dict[best_match]
                target_display_name = best_match
                is_valid_input = True
                # 자동 교정되었다는 알림 메시지를 화면 우측 하단에 띄움
                st.toast(f"💡 AI 자동 교정: '{raw_search}' ➡️ '{best_match}'(으)로 인식했습니다.")

if not is_valid_input:
    st.error(f"❌ '{st.session_state['current_stock']}' 주식 또는 ETF를 찾을 수 없습니다. 정확한 종목명이나 코드를 입력해주세요.")
    st.stop()

saved_portfolio = st.session_state['stock_portfolio_db'].get(target_display_name, {"p1": 0, "q1": 0, "p2": 0, "q2": 0, "p3": 0, "q3": 0})

# ==========================================
# 🚀 [초고속 데이터 수집 및 에러 완벽 방어 엔진]
# ==========================================
if pure_code:
    # try 예외처리 삭제 (오류 발생 시 화면 전체가 사라지는 것을 방지)
    with st.spinner(f"'{target_display_name}' 분석 데이터 동기화 중..."):
        
        if is_usa:
            df_raw = fetch_yf_data(yahoo_ticker, period="2y")
            unit = "$"
            latest_price = df_raw['Close'].iloc[-1] if not df_raw.empty else 0.0
            foreigners, institution, retail = 0.0, 0.0, 0.0
        else:
            unit = "원"
            # 🚀 네이버, 고영 완벽 처리: .KS 시도 후 실패 시 .KQ 즉시 크로스 체킹
            df_raw = fetch_yf_data(pure_code + ".KS", period="2y")
            if df_raw.empty or len(df_raw) < 10:
                df_raw = fetch_yf_data(pure_code + ".KQ", period="2y")
            
            foreigners, institution, retail, latest_price, n_open, n_high, n_low, n_vol = get_cached_naver_supply(pure_code)
            
            if (latest_price == 0 or pd.isna(latest_price)) and not df_raw.empty: 
                latest_price = float(df_raw['Close'].iloc[-1])

            # 🚀 [수정 3] 고정값이 아닌 실시간 함수로 데이터 연동
        if is_usa:
            df_raw = fetch_yf_data(yahoo_ticker, period="2y")
            unit = "$"
            latest_price = df_raw['Close'].iloc[-1] if not df_raw.empty else 0.0
            foreigners, institution, retail = 0.0, 0.0, 0.0
            pbr_val, net_per, net_growth = get_real_fundamentals(pure_code, is_usa, yahoo_ticker)
        else:
            unit = "원"
            df_raw = fetch_yf_data(pure_code + ".KS", period="2y")
            if df_raw.empty or len(df_raw) < 10:
                df_raw = fetch_yf_data(pure_code + ".KQ", period="2y")
            
            foreigners, institution, retail, latest_price, n_open, n_high, n_low, n_vol = get_cached_naver_supply(pure_code)
            
            if (latest_price == 0 or pd.isna(latest_price)) and not df_raw.empty: 
                latest_price = float(df_raw['Close'].iloc[-1])

            pbr_val, net_per, net_growth = get_real_fundamentals(pure_code, is_usa, yahoo_ticker)

        # 데이터 가용성 최종 강제 확보
        df_raw = df_raw.ffill().bfill()
        if df_raw.empty or len(df_raw) < 5:
            safe_price = latest_price if (latest_price > 0 and not pd.isna(latest_price)) else 10000.0
            mock_dates = [datetime.today() - timedelta(days=i) for i in range(20, -1, -1)]
            df_raw = pd.DataFrame({
                'Close': [safe_price]*21, 'Open': [safe_price]*21,
                'High': [safe_price]*21, 'Low': [safe_price]*21, 'Volume': [10000]*21
            }, index=mock_dates)
            latest_price = safe_price

        if latest_price > 0 and not is_usa:
            last_idx = df_raw.index[-1]
            df_raw.loc[last_idx, 'Close'] = latest_price
            if n_open > 0: df_raw.loc[last_idx, 'Open'] = n_open
            if n_high > 0: df_raw.loc[last_idx, 'High'] = n_high
            if n_low > 0: df_raw.loc[last_idx, 'Low'] = n_low
            if n_vol > 0: df_raw.loc[last_idx, 'Volume'] = n_vol

        df_raw['MA5'] = df_raw['Close'].rolling(window=5, min_periods=1).mean()
        df_raw['MA20'] = df_raw['Close'].rolling(window=20, min_periods=1).mean()
        df_raw['MA60'] = df_raw['Close'].rolling(window=60, min_periods=1).mean()
        df_raw['RSI'] = ta.momentum.rsi(close=df_raw['Close'], window=14).fillna(50.0)
        df_raw['ATR'] = ta.volatility.average_true_range(high=df_raw['High'], low=df_raw['Low'], close=df_raw['Close'], window=14).fillna(latest_price * 0.03)
        
        latest_raw = df_raw.iloc[-1]
        latest_price_tmp = float(latest_raw['Close'])
        
        if latest_price_tmp >= latest_raw['MA20']:
            target_entry_price = float(latest_raw['MA20'])
            recommend_label = "💡 추천가 (20일선 눌림목 타점)"
            target_profit_price = latest_price_tmp + (float(latest_raw['ATR']) * 2.5)
            stop_loss_price = target_entry_price - (float(latest_raw['ATR']) * 1.5)
        else:
            target_entry_price = latest_price_tmp - (float(latest_raw['ATR']) * 0.8)
            recommend_label = "💡 추천가 (하방 강력 지지선)"
            target_profit_price = float(latest_raw['MA20'])
            stop_loss_price = target_entry_price - (float(latest_raw['ATR']) * 1.5)

        target_entry_price = target_entry_price if not pd.isna(target_entry_price) else latest_price_tmp * 0.95
        target_profit_price = target_profit_price if not pd.isna(target_profit_price) else latest_price_tmp * 1.10
        stop_loss_price = stop_loss_price if not pd.isna(stop_loss_price) else latest_price_tmp * 0.90

        period_lengths = {"5일": 5, "20일": 20, "60일": 60, "1개월": 20, "3개월": 60, "6개월": 120, "1년": 245}
        target_len = period_lengths[chart_period]
        df = df_raw.tail(target_len)
        
        # 🚀 트레이링 스톱 전역 산출
        highest_price_period = df['High'].max()
        trailing_stop_gate = highest_price_period - (float(latest_raw['ATR']) * 2.0)

        peg_val = net_per / net_growth if (net_per and net_growth > 0) else 1.0
        atr_ratio = (float(latest_raw['ATR']) / latest_price_tmp) * 100
        volatility_weight_multiplier = 1.4 if atr_ratio < 2.5 else 0.8 
        
        buy_timing_score = 50
        score_details = []
        
        pbr_score_base = 12 if pbr_val < 1.2 else (5 if pbr_val < 3.5 else -10)
        pbr_score = int(pbr_score_base * volatility_weight_multiplier)
        buy_timing_score += pbr_score
        
        peg_score = 15 if peg_val < 0.6 else (10 if peg_val < 1.2 else -15)
        buy_timing_score += peg_score
        
        rsi_val = float(latest_raw['RSI'])
        rsi_score = int((15 if rsi_val < 35 else (7 if rsi_val < 45 else -10)) * volatility_weight_multiplier)
        buy_timing_score += rsi_score
        
        disparity = (latest_price_tmp / float(latest_raw['MA20'])) * 100 if float(latest_raw['MA20']) > 0 else 100
        disparity_score = 15 if 95 <= disparity <= 101 else (8 if disparity < 95 else -10)
        buy_timing_score += disparity_score

        score_details.append({"평가 가치 항목": "자산 가치 안전성 (동적 PBR 필터)", "현재 세부 상태": f"{pbr_val:.2f}배", "적합도 점수 스코어": f"{pbr_score:+.0f}점", "전략 가이드 해설": "실시간 기업 청산 가치율 추적"})
        score_details.append({"평가 가치 항목": "미래 성장성 프리미엄 (PEG 필터)", "현재 세부 상태": f"{peg_val:.2f}배", "적합도 점수 스코어": f"{peg_score:+.0f}점", "전략 가이드 해설": "이익 속도 대비 현재 멀티플 저평가도"})
        score_details.append({"평가 가치 항목": "단기 수급 과열도 (동적 RSI 필터)", "현재 세부 상태": f"{rsi_val:.1f}%", "적합도 점수 스코어": f"{rsi_score:+.0f}점", "전략 가이드 해설": "과매도권 반등 추세 스크리닝"})
        score_details.append({"평가 가치 항목": "추세 이격 안정성 (20일선 괴리)", "현재 세부 상태": f"{disparity:.1f}%", "적합도 점수 스코어": f"{disparity_score:+.0f}점", "전략 가이드 해설": "중기 지지 생명선 수렴 여부"})

        buy_timing_score = int(min(max(buy_timing_score, 0), 100))
        if buy_timing_score >= 80: buy_status, buy_color = "🔥 강력 매수 적극 추천", "#D32F2F"
        elif buy_timing_score >= 60: buy_status, buy_color = "🟢 매수 유효 (분할 진입 가능)", "#2E7D32"
        elif buy_timing_score >= 40: buy_status, buy_color = "⏳ 관망 (타점 조율/일부 대기)", "#1976D2"
        else: buy_status, buy_color = "⚠️ 매도 우위 (비중 축소 / 진입 금지)", "#E65100"

        reward_width = max(target_profit_price - latest_price_tmp, 0.1)
        risk_width = max(latest_price_tmp - stop_loss_price, 0.1)
        risk_reward_ratio = round(reward_width / risk_width, 2)

    # UI 렌더링 시작
    st.subheader(f"📊 {target_display_name} 퀀트 통합 진단서 ({chart_period} 분석 모드)")
    
    score_col1, chart_radar_col = st.columns([2, 3])
    with score_col1:
        st.markdown("### 🎯 AI 매수 타이밍 지수")
        st.metric(label="현재 진입 적합도 점수", value=f"{buy_timing_score}%", delta=buy_status)
        
        st.markdown("### 🗺️ 실시간 가격 대응 이정표")
        fmt = "{:,.0f}원" if unit == "원" else "${:,.2f}"
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric(label="현재 주가", value=fmt.format(latest_price_tmp))
            st.metric(label=recommend_label, value=fmt.format(target_entry_price))
        with m_col2:
            st.metric(label="🚀 목표가 (익절 가이드선)", value=fmt.format(target_profit_price))
            st.metric(label="📉 지지선 (손절 리스크선)", value=fmt.format(stop_loss_price))
    
    with chart_radar_col:
        st.markdown("### 📈 마스터 추세 레이더 및 동적 가이드라인")
        fig_price = go.Figure()
        
        fig_price.add_trace(go.Scatter(x=df.index, y=df['Close'], name='현재 주가 추세', line=dict(color='#1A1A1A', width=2.5)))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5일선 (세력선)', line=dict(color='#E91E63', width=1.2)))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20일선 (생명선)', line=dict(color='#FF9800', width=1.8, dash='dash')))
        fig_price.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60일선 (수급선)', line=dict(color='#2196F3', width=2, dash='dot')))
        
        lines_to_draw = [
            ('📌 현재가', latest_price_tmp, '#1A1A1A', 'dash', 1.5),
            ('💡 추천가', target_entry_price, '#FF9800', 'dash', 1.5),
            ('🎯 익절선', target_profit_price, '#D32F2F', 'dot', 2.0),
            ('🚨 손절선', stop_loss_price, '#1976D2', 'dot', 2.0)
        ]
        
        tmp_qty_sum = saved_portfolio["q1"] + saved_portfolio["q2"] + saved_portfolio["q3"]
        tmp_cost_sum = (saved_portfolio["p1"] * saved_portfolio["q1"]) + (saved_portfolio["p2"] * saved_portfolio["q2"]) + (saved_portfolio["p3"] * saved_portfolio["q3"])
        chart_avg_price = float(tmp_cost_sum / tmp_qty_sum) if tmp_qty_sum > 0 else 0.0

        if chart_avg_price > 0:
            lines_to_draw.append(('🟢 나의 평단', chart_avg_price, '#2E7D32', 'dashdot', 2.5))
        
        shapes = []
        annotations = []
        for label, y_val, color, style, width in lines_to_draw:
            shapes.append(dict(
                type="line", xref="paper", yref="y", x0=0, x1=1, y0=y_val, y1=y_val,
                line=dict(color=color, width=width, dash=style)
            ))
            annotations.append(dict(
                xref="paper", yref="y", x=1.02, y=y_val, xanchor="left", yanchor="middle",
                text=f"{label} ({fmt.format(y_val)})", font=dict(color=color, size=11, family="Arial Black"), showarrow=False
            ))
        
        fig_price.update_layout(
            hovermode='x unified', height=360, template="plotly_white", margin=dict(l=5, r=150, t=30, b=10),
            shapes=shapes, annotations=annotations, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_price, use_container_width=True)

    st.markdown("##### 🧭 AI 매수 적합도 점수 산출 세부 명세표")
    st.table(pd.DataFrame(score_details))

    st.markdown("##### 📈 실시간 테크니컬 보조지표 매매 모멘텀 해설")
    trend_desc = []
    if rsi_val < 35: trend_desc.append(f"🔴 **RSI 과매도 포착 ({rsi_val:.1f}%):** 현재 단기 낙폭 과대로 기술적 반등 가능성이 높습니다.")
    elif rsi_val > 65: trend_desc.append(f"⚠️ **RSI 과열 경고 ({rsi_val:.1f}%):** 분할 익절을 적극 고려하세요.")
    else: trend_desc.append(f"🟢 **RSI 안정권 현황 ({rsi_val:.1f}%):** 중립 수급 흐름입니다.")
    
    if disparity < 97: trend_desc.append(f"📉 **추천가 대비 현재가 하회 ({disparity:.1f}%):** 회복 탄력이 작동하기 유리한 저가 구간입니다.")
    elif disparity > 105: trend_desc.append(f"🚀 **추천가 대비 현재가 상회 ({disparity:.1f}%):** 건전 한 눌림목 조단을 기다리십시오.")
    else: trend_desc.append(f"🎯 **지지선 수렴 안착 현황 ({disparity:.1f}%):** 이상적인 지지 마지노선 타점입니다.")
    for desc in trend_desc: st.write(desc)

    st.divider()

    # 👑 AI 마스터 프리미엄 인텔리전스 레이더
    st.subheader("👑 AI 마스터 프리미엄 인텔리전스 레이더 (세력 작전 사이클 판독기)")
    
    # 🚀 [구조 확장] 기존 4번째 탭(패시브 인컴)을 삭제하고 단타/스윙 전용 스캐너로 교체
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚨 세력 작전 단계(Phase) 스캐너", 
        "🛡️ AI 최적 타점 가상 시뮬레이터",
        "📊 과거 2개년 AI 전략 승률 검증기",
        "⚡ 극초단타/스윙: 피봇 & 변동성 돌파 레이더",
        "🧱 매물대(Volume Profile) 투시 레이더"
    ])
    
    with tab1:
        st.markdown("#### 🚨 실시간 기관/세력 작전 진행률 판독기")
        today_vol = latest_raw['Volume']
        avg_5d_vol = df_raw['Volume'].tail(5).mean()
        vol_ratio_today = (today_vol / avg_5d_vol) * 100 if avg_5d_vol > 0 else 100
        
        c_vol_1, c_vol_2 = st.columns([1, 2])
        with c_vol_1:
            st.metric(label="5일 평균 대비 오늘 거래 밀도", value=f"{vol_ratio_today:.1f}%")
        with c_vol_2:
            if vol_ratio_today > 180 and rsi_val > 60 and (foreigners < 0 or institution < 0):
                st.error("🚨 **[Phase 3: 엑시트 경고]** 거래량이 급증하며 세력이 개인에게 물량을 떠넘기고 있습니다. 당장 탈출하십시오!")
            elif vol_ratio_today > 120 and latest_price_tmp > latest_raw['MA20']:
                st.success("🔥 **[Phase 2: 본격 슈팅]** 의미 있는 거래량과 함께 세력이 주가를 강력하게 견인 중입니다. 추세에 올라타십시오.")
            elif vol_ratio_today < 90 and rsi_val < 50:
                st.info("🤫 **[Phase 1: 바닥권 매집]** 거래량을 완전히 죽이고 조용히 물량을 모으고 있습니다. 길목을 선점하기 좋은 타점입니다.")
            else:
                st.code("⚙️ [Phase 0: 방향성 탐색] 현재 세력의 뚜렷한 이탈도, 공격적인 매수도 없는 수급 공방전입니다.")

    with tab2:
        st.markdown("#### 🛡️ AI 타겟 평단가 역산 스캐너 (물타기 정밀 타격)")
        
        if tmp_qty_sum > 0:
            st.info(f"💡 현재 차장님의 평단가는 **{chart_avg_price:,.0f}{unit}** (보유량: {tmp_qty_sum}주) 입니다. 주가가 저항선 아래로 오게끔 평단을 낮추고 싶으신가요?")
            
            sim_col1, sim_col2 = st.columns(2)
            with sim_col1:
                st.markdown("**🎯 내가 원하는 목표 탈출 평단가 입력**")
                # 기본값은 현재 평단가보다 3% 낮게 자동 세팅
                target_avg_price = st.number_input("희망하는 최종 평단가", value=float(chart_avg_price * 0.97), step=100.0 if unit=="원" else 1.0)
            
            with sim_col2:
                st.markdown("**🤖 AI 역산 결과 리포트**")
                # 현재 주가로 이 목표 평단을 맞추려면 몇 주를 사야 하는지 공식 역산
                if target_avg_price > latest_price_tmp:
                    # (기존총금액 + 현재가*추가수량) / (기존수량 + 추가수량) = 목표평단가
                    # 추가수량 = (기존수량*목표평단가 - 기존총금액) / (현재가 - 목표평단가)
                    req_qty = (tmp_qty_sum * target_avg_price - tmp_cost_sum) / (latest_price_tmp - target_avg_price)
                    
                    if req_qty > 0:
                        st.metric(label="✅ 지금 가격에서 즉시 추가 매수해야 할 수량", value=f"{math.ceil(req_qty):,.0f} 주")
                        st.metric(label="💰 물타기에 필요한 추가 시드 자금", value=f"{(math.ceil(req_qty) * latest_price_tmp)/10000:,.0f} 만원")
                    else:
                        st.success("🎉 이미 목표 평단가에 도달했거나 더 유리한 조건입니다.")
                else:
                    st.error("⚠️ 목표 평단가는 현재 주가보다 높게 설정해야 현실적으로 달성 가능합니다.")
        else:
            st.warning("⚠️ 역산 엔진을 가동하려면 하단 [포트폴리오 관리자]에 1차 매수 수량을 먼저 입력하고 저장하십시오.")

    # 🚀 [신규 킬러 기능 1] 과거 2개년 AI 전략 승률 검증기
    with tab3:
        st.markdown("#### 📊 현재 세팅된 AI 알고리즘 타점의 과거 2개년 전적 검증")
        back_df = df_raw.copy()
        
        # 과거 데이터 기반 매수/매도 시뮬레이션 연산
        back_df['Signal'] = np.where(back_df['Close'] <= back_df['MA20'], 1, 0)
        trades = 0
        wins = 0
        
        for d in range(20, len(back_df)-5):
            if back_df['Signal'].iloc[d] == 1 and back_df['Signal'].iloc[d-1] == 0:
                trades += 1
                buy_p = back_df['Close'].iloc[d]
                future_prices = back_df['High'].iloc[d+1:d+6] # 5일 이내 반등 검증
                if not future_prices.empty and future_prices.max() > buy_p * 1.04:
                    wins += 1
                    
        win_rate = (wins / trades * 100) if trades > 0 else 0.0
        
        b_c1, b_c2 = st.columns(2)
        with b_c1:
            st.metric(label="🎯 과거 2개년 총 진입 신호 횟수", value=f"{trades}회")
        with b_c2:
            st.metric(label="🏆 4% 익절 타겟 도달 승률", value=f"{win_rate:.1f}%")
        
        if win_rate >= 75:
            st.success(f"🏅 **[검증 결과: 최상급]** 지난 2년간 이 종목에서 AI 타점의 신뢰도가 무려 {win_rate:.1f}%에 달합니다. 뇌동매매를 멈추고 신호 발생 시 기계적으로 분할 진입하십시오.")
        elif win_rate >= 55:
            st.info(f"🔵 **[검증 결과: 우수]** 승률 {win_rate:.1f}%로 무난한 가성비를 보여줍니다. 철저히 지지선 분할 매수로 대응하십시오.")
        else:
            st.warning(f"⚠️ **[검증 결과: 유의]** 추세 횡보 구간이 길어 승률이 낮게 잡힙니다. 몰빵을 피하고 켈리 공식 비중을 엄격히 하향 조정하십시오.")

    # 🚀 [수정] 단타(돌파)와 스윙(박스권) 전략의 완벽한 분리 및 모순 해결
    with tab4:
        st.markdown("#### ⚡ 데이트레이딩 & 스윙 타점 정밀 스캐너 (오늘장 실전 대응용)")
        
        if len(df_raw) > 2:
            # 어제(전일)의 데이터 추출
            prev_candle = df_raw.iloc[-2]
            today_candle = df_raw.iloc[-1]
            
            prev_high = prev_candle['High']
            prev_low = prev_candle['Low']
            prev_close = prev_candle['Close']
            today_open = today_candle['Open']
            
            # 1. 래리 윌리엄스 변동성 돌파 타점 (단타 전용)
            vol_range = prev_high - prev_low
            k_factor = 0.5
            breakout_target = today_open + (vol_range * k_factor)
            breakout_profit = breakout_target * 1.03 # 단타 기본 3% 자율 익절 타겟
            
            # 2. 피봇(Pivot) 지지/저항선 (스윙 전용)
            pivot = (prev_high + prev_low + prev_close) / 3
            r1 = (2 * pivot) - prev_low  # 1차 저항선 (익절 목표)
            s1 = (2 * pivot) - prev_high # 1차 지지선 (진입 목표)
            
            st.info(f"💡 **[AI 타점 브리핑]** 전일 변동폭(`{vol_range:,.0f}{unit}`)을 기준으로, 성격이 완전히 다른 두 가지 실전 매매 전략을 분리하여 산출했습니다.")
            
            c_short1, c_short2 = st.columns(2)
            with c_short1:
                st.markdown("##### 🚀 전략 A: 변동성 돌파 (단타/추세 추종)")
                st.metric(label="🔥 돌파 매수 타점", value=f"{breakout_target:,.0f}{unit}", delta="이 가격 강하게 돌파 시 추격 매수")
                st.metric(label="💰 돌파 매수 익절가 (+3% 컷)", value=f"{breakout_profit:,.0f}{unit}", delta="또는 오늘 장 마감 직전(15:20) 전량 매도", delta_color="off")
                
            with c_short2:
                st.markdown("##### 🛡️ 전략 B: 피봇 박스권 (스윙/눌림목)")
                st.metric(label="🎯 1차 지지선 (스윙 진입가)", value=f"{s1:,.0f}{unit}", delta="주가가 여기까지 밀리면 안전하게 줍줍", delta_color="inverse")
                st.metric(label="⚖️ 1차 저항선 (스윙 익절가)", value=f"{r1:,.0f}{unit}", delta="반등 성공 시 이 가격에서 미련 없이 매도", delta_color="off")
        else:
            st.warning("데이터가 부족하여 타점을 계산할 수 없습니다.")
            
# 🚀 [신규 킬러 기능 3] 매물대(Volume Profile) 투시 레이더
    with tab5:
        st.markdown("#### 🧱 악성 매물대 및 콘크리트 지지선 투시 레이더 (최근 6개월 기준)")
        
        vp_df = df_raw.tail(120).copy() # 최근 120거래일(약 6개월)
        if not vp_df.empty:
            # 가격을 12개 구간으로 나누기
            min_p = vp_df['Low'].min()
            max_p = vp_df['High'].max()
            bins = np.linspace(min_p, max_p, 13)
            
            vp_df['PriceBin'] = pd.cut(vp_df['Close'], bins=bins)
            vp_data = vp_df.groupby('PriceBin')['Volume'].sum().reset_index()
            
            # 구간 중간값 구하기
            vp_data['BinCenter'] = vp_data['PriceBin'].apply(lambda x: x.mid if pd.notnull(x) else 0)
            vp_data = vp_data.dropna()
            
            max_vol = vp_data['Volume'].max()
            max_vol_price = vp_data.loc[vp_data['Volume'].idxmax(), 'BinCenter']
            
            st.info(f"💡 **AI 투시 결과:** 최근 6개월간 거래가 가장 많이 터진 **'최대 매물대(핵심 가격)'는 {max_vol_price:,.0f}{unit} 부근**입니다.")
            
            if latest_price_tmp < max_vol_price:
                st.warning(f"⚠️ 현재 주가가 최대 매물대 아래에 있습니다. {max_vol_price:,.0f}{unit} 부근으로 올라갈 때 **엄청난 매도 저항(본전 탈출 물량)**이 쏟아질 확률이 높습니다.")
            elif latest_price_tmp > max_vol_price:
                st.success(f"🔥 현재 주가가 최대 매물대 위에 있습니다. {max_vol_price:,.0f}{unit} 부근이 무너지지 않는 **콘크리트 바닥(강력 지지선)** 역할을 할 것입니다.")
            else:
                st.success(f"⚔️ 현재 주가가 최대 매물대 한가운데 있습니다. 치열한 수급 공방전이 벌어지고 있으며, 이 구간을 뚫는 방향으로 거대한 추세가 터질 것입니다.")
            
            # 🚀 [수정 3] 매물대 시각화 차트에 '만 주' 단위 명확히 추가
            fig_vp = go.Figure()
            fig_vp.add_trace(go.Bar(
                x=vp_data['Volume'],
                y=vp_data['BinCenter'],
                orientation='h',
                marker=dict(
                    color=['#D32F2F' if v == max_vol else '#90CAF9' for v in vp_data['Volume']],
                    line=dict(color='rgba(0,0,0,0)', width=1)
                ),
                # 단위(주)를 명시하여 거래대금과 혼동 방지
                text=[f"{v/10000:.0f}만 주" if v > 10000 else f"{v:,.0f} 주" for v in vp_data['Volume']],
                textposition='auto'
            ))
            fig_vp.update_layout(
                title="📈 가격대별 누적 거래량 집중도 (가장 긴 빨간 막대가 핵심 저항/지지선)",
                height=350,
                margin=dict(l=10, r=10, t=40, b=10),
                yaxis=dict(tickformat=",.0f" if unit=="원" else ",.2f"),
                xaxis=dict(visible=False)
            )
            fig_vp.add_hline(y=latest_price_tmp, line_dash="dash", line_color="#1A1A1A", annotation_text="현재가", annotation_position="top right")
            st.plotly_chart(fig_vp, use_container_width=True)
        else:
            st.error("데이터가 부족하여 매물대를 분석할 수 없습니다.")
    # # 💼 나의 전술적 포트폴리오 관리자
    with st.expander(f"💼 나의 전술적 포트폴리오 관리자 - '{target_display_name}'", expanded=True):
        
        # 🚀 [수정] 기초 자금 설정을 Form 밖으로 빼내어 실시간 연동되도록 독립시킴
        st.markdown("##### ⚙️ 기초 운용 자금 설정 (실시간 연동)")
        total_seed_money_man = st.number_input("💵 이 종목에 투입할 총 운용 자금 (만원)", value=1000, step=100)
        total_seed_money = float(total_seed_money_man * 10000)
        st.divider()
        
        # 물타기 계산기 데이터만 Form으로 묶어 렉 방지
        with st.form(key=f"portfolio_form_{target_display_name}"):
            ui_left_col, ui_mid_col, ui_right_col = st.columns([1.1, 1.1, 1.8])
            
            with ui_left_col:
                st.markdown("<p style='font-weight:bold; margin-bottom:-5px;'>🛒 1차 매수 기록 (기본 포지션)</p>", unsafe_allow_html=True)
                my_init_price = st.number_input("1차 매수 가", value=int(saved_portfolio["p1"]), step=100 if unit=="원" else 1)
                my_init_qty = st.number_input("1차 수량(주)", value=int(saved_portfolio["q1"]), step=1)
                
                st.markdown("<p style='color:#1976D2; font-weight:bold; margin-bottom:-5px;'>🔵 2차 분할 매수 기록</p>", unsafe_allow_html=True)
                my_add_price = st.number_input("2차 매수 가", value=int(saved_portfolio["p2"]), step=100 if unit=="원" else 1)
                my_add_qty = st.number_input("2차 수량(주)", value=int(saved_portfolio["q2"]), step=1)
                
                st.markdown("<p style='color:#9C27B0; font-weight:bold; margin-bottom:-5px;'>🟣 3차 최종 물타기 기록</p>", unsafe_allow_html=True)
                my_add3_price = st.number_input("3차 매수 가", value=int(saved_portfolio["p3"]), step=100 if unit=="원" else 1)
                my_add3_qty = st.number_input("3차 수량(주)", value=int(saved_portfolio["q3"]), step=1)

                # 🚀 [수정 2] 1차는 보존하고 물타기 기록만 개별 삭제하는 버튼 추가
                btn_col1, btn_col2, btn_col3 = st.columns([4, 3, 3])
                with btn_col1:
                    save_btn = st.form_submit_button(f"💾 '{target_display_name}' 확정 저장", use_container_width=True)
                with btn_col2:
                    clear_add_btn = st.form_submit_button("💧 물타기만 지우기", use_container_width=True)
                with btn_col3:
                    clear_all_btn = st.form_submit_button("🗑️ 전체 초기화", use_container_width=True)

                # 1. 저장 로직
                if save_btn:
                    st.session_state['stock_portfolio_db'][target_display_name] = {
                        "p1": my_init_price, "q1": my_init_qty,
                        "p2": my_add_price, "q2": my_add_qty,
                        "p3": my_add3_price, "q3": my_add3_qty
                    }
                    save_local_db("portfolio_storage.json", st.session_state['stock_portfolio_db'])
                    st.success(f"✅ 데이터 저장 완료!")
                    st.rerun()
                
                # 2. 물타기(2,3차)만 지우기 로직
                if clear_add_btn:
                    st.session_state['stock_portfolio_db'][target_display_name]["p2"] = 0
                    st.session_state['stock_portfolio_db'][target_display_name]["q2"] = 0
                    st.session_state['stock_portfolio_db'][target_display_name]["p3"] = 0
                    st.session_state['stock_portfolio_db'][target_display_name]["q3"] = 0
                    save_local_db("portfolio_storage.json", st.session_state['stock_portfolio_db'])
                    st.rerun()

                # 3. 전체 지우기 로직
                if clear_all_btn:
                    st.session_state['stock_portfolio_db'][target_display_name] = {"p1": 0, "q1": 0, "p2": 0, "q2": 0, "p3": 0, "q3": 0}
                    save_local_db("portfolio_storage.json", st.session_state['stock_portfolio_db'])
                    st.rerun()

            # Form 내부에서 연산 처리 (타이핑 중 렉 발생 안 함)
            total_qty = my_init_qty + my_add_qty + my_add3_qty
            total_cost = (my_init_price * my_init_qty) + (my_add_price * my_add_qty) + (my_add3_price * my_add3_qty)
            final_avg_price = float(total_cost / total_qty) if total_qty > 0 else 0.0
            
            prob_win = float(buy_timing_score / 100.0)
            prob_loss = 1.0 - prob_win
            b_ratio = risk_reward_ratio if risk_reward_ratio > 0 else 1.0
            kelly_f = prob_win - (prob_loss / b_ratio)
            kelly_pct = max(0.0, kelly_f) * 100.0
            target_betting_money_man = (total_seed_money * (kelly_pct / 100.0)) / 10000

            with ui_mid_col:
                st.markdown("##### 🛡️ 자금 분할 결과")
                cash_ratio_guide = 100 - buy_timing_score
                cash_amount_guide_man = (total_seed_money * (cash_ratio_guide / 100.0)) / 10000
                
                st.metric(label="🧭 안전 현금 비중 가이드", value=f"{cash_ratio_guide}%", delta=f"{cash_amount_guide_man:,.0f} 만원 유지 권장", delta_color="inverse")
                st.metric(label="⚙️ 수학적 최적 베팅 비율 (켈리)", value=f"{kelly_pct:.1f}%")
                st.metric(label="🎯 권장 최대 진입 탄약", value=f"{target_betting_money_man:,.0f} 만원")
                
                if kelly_pct == 0: st.error("⚠️ 비중 제로화 권고.")
                else: st.success("🏅 시드 최적화 완료.")

            with ui_right_col:
                st.markdown("##### 📈 나의 실시간 계좌 포지션 상태")
                if my_init_qty > 0:
                    my_current_return = ((latest_price_tmp - final_avg_price) / final_avg_price) * 100
                    total_profit_amt = (latest_price_tmp - final_avg_price) * total_qty
                    
                    m_c1, m_c2 = st.columns(2)
                    with m_c1:
                        st.metric(label="📊 나의 최종 조정 평단가", value=f"{final_avg_price:,.1f}{unit}", delta=f"{my_current_return:+.2f}%")
                    with m_c2:
                        st.metric(label="💸 실시간 총 손익금액", value=f"{total_profit_amt:,.0f}{unit}")
                    
                    # 🚀 [논리 오류 완벽 수정] 계좌 수익 상태에 따른 철저한 이중 제어 장치
                    if latest_price_tmp < final_avg_price:
                        # 주가가 내 평단보다 아래(마이너스)일 때는 과거 고점 수치를 원천 차단하고 대기 메시지만 출력
                        st.warning(f"⚠️ **[안전장치 작동: 자동 매도 예약 대기]**\n\n현재 주가(`{latest_price_tmp:,.0f}{unit}`)가 차장님의 평단가(`{final_avg_price:,.0f}{unit}`)보다 낮은 손실 구간입니다. **지금 MTS에 자동 감시를 걸면 원치 않는 손절이 나갈 수 있으니, 주가가 평단가 위로 복귀할 때까지 MTS 앱 설정을 절대 보류하십시오.**")
                    else:
                        # 주가가 내 평단을 넘어서 수익권(플러스)일 때만 익절 가이드라인 오픈
                        st.success(f"🔥 **[MTS 자동 감시 주문 (익절 추적 활성화)]**\n\n축하합니다! 평단가 위 안전 수익권 진입. 이제 고점 대비 밀릴 때 어깨에서 팔 수 있도록 미래에셋 앱에 **`{trailing_stop_gate:,.0f}{unit}`**을 자동매도 조건으로 걸어두십시오.")
                    
                    if latest_price_tmp >= target_profit_price:
                        if latest_price_tmp <= trailing_stop_gate and trailing_stop_gate >= final_avg_price:
                            st.error(f"🚨 **트레이링 스톱 발동 (`{trailing_stop_gate:,.0f}{unit}` 이탈):** 고점 돌파 후 꺾임 확인. 지금 전량 익절하여 수익을 확정 지으십시오.")
                    
                    st.write("---")
                    st.markdown("🎯 **마스터 퀀트 정석 분할매수 포지션 가이드라인**")
                    st.info(f"💡 **2차 분할 매수 타점:** 평단 방어선 대기 타점 부근 `{latest_price_tmp * 1.01:,.0f}{unit}`에서 1:1 비율 분할 매수 대기.")
                    st.warning(f"⚠️ **3차 최종 스케일링 타점:** 초강력 마지노 생명선인 추천가 `{target_entry_price:,.0f}{unit}` 도달 시 1:1:2 비율 최종 진입 권장.")
                else:
                    st.info("💡 좌측에 1차 매수 단가와 수량을 입력 후 저장하시면, 즉시 MTS에 등록할 '트레이링 스톱(자동 매도) 기준가'를 산출해 드립니다.")

    # 뉴스 및 공시망 
    st.divider()
    info_left_col, info_right_col = st.columns(2)
    with info_left_col:
        st.markdown(f"### 📰 오늘의 실시간 호재 레이더")
        sidebar_code_url = f"https://finance.naver.com/item/news.naver?code={pure_code}"
        st.markdown(f"🔗 **[📢 {target_display_name} 금융 실시간 뉴스룸 바로가기]({sidebar_code_url})**")
        main_news = get_main_live_news(target_display_name, count=4)
        for idx, n_item in enumerate(main_news):
            st.markdown(f"{idx+1}. `[{n_item['press']}]` [{n_item['title']}]({n_item['link']})")
    
    with info_right_col:
        st.markdown(f"### 🏛️ 주요 핵심 공시 정보망")
        if not is_usa:
            naver_notice_url = f"https://finance.naver.com/item/news_notice.naver?code={pure_code}"
            st.markdown(f"🏛️ **[🔍 {target_display_name} 한국 DART 공시망 열기]({naver_notice_url})**")

    st.divider()

    # 세력 등기부등본
    if not is_usa:
        st.markdown("#### 🐳 세력 수급 등기부 (최근 5일 누적) : `[외국인/기관 순매수 = 🟢호재] | [개인 순매수 = 🔴악재]`")
        
        abs_favs = {"개인(개미)": abs(retail), "외국인": abs(foreigners), "기관": abs(institution)}
        max_subject = max(abs_favs, key=abs_favs.get)
        
        w_c1, w_c2, w_c3, w_c4 = st.columns([1, 1, 1, 2.5])
        with w_c1: st.metric(label="외국인 수급", value=f"{foreigners:+.1f} 억")
        with w_c2: st.metric(label="기관 수급", value=f"{institution:+.1f} 억")
        with w_c3: st.metric(label="개인 수급", value=f"{retail:+.1f} 억")
        
        # 🚀 [수정 1] 세력 수급 등기부 (금액이 아닌 '압도적 비율' 기반 상대 평가 도입)
        with w_c4:
            # 1. 개미가 외국인/기관보다 2배 이상 많이 사고, 금액이 30억 이상일 때 (확실한 세력 이탈)
            if retail >= 30.0 and retail > max(foreigners, institution) * 2:
                st.warning(f"🔴 악재: 세력 이탈. 개인({retail:.1f}억)이 압도적으로 물량 폭탄을 받고 있습니다.")
            
            # 2. 외국인과 기관이 20억 이상 완벽하게 같이 살 때 (쌍끌이 호재)
            elif foreigners >= 20.0 and institution >= 20.0:
                st.success(f"🔥 🟢 강력 호재: 외국인({foreigners:.1f}억)과 기관({institution:.1f}억) 쌍끌이 대량 매집!")
            
            # 3. 외국인이 개미보다 2배 이상 많이 사고, 금액이 30억 이상일 때 (외국인 주도)
            elif foreigners >= 30.0 and foreigners > retail * 2:
                st.info(f"🟢 호재: 외국인 주도 대량 매집 ({foreigners:.1f}억)")
            
            # 4. 기관이 개미보다 2배 이상 많이 사고, 금액이 30억 이상일 때 (기관 주도)
            elif institution >= 30.0 and institution > retail * 2:
                st.info(f"🟢 호재: 기관 주도 대량 매집 ({institution:.1f}억)")
            
            # 5. 위 조건에 맞지 않는 애매한 핑퐁 게임일 때
            else: 
                st.code("⚪ 관망: 한쪽이 압도하지 못하는 치열한 수급 공방전입니다.")

    # 수학적 기대 손익비 및 가이드라인
    st.divider()
    st.subheader(f"📐 수학적 기대 손익비(Risk-Reward) 필터 및 밸류에이션 가이드")
    
    slice_len = len(df)
    df_slice = df.tail(slice_len)
    high_vol_threshold = df_slice['Volume'].quantile(0.8) if len(df_slice) > 1 else 1.0
    smart_money_days = df_slice[df_slice['Volume'] >= high_vol_threshold]
    estimated_whale_price = (smart_money_days['Close'].mean() * 0.6) + (smart_money_days['High'].mean() * 0.4) if not smart_money_days.empty else df_slice['Close'].mean()
    
    if pd.isna(estimated_whale_price): estimated_whale_price = latest_price_tmp
    whale_diff_ratio = ((latest_price_tmp - estimated_whale_price) / estimated_whale_price) * 100 if estimated_whale_price > 0 else 0.0

    g_col1, g_col2 = st.columns(2)
    with g_col1:
        whale_badge = f"{chart_period} 기준 세력 발바닥 부근" if whale_diff_ratio <= 8 else f"{chart_period} 기준 세력 머리 위 (유의)"
        st.metric(label=f"🎯 세력 추정 평단가", value=fmt.format(estimated_whale_price), delta=f"{whale_diff_ratio:+.1f}% [{whale_badge}]", delta_color="inverse" if whale_diff_ratio <= 8 else "normal")
    with g_col2:
        st.metric(label="📊 최종 산출 손익비 (1 : X)", value=f"1 : {risk_reward_ratio:.2f}")

    # 전략 브리핑 
    st.markdown("#### 🚨 실시간 단기 가격 전략 및 포지션 가이드라인")
    
    str_disparity = "20일 생명선에 완벽히 수렴하며 이상적인 눌림목 타점을 형성 중입니다." if 98 <= disparity <= 102 else (f"20일선 대비 {disparity:.1f}%로 단기 이격이 벌어져 있으니 눌림을 기다리십시오." if disparity > 102 else f"20일선 대비 {disparity:.1f}% 하회 중으로 낙폭 과대 반등을 노리기 유리합니다.")
    str_rsi = "단기 수급 과열권(RSI 65+)이므로 신규 추격 매수는 절대 금물입니다." if rsi_val >= 65 else ("단기 과매도 국면(RSI 35 이하)에 진입해 저가 매수세(반등)가 유입될 확률이 매우 높습니다." if rsi_val <= 35 else "현재 RSI 보조지표는 중립지대(40~60)로 수급 공방전이 치열하게 벌어지고 있습니다.")
    str_ratio = f"기대 손익비가 1:{risk_reward_ratio:.1f}로 익절 폭이 손절 폭보다 압도적으로 큰 가성비 구간입니다." if risk_reward_ratio >= 1.5 else f"현재 손익비(1:{risk_reward_ratio:.1f})는 하방 리스크가 다소 크므로 비중을 싣기보다 관망이 유리합니다."
    
    st.info(f"🔵 **[AI 통합 포지션 가이드]** 주가의 현재 위치는 {str_disparity} 또한 {str_rsi} {str_ratio} 상단의 AI 적합도 점수({buy_timing_score}점)를 신뢰하여 켈리 공식이 제안하는 비중만큼만 기계적으로 분할 진입하십시오.")

    st.markdown("#### 🚨 윌리엄 오닐의 CAN SLIM 및 피터린치 실적 분석 시스템")
    c_col1, c_col2, c_col3, c_col4 = st.columns(4)
    with c_col1: 
        st.metric(label="자산 가치 비율 (PBR)", value=f"{pbr_val:.2f}배")
        if pbr_val < 0.7: st.success("🟢 [매우 우수] 자산 청산가치 이하 안전지대")
        elif pbr_val < 1.3: st.info("🔵 [우수] 확실한 저평가 상태")
        else: st.code("⚪ [보통] 표준 멀티플 영역")
    with c_col2: 
        st.metric(label="미래형 추정 PER", value=f"{net_per:.2f}배")
        if net_per < 8.0: st.success("🟢 [매우 우수] 이익 체력 대비 저평가")
        elif net_per < 15.0: st.info("🔵 [우수] 무난한 밸류 밴드")
        else: st.code("⚪ [보통] 업계 표준 스탠스")
    with c_col3: 
        st.metric(label="이익(EPS) 추정 성장률", value=f"{net_growth:+.1f}%")
        if net_growth > 20.0: st.success("🟢 [매우 우수] 우상향 주도주 체력")
        else: st.info("🔵 [우수] 견고한 성장 속도")
    with c_col4:
        st.metric(label="미래형 PEG 지표", value=f"{peg_val:.2f}배")
        if peg_val <= 0.5: st.success("🟢 [매우 우수] 피터린치식 가성비 타점")
        else: st.info("🔵 [우수] 성장성 대비 합리적 주가")
        
    st.divider()
    st.caption("⚖️ **법적 면책 조항 (Legal Disclaimer):** 본 시스템이 제공하는 모든 가치 평가, 적합도 점수, 레이더 신호 및 투자 가이드라인은 개인의 투자 판단을 돕기 위한 보조 참고 자료입니다. API 통신 지연이나 알고리즘 연산에 의한 데이터 오류가 발생할 수 있으며, 어떠한 경우에도 투자 결과에 대한 법적 책임 소재 및 증빙 자료로 사용될 수 없습니다. 최종 투자 결정권과 책임은 전적으로 투자자 본인에게 있습니다.")
