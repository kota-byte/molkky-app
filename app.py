import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. データベース準備 ---
def init_db():
    conn = sqlite3.connect('molkky.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS throw_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  dist REAL, target_no INTEGER, is_success INTEGER,
                  n INTEGER, ne INTEGER, e INTEGER, se INTEGER,
                  s INTEGER, sw INTEGER, w INTEGER, nw INTEGER,
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 🚀 【高速化】データを読み込む関数をキャッシュ化し、スマホの負担を激減させる
@st.cache_data(ttl=60) # 60秒間は再計算せず、メモリから一瞬でデータを引き出す
def load_data():
    conn = sqlite3.connect('molkky.db')
    df = pd.read_sql_query("SELECT * FROM throw_logs", conn)
    conn.close()
    return df

# --- 2. 状態管理の初期化 ---
if 'obstacles' not in st.session_state:
    st.session_state.obstacles = {
        'nw': False, 'n': False, 'ne': False,
        'w': False,  'e': False,
        'sw': False, 's': False, 'se': False
    }

# --- 3. 画面全体の設定と、3列固定CSS ---
st.set_page_config(page_title="モルック投擲記録", layout="centered")

st.markdown("""
    <style>
    .block-container {
        padding-left: 8px !important;
        padding-right: 8px !important;
        padding-top: 1rem !important;
    }
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
    }
    div[data-testid="stHorizontalBlock"] > div {
        flex: 1 1 33.33% !important;
        max-width: 33.33% !important;
        min-width: 0px !important;
    }
    div.stButton > button {
        width: 100% !important;
        height: 55px !important;
        padding: 0px !important;
        font-size: 13px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 投擲データ入力")

# --- 4. 入力エリア：基本情報 ---
col_info1, col_info2 = st.columns(2)
with col_info1:
    target_no = st.selectbox("狙う番号", list(range(1, 13)), index=11)
with col_info2:
    dist = st.slider("距離 (m)", 3.0, 10.0, 3.5, 0.5)

st.divider()

# --- 5. 入力エリア：障害物配置 (3x3ボタン) ---
st.subheader("障害物配置")
st.caption("ターゲット周囲の状況をタップ（前＝自分に近い側）")

keys = [
    ['nw', 'n', 'ne'],
    ['w',  None, 'e'],
    ['sw', 's', 'se']
]
labels = {
    'nw': '奥左', 'n': '真奥', 'ne': '奥右',
    'w': '左', 'e': '右',
    'sw': '前左', 's': '真前', 'se': '前右'
}

for row in keys:
    cols = st.columns(3)
    for i, key in enumerate(row):
        if key is None:
            cols[i].button("🎯", disabled=True, key="center_target")
        else:
            is_active = st.session_state.obstacles[key]
            label = f"🚩 {labels[key]}" if is_active else labels[key]
            
            if cols[i].button(label, key=f"btn_{key}"):
                st.session_state.obstacles[key] = not st.session_state.obstacles[key]
                st.rerun()

st.divider()

# --- 6. 結果入力と保存処理 ---
success_val = st.radio("結果", ["成功", "失敗"], horizontal=True)

if st.button("記録を保存する", type="primary", width='stretch'):
    conn = sqlite3.connect('molkky.db')
    c = conn.cursor()
    c.execute('''INSERT INTO throw_logs 
                 (dist, target_no, is_success, n, ne, e, se, s, sw, w, nw, timestamp)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (dist, target_no, 1 if success_val == "成功" else 0,
               st.session_state.obstacles['n'], st.session_state.obstacles['ne'],
               st.session_state.obstacles['e'], st.session_state.obstacles['se'], 
               st.session_state.obstacles['s'], st.session_state.obstacles['sw'], 
               st.session_state.obstacles['w'], st.session_state.obstacles['nw'],
               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    
    for k in st.session_state.obstacles:
        st.session_state.obstacles[k] = False
    
    # 🚀 キャッシュをクリアして、新しいデータをグラフに即時反映させる
    st.cache_data.clear()
    st.success("データを保存しました！")
    st.rerun()

# --- 7. 成功率のグラフ表示（高速キャッシュ版） ---
st.divider()
st.subheader("📊 距離別の成功率実績")

# 🚀 キャッシュされた高速読込関数を使用
df = load_data()

if not df.empty:
    stats_df = df.groupby('dist')['is_success'].agg(['sum', 'count']).reset_index()
    stats_df['success_rate'] = (stats_df['sum'] / stats_df['count']) * 100
    stats_df['counts_text'] = stats_df['sum'].astype(str) + " / " + stats_df['count'].astype(str) + " 回"
    stats_df['dist_label'] = stats_df['dist'].astype(str) + "m"

    import altair as alt
    
    chart = alt.Chart(stats_df).mark_bar(color="#1f77b4").encode(
        x=alt.X('dist_label:N', title='投擲距離 (m)', sort=None),
        y=alt.Y('success_rate:Q', title='成功率 (%)', scale=alt.Scale(domain=[0, 100])),
        tooltip=[
            alt.Tooltip('dist_label:N', title='距離'),
            alt.Tooltip('success_rate:Q', title='成功率', format='.1f'),
            alt.Tooltip('counts_text:N', title='成功 / 試行回数')
        ]
    ).properties(
        height=300
    )
    
    st.altair_chart(chart, width='stretch')
    
    df_disp = df.copy()
    df_disp['結果'] = df_disp['is_success'].map({1: "○ 成功", 0: "× 失敗"})
    df_disp['距離'] = df_disp['dist'].astype(str) + "m"
    df_disp['狙った番号'] = df_disp['target_no'].astype(str) + "番"
    df_disp = df_disp.sort_values(by='timestamp', ascending=False)
    
    # --- 最新の5件表示 ---
    st.markdown("### 📜 最新の投擲履歴（5件）")
    st.dataframe(df_disp.head(5)[['timestamp', '狙った番号', '距離', '結果']], width='stretch')
    
    # --- 6件目以降の過去データ開閉 ---
    st.write("") 
    if len(df_disp) > 5:
        if st.checkbox("📁 6件目より過去のすべての履歴を表示する"):
            st.markdown("### 📚 過去の投擲履歴（全件）")
            st.dataframe(df_disp[['timestamp', '狙った番号', '距離', '結果']], width='stretch', height=300)
            
else:
    st.info("データを保存すると、ここに自動で成功率のグラフが生成されます。")