import streamlit as st
import streamlit.components.v1 as components  
import requests
import time
from datetime import datetime, timedelta, timezone # 🔥 加咗時區工具
import pandas as pd

# --- 獲取強制香港時間 (UTC+8) ---
def get_hk_time():
    tz_hk = timezone(timedelta(hours=8))
    # 將時間轉返做普通格式，方便後面做加減數
    return datetime.now(tz_hk).replace(tzinfo=None) 

# --- 配置資訊 ---
URL_INDEX = "https://api.ibob.ai/tricky/v1/tricky-index"
URL_LIST = "https://api.ibob.ai/race/list-races"
HEADERS = {
    "token": "fe39e8b6e4c343d89f46ab65cec060b6", 
    "User-Agent": "uni-app-x/4.87",
    "v-app": "1.2.7",
    "Content-Type": "application/json"
}

RACE_COUNT = 11
MS_LIST = ["30", "25", "20", "15", "10", "6", "3", "1", "-1", "-5"]

# --- 初始化 Session State ---
if "all_data" not in st.session_state:
    st.session_state.all_data = {i: {} for i in range(1, RACE_COUNT + 1)}
if "start_times" not in st.session_state:
    st.session_state.start_times = {i: "" for i in range(1, RACE_COUNT + 1)}
if "field_sizes" not in st.session_state: 
    st.session_state.field_sizes = {i: 14 for i in range(1, RACE_COUNT + 1)}
if "is_monitoring" not in st.session_state:
    st.session_state.is_monitoring = False
if "init_done" not in st.session_state:
    st.session_state.init_done = False
if "venue_prefix" not in st.session_state:
    st.session_state.venue_prefix = "獲取中..."
if "venue_name" not in st.session_state:
    st.session_state.venue_name = "獲取中..."
if "debug_raw_times" not in st.session_state:
    st.session_state.debug_raw_times = {}

# --- 函數區 ---
def sync_all_times():
    try:
        res = requests.post(URL_LIST, headers=HEADERS, json={}, timeout=5)
        if res.status_code == 200:
            raw_json = res.json()
            st.session_state.debug_raw_times = raw_json 
            
            meetings = raw_json.get('data') or []
            if meetings:
                meeting = meetings[0] 
                
                venue_code = meeting.get('venueCode', '')
                venue_zh = meeting.get('venue', {}).get('zh', '')
                date_str = meeting.get('date', '').replace('-', '')
                
                if venue_code and date_str:
                    st.session_state.venue_prefix = f"{date_str}{venue_code}"
                    st.session_state.venue_name = f"{venue_zh} ({venue_code}) 🐎"
                
                races = meeting.get('races', [])
                for r in races:
                    r_no = r.get('no')
                    post_time = r.get('postTime') 
                    field_size = r.get('wageringFieldSize', 14) 
                    
                    if r_no is not None:
                        if post_time:
                            time_str = post_time.split('T')[1][:5]
                            st.session_state.start_times[int(r_no)] = time_str
                        st.session_state.field_sizes[int(r_no)] = field_size
            
            st.session_state.init_done = True
            return True
        else:
            st.session_state.init_done = True
            return False
    except Exception as e:
        st.session_state.init_done = True
        return False

def fetch_data(prefix):
    for n in range(1, RACE_COUNT + 1):
        race_id = f"{prefix}{str(n).zfill(2)}"
        try:
            res = requests.post(URL_INDEX, headers=HEADERS, json={"raceId": race_id}, timeout=3)
            if res.status_code == 200:
                data = res.json().get('data', [])
                process_data(n, data)
        except:
            pass

def process_data(race_num, data):
    t_str = st.session_state.start_times.get(race_num, "")
    mins_left = -999
    if len(t_str) == 5:
        try:
            # 🔥 將 datetime.now() 全部換做 get_hk_time()
            target = datetime.combine(get_hk_time().date(), datetime.strptime(t_str, "%H:%M").time())
            mins_left = (target - get_hk_time()).total_seconds() / 60
        except:
            pass
        
    for item in data:
        h_no = str(item['horseNo'])
        
        if h_no not in st.session_state.all_data[race_num]:
            st.session_state.all_data[race_num][h_no] = {}
            
        st.session_state.all_data[race_num][h_no]["current"] = item['current']
        
        if mins_left != -999:
            for m in MS_LIST:
                m_val = int(m)
                if abs(mins_left - m_val) <= 0.5:
                    if m not in st.session_state.all_data[race_num][h_no]:
                        st.session_state.all_data[race_num][h_no][m] = item['current']

