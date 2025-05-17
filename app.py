import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from finmind.data import DataLoader

# FinMind Token（第一次會要你輸入，有存檔就不用再重複）
@st.cache_data
def get_token():
    token = st.session_state.get("finmind_token", "")
    if not token:
        token = st.text_input("請輸入你的 FinMind API Token：", type="password")
        st.session_state["finmind_token"] = token
    return token

token = get_token()
if not token:
    st.stop()

dl = DataLoader()
dl.login_by_token(api_token=token)

# 股票代碼與條件
st.title("台股選股神器 - 理想版（FinMind專用）")
stock_id = st.text_input("輸入股票代號（例：2330）", value="2330")

# 是否還原K線
restore_k = st.checkbox("顯示還原權息K棒（需 FinMind 權限）", value=False)
data_type = "after" if restore_k else "origin"

# 下載K棒與法人
@st.cache_data
def load_data(stock_id, data_type):
    k = dl.taiwan_stock_daily(
        stock_id=stock_id,
        start_date="2020-01-01",
        end_date=pd.Timestamp.now().strftime("%Y-%m-%d"),
        data_type=data_type
    )
    # 法人
    f = dl.taiwan_stock_institutional_investors(
        stock_id=stock_id,
        start_date="2020-01-01",
        end_date=pd.Timestamp.now().strftime("%Y-%m-%d")
    )
    return k, f

try:
    k, f = load_data(stock_id, data_type)
    if k.empty:
        st.error("查無資料，請檢查代碼或權限！")
        st.stop()
except Exception as e:
    st.error(f"下載資料失敗：{e}")
    st.stop()

# 計算20日、100日均線
k["MA20"] = k["close"].rolling(window=20).mean()
k["MA100"] = k["close"].rolling(window=100).mean()

# 成交量均線
k["VOL10"] = k["Trading_Volume"].rolling(window=10).mean()
k["VOL20"] = k["Trading_Volume"].rolling(window=20).mean()

# --- K棒主圖 ---
fig = go.Figure()

# K棒
fig.add_trace(go.Candlestick(
    x=k["date"],
    open=k["open"],
    high=k["max"],
    low=k["min"],
    close=k["close"],
    name="K棒"
))

# 20日均線（綠色）
fig.add_trace(go.Scatter(
    x=k["date"], y=k["MA20"],
    mode='lines', line=dict(color='lime', width=1.5),
    name='20日均線'
))
# 100日均線（紅色）
fig.add_trace(go.Scatter(
    x=k["date"], y=k["MA100"],
    mode='lines', line=dict(color='red', width=1.5),
    name='100日均線'
))

fig.update_layout(
    title=f"{stock_id} K棒（{'還原' if restore_k else '原始'}）+ 20/100日均線",
    xaxis_rangeslider_visible=False,
    height=480,
    plot_bgcolor="#23272e",
    paper_bgcolor="#23272e",
    font_color="#fff"
)

# --- 成交量 ---
fig_vol = go.Figure()
fig_vol.add_trace(go.Bar(
    x=k["date"], y=k["Trading_Volume"], name="成交量", marker_color='#8888FF'
))
fig_vol.add_trace(go.Scatter(
    x=k["date"], y=k["VOL10"],
    mode='lines', line=dict(color='yellow', width=1.2, dash='dot'),
    name='10日均量'
))
fig_vol.add_trace(go.Scatter(
    x=k["date"], y=k["VOL20"],
    mode='lines', line=dict(color='purple', width=1.2, dash='dot'),
    name='20日均量'
))
fig_vol.update_layout(
    title="成交量",
    height=200, plot_bgcolor="#23272e", paper_bgcolor="#23272e", font_color="#fff"
)

# --- 法人買賣 ---
f_sum = f.groupby("date")[["Foreign_Investor_Buy", "Foreign_Investor_Sell",
                           "Investment_Trust_Buy", "Investment_Trust_Sell",
                           "Dealer_Self_Buy", "Dealer_Self_Sell"]].sum().reset_index()
f_sum["外資淨買賣"] = f_sum["Foreign_Investor_Buy"] - f_sum["Foreign_Investor_Sell"]
f_sum["投信淨買賣"] = f_sum["Investment_Trust_Buy"] - f_sum["Investment_Trust_Sell"]
f_sum["自營商淨買賣"] = f_sum["Dealer_Self_Buy"] - f_sum["Dealer_Self_Sell"]

fig_fund = go.Figure()
fig_fund.add_trace(go.Bar(
    x=f_sum["date"], y=f_sum["外資淨買賣"],
    name="外資", marker_color="#4fbeef"
))
fig_fund.add_trace(go.Bar(
    x=f_sum["date"], y=f_sum["投信淨買賣"],
    name="投信", marker_color="#d8b02c"
))
fig_fund.add_trace(go.Bar(
    x=f_sum["date"], y=f_sum["自營商淨買賣"],
    name="自營商", marker_color="#b85fff"
))
fig_fund.update_layout(
    title="三大法人每日淨買賣",
    barmode="relative", height=200, plot_bgcolor="#23272e", paper_bgcolor="#23272e", font_color="#fff"
)

# --- 版面配置 ---
st.plotly_chart(fig, use_container_width=True)
st.plotly_chart(fig_vol, use_container_width=True)
st.plotly_chart(fig_fund, use_container_width=True)

st.markdown("""
<span style='color:#aaa;font-size:13px'>
Powered by FinMind API & 宏爺理想選股神器 2024  
（遇API權限不足時，請至 FinMind 會員中心購買還原K棒權限）
</span>
""", unsafe_allow_html=True)
