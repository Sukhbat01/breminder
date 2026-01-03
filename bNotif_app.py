import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Fruit Stock Dashboard", page_icon="🍎", layout="wide")

cert_content = os.environ.get("CA_CERT_CONTENT")
if cert_content:
    with open("ca.pem", "w") as f:
        f.write(cert_content)

@st.cache_resource
def get_engine():
    db_url = os.environ.get("DATABASE_URL")
    return create_engine(
        db_url, 
        connect_args={"ssl_ca": "ca.pem"}, 
        pool_recycle=3600, 
        pool_pre_ping=True
    )

engine = get_engine()

@st.cache_data(ttl=600)
def get_data():
    try:
        query = "SELECT fruit_name, rarity, detected_at FROM fruit_history ORDER BY detected_at DESC"
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        if not df.empty:
            df['detected_at'] = pd.to_datetime(df['detected_at']) + pd.Timedelta(hours=8)
        return df
    
    except Exception as e:
        st.error(f"Could not connect to Aiven: {e}")
        return pd.DataFrame()

st.title("Blox Fruits Stock Intelligence")
st.markdown("---")

if st.sidebar.button("Force Refresh"):
    st.cache_data.clear()
    st.rerun()

df = get_data()

if not df.empty:
    col1, col2, col3 = st.columns(3)
    
    total_detections = len(df)
    latest_fruit = df['fruit_name'].iloc[0]
    latest_time = df['detected_at'].iloc[0].strftime("%Y-%m-%d %H:%M")

    col1.metric("Total Detections", total_detections)
    col2.metric("Latest Stock", latest_fruit)
    col3.metric("Last Update", latest_time)

    st.markdown("---")

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Rarity Distribution")
        rarity_counts = df['rarity'].value_counts()
        st.bar_chart(rarity_counts)

    with right_col:
        st.subheader("Most Frequent Rare Fruits")
        top_fruits = df[df['rarity'].isin(['Mythical', 'Legendary'])]['fruit_name'].value_counts()
        st.bar_chart(top_fruits)

    st.subheader("Live Detection History")
    def color_rarity(val):
        if val == 'Mythical': return 'color: #ff4b4b' 
        elif val == 'Legendary': return 'color: #fca311' 
        return 'color: white'

    st.dataframe(
        df.style.applymap(color_rarity, subset=['rarity']),
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("Database is empty. Run your submarine script to start collecting data!")

if not df.empty:
    last_update = df['detected_at'].max().strftime('%Y-%m-%d %H:%M:%S')
    st.subheader(f"🕒 Last Updated: {last_update} (Local Time)")

st.sidebar.info("Bot Status: 🛰️ Online")
st.sidebar.write(f"Connected to: `{os.getenv('DB_HOST')}`")