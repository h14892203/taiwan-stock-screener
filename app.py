
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("選股神器｜台股條件選股與技術圖表")

TOKEN = st.text_input("請輸入你的 FinMind API Token", type="password")
API_URL = "https://api.finmindtrade.com/api/v4/data"

# 選股條件設定
st.sidebar.header("選股條件")
ma_20_up = st.sidebar.checkbox("20日均線上揚")
ma_100_up = st.sidebar.checkbox("100日均線上揚")
foreign_buy_days = st.sidebar.number_input("外資連續買超天數(0=不限)", 0, 30, 0)
volume_ratio = st.sidebar.number_input("近5日均量/前20日均量 > ", 0.0, 10.0, 1.0)

# 股票代碼
stock_id = st.text_input("輸入股票代碼（如 2330，留空則自動全市場篩選）")
run_filter = st.button("執行選股（全市場）")

# 範例台股代碼清單（可連API自動抓最新上市清單，這裡簡化示範）
stock_list = ['2330', '2317', '2412', '2454', '2303', '2308']

@st.cache_data(show_spinner=False)
def get_price_data(stock_id, token):
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d"),
        "end_date": datetime.today().strftime("%Y-%m-%d"),
        "token": token,
    }
    r = requests.get(API_URL, params=params)
    d = r.json().get("data", [])
    if not d:
        return None
    df = pd.DataFrame(d)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df = df.sort_index()
    return df

@st.cache_data(show_spinner=False)
def get_institutional_data(stock_id, token):
    params = {
        "dataset": "TaiwanStockInstitutionalInvestors",
        "data_id": stock_id,
        "start_date": (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d"),
        "end_date": datetime.today().strftime("%Y-%m-%d"),
        "token": token,
    }
    r = requests.get(API_URL, params=params)
    d = r.json().get("data", [])
    if not d:
        return None
    df = pd.DataFrame(d)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df = df.sort_index()
    return df

def plot_stock(df, inst_df):
    # 計算均線
    df["MA20"] = df["close"].rolling(window=20).mean()
    df["MA100"] = df["close"].rolling(window=100).mean()
    # 畫K線
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["max"], low=df["min"], close=df["close"],
        name="K線", increasing_line_color="green", decreasing_line_color="red"
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], mode="lines", name="20日均線", line=dict(color="violet")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA100"], mode="lines", name="100日均線", line=dict(color="pink")))
    # 成交量
    fig.add_trace(go.Bar(x=df.index, y=df["Trading_Volume"], name="成交量", marker=dict(color="gray"), yaxis="y2"))
    # 法人買賣超
    if inst_df is not None and not inst_df.empty:
        fig.add_trace(go.Bar(x=inst_df.index, y=inst_df["Foreign_Investor_Net_Buy_Sell"], name="外資買賣超", marker=dict(color="green"), yaxis="y3"))
        fig.add_trace(go.Bar(x=inst_df.index, y=inst_df["Investment_Trust_Net_Buy_Sell"], name="投信買賣超", marker=dict(color="orange"), yaxis="y3"))
        fig.add_trace(go.Bar(x=inst_df.index, y=inst_df["Dealer_Net_Buy_Sell"], name="自營買賣超", marker=dict(color="red"), yaxis="y3"))
    # 設定 layout
    fig.update_layout(
        xaxis=dict(domain=[0, 1], rangeslider=dict(visible=False)),
        yaxis=dict(title="股價", side="left"),
        yaxis2=dict(title="成交量", overlaying="y", side="right", position=0.95, showgrid=False),
        yaxis3=dict(title="三大法人", anchor="free", overlaying="y", side="right", position=1, showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
        height=700, template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

def filter_stock(df, inst_df):
    # 條件判斷
    result = True
    if ma_20_up:
        result = result and (df["MA20"].iloc[-1] > df["MA20"].iloc[-2])
    if ma_100_up:
        result = result and (df["MA100"].iloc[-1] > df["MA100"].iloc[-2])
    if foreign_buy_days > 0 and inst_df is not None and not inst_df.empty:
        # 連續外資買超天數
        last_n = inst_df["Foreign_Investor_Net_Buy_Sell"].tail(int(foreign_buy_days))
        result = result and all(last_n > 0)
    if volume_ratio > 1.0:
        # 近5日均量/前20日均量
        v5 = df["Trading_Volume"].tail(5).mean()
        v20 = df["Trading_Volume"].tail(25).head(20).mean()
        if v20 > 0:
            result = result and ((v5/v20) > volume_ratio)
    return result

# 主流程
if TOKEN:
    if stock_id:
        df = get_price_data(stock_id, TOKEN)
        inst_df = get_institutional_data(stock_id, TOKEN)
        if df is not None and inst_df is not None:
            df["MA20"] = df["close"].rolling(window=20).mean()
            df["MA100"] = df["close"].rolling(window=100).mean()
            plot_stock(df, inst_df)
        else:
            st.error("查無資料，請檢查代碼或API權限")
    elif run_filter:
        result_table = []
        for sid in stock_list:
            df = get_price_data(sid, TOKEN)
            inst_df = get_institutional_data(sid, TOKEN)
            if df is None or inst_df is None or len(df) < 101:
                continue
            df["MA20"] = df["close"].rolling(window=20).mean()
            df["MA100"] = df["close"].rolling(window=100).mean()
            if filter_stock(df, inst_df):
                result_table.append({"股票代碼": sid, "股價": df["close"].iloc[-1]})
        if result_table:
            st.success("選股結果：")
            df_result = pd.DataFrame(result_table)
            st.dataframe(df_result)
        else:
            st.warning("目前無任何符合條件的股票")
else:
    st.info("請輸入 FinMind Token 開始查詢（所有條件與圖表皆可用免費API）")

st.markdown("---")
st.markdown(
    '''<div style='font-size:13px; color:gray; text-align:center;'>
    本系統為選股輔助工具，資料來源為台灣公開市場資訊，<br>
    不提供投資建議、個股推薦或保證報酬。<br>
    使用者應自行判斷投資風險，所有操作與決策應由使用者獨立承擔。
    </div>''',
    unsafe_allow_html=True
)
