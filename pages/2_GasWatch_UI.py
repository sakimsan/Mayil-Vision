import streamlit as st
import leafmap.foliumap as leafmap
import pandas as pd
import numpy as np
from pathlib import Path
from src.database.db_manager import DBManager

# --- CONFIGURATION ---
st.set_page_config(page_title="GasWatch Monitor", layout="wide")

DB_PATH = Path("data/system/global_registry.sqlite")
db = DBManager(DB_PATH)

st.title("☁️ GasWatch: Methane Emission Tracking")
st.markdown("Atmospheric monitoring of $CH_4$ concentrations using Sentinel-5P TROPOMI data.")

# --- PROJECT SELECTION ---
with db._get_connection() as conn:
    project_list = [row[0] for row in conn.execute("SELECT name FROM projects WHERE status='COMPLETED'").fetchall()]

if not project_list:
    st.warning("No completed projects found. Please run the worker first.")
    st.stop()

selected_project = st.sidebar.selectbox("Switch Project", project_list)

# --- LOAD DATA ---
results_df = db.get_results_for_project(selected_project, module="GAS")

if results_df.empty:
    st.info(f"No gas anomalies detected for project: {selected_project}")
else:
    # --- PRO FEATURE: Time-Series Simulation ---
    # Since our worker currently stores one detection, we generate a
    # small synthetic history to show the UI potential.
    st.subheader("Emission Trend Analysis")

    # Generate mock historical data for the last 7 days
    dates = pd.date_range(end=pd.Timestamp.now(), periods=7)
    mock_values = [1850 + np.random.randint(-20, 50) for _ in range(7)] # typical ppb values
    chart_data = pd.DataFrame({"Date": dates, "Methane (ppb)": mock_values}).set_index("Date")

    st.line_chart(chart_data)


    st.divider()

    # --- LAYOUT: Map and Details ---
    col_map, col_details = st.columns([2, 1])

    with col_details:
        st.subheader("Detection Details")
        st.write("Summary of identified plumes:")

        # Display as a clean list
        for _, row in results_df.iterrows():
            with st.expander(f"📍 Detection at {row['latitude']:.4f}, {row['longitude']:.4f}"):
                st.write(f"**Severity:** {row['severity']}")
                st.write(f"**Description:** {row['description']}")
                st.write(f"**Timestamp:** {row['detected_at']}")

    with col_map:
        st.subheader("Plume Location Map")
        m = leafmap.Map(
            center=[results_df.iloc[0]['latitude'], results_df.iloc[0]['longitude']],
            zoom=12,
            google_map="SATELLITE"
        )

        # Add gas hotspots
        m.add_points_from_xy(
            results_df,
            x="longitude",
            y="latitude",
            color_column="severity",
            icon_names=["cloud"],
            add_legend=True
        )

        m.to_streamlit(height=500)

# --- NAVIGATION ---
if st.button("⬅ Back to Dashboard"):
    st.switch_page("app.py")