# --- 介面區 (UI) ---
st.set_page_config(page_title="iBob AI 趨勢監控", layout="wide")
st.title("🏇 iBob AI 趨勢監控 - 終極自動版")

if not st.session_state.init_done:
    with st.spinner('🔄 系統自動讀取緊今日場地同開跑時間...'):
        sync_all_times()
        st.rerun()

st.success(f"📍 系統偵測到今日賽事： **{st.session_state.venue_name}**")

col1, col2, col3 = st.columns([2, 2, 2])
with col1:
    prefix = st.text_input("日期前綴 (已全自動同步):", value=st.session_state.venue_prefix)
with col2:
    st.write("") 
    if st.button("🔄 手動重新同步資料"):
        with st.spinner('同步中...'):
            sync_all_times()
        st.rerun()
with col3:
    st.write("") 
    if st.session_state.is_monitoring:
        if st.button("🛑 停止監控", type="primary"):
            st.session_state.is_monitoring = False
            st.rerun()
    else:
        if st.button("🚀 啟動監控"):
            st.session_state.is_monitoring = True
            st.rerun()

race_list = [f"第 {i} 場" for i in range(1, RACE_COUNT + 1)]
selected_race_str = st.radio("選擇場次:", race_list, horizontal=True)
curr_race = int(selected_race_str.split(" ")[1])

c1, c2 = st.columns(2)
with c1:
    new_time = st.text_input(
        f"第 {curr_race} 場開跑時間 (可手動修改):", 
        value=st.session_state.start_times.get(curr_race, ""), 
        placeholder="例如打 18:40 然後撳 Enter"
    )
    if new_time != st.session_state.start_times.get(curr_race, ""):
        st.session_state.start_times[curr_race] = new_time
        st.rerun()

with c2:
    t_str = st.session_state.start_times.get(curr_race, "")
    if len(t_str) == 5:
        try:
            # 🔥 將 datetime.now() 換做 get_hk_time()
            target = datetime.combine(get_hk_time().date(), datetime.strptime(t_str, "%H:%M").time())
            diff_seconds = int((target - get_hk_time()).total_seconds())
            
            html_code = f"""
            <div style="font-family: 'Source Sans Pro', sans-serif; padding-top: 5px;">
                <div style="font-size: 14px; color: #888;">⏳ 倒數計時</div>
                <div id="timer" style="font-size: 2.2rem; font-weight: bold; margin-top: 2px;"></div>
            </div>
            <script>
                let diff = {diff_seconds};
                function updateTimer() {{
                    const timerElement = document.getElementById("timer");
                    if (diff > 0) {{
                        const m = Math.floor(diff / 60);
                        const s = diff % 60;
                        timerElement.innerText = "T-Minus: " + m + "m " + (s < 10 ? "0" : "") + s + "s";
                        timerElement.style.color = "#FF4B4B"; 
                    }} else {{
                        const over = Math.abs(diff);
                        const m = Math.floor(over / 60);
                        const s = over % 60;
                        timerElement.innerText = "🏁 OVER: " + m + "m " + (s < 10 ? "0" : "") + s + "s";
                        timerElement.style.color = "#9b59b6"; 
                    }}
                    diff--;
                }}
                setInterval(updateTimer, 1000);
                updateTimer();
            </script>
            """
            components.html(html_code, height=90)
        except Exception as e:
            st.metric("⏳ 倒數計時", "--:--")
    else:
        st.metric("⏳ 倒數計時", "⚠️ 未有時間")

# 表格顯示
st.subheader(f"📊 {selected_race_str} 數據")
race_data = st.session_state.all_data[curr_race]
current_field_size = st.session_state.field_sizes.get(curr_race, 14) 

df_data = []
for h_idx in range(1, current_field_size + 1):
    h_no = str(h_idx)
    row = {"馬號": h_no, "目前": race_data.get(h_no, {}).get("current", "--")}
    for m in MS_LIST:
        row[m] = race_data.get(h_no, {}).get(m, "--")
    df_data.append(row)

df = pd.DataFrame(df_data)
dynamic_height = (current_field_size + 1) * 36 + 20
st.dataframe(df, width="stretch", height=dynamic_height, hide_index=True)

with st.expander("🛠️ IT大師除錯模式"):
    st.write("如果有問題先打開睇")
    st.json(st.session_state.debug_raw_times)

# --- 監控迴圈 ---
if st.session_state.is_monitoring:
    fetch_data(prefix)
    time.sleep(10)
    st.rerun()
