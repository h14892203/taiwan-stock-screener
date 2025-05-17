
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("選股神器｜台股技術圖表系統")

# 1. 讓用戶輸入Token
TOKEN = st.text_input("請輸入你的 FinMind API Token", type="password")
API_URL = "https://api.finmindtrade.com/api/v4/data"

stock_id = st.text_input("輸入股票代碼（如 2330）", value="2330")
k_type = st.selectbox("K線類型", ["日K", "週K", "月K"])
adjusted = st.radio("是否還原權息", ["還原", "不還原"], horizontal=True)

def get_price_data(stock_id, adjusted, token):
    dataset = "TaiwanStockPriceAdj" if adjusted == "還原" else "TaiwanStockPrice"
    start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = datetime.today().strftime("%Y-%m-%d")
    params = {
        "dataset": dataset,
        "data_id": stock_id,
        "start_date": start_date,
        "end_date": end_date,
        "token": token,
    }
    response = requests.get(API_URL, params=params)
    # 錯誤保護
    try:
        res_json = response.json()
        if "data" not in res_json:
            st.error(f"API 回應錯誤：{res_json.get('msg', '未知錯誤')}")
            return None
        data = res_json["data"]
        if not data:
            st.warning("查無資料，請檢查代碼或資料區間")
            return None
    except Exception as e:
        st.error(f"API 回應異常：{e}")
        return None
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    return df

def resample_ohlc(df, period):
    ohlc = df[["open", "max", "min", "close"]].resample(period).agg({
        "open": "first",
        "max": "max",
        "min": "min",
        "close": "last"
    }).dropna()
    return ohlc

def plot_chart(df):
    df["MA20"] = df["close"].rolling(window=20).mean()
    df["MA100"] = df["close"].rolling(window=100).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["max"],
        low=df["min"],
        close=df["close"],
        name="K線",
        increasing_line_color="green",
        decreasing_line_color="red"
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], mode="lines", name="20日均線", line=dict(color="violet")))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA100"], mode="lines", name="100日均線", line=dict(color="pink")))

    fig.update_layout(
        xaxis_title="日期",
        yaxis_title="價格",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

def legal_disclaimer():
    st.markdown("---")
    st.markdown(
        '''<div style='font-size:13px; color:gray; text-align:center;'>
        本系統為選股輔助工具，資料來源為台灣公開市場資訊，<br>
        不提供投資建議、個股推薦或保證報酬。<br>
        使用者應自行判斷投資風險，所有操作與決策應由使用者獨立承擔。
        </div>''',
        unsafe_allow_html=True
    )

# 要有Token才能查詢
if stock_id and TOKEN:
    df = get_price_data(stock_id, adjusted, TOKEN)
    if df is not None:
        if k_type == "週K":
            df = resample_ohlc(df, "W")
        elif k_type == "月K":
            df = resample_ohlc(df, "M")
        plot_chart(df)
        legal_disclaimer()
else:
    st.info("請輸入股票代碼與 FinMind Token 以顯示圖表")
