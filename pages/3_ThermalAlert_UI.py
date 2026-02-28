import streamlit as st
import leafmap.foliumap as leafmap
import pandas as pd
from pathlib import Path
from src.database.db_manager import DBManager

# --- CONFIGURATION ---
st.set_page_config(page_title="ThermalAlert Dashboard", layout="wide")

DB_PATH = Path("data/system/global_registry.sqlite")
db = DBManager(DB_PATH)

st.title("🌡️ ThermalAlert: Infrastructure Heat Monitoring")
st.markdown("Identification of thermal anomalies in substations and transformers using Landsat 8/9 TIRS.")

# --- PROJECT SELECTION ---
with db._get_connection() as conn:
    project_list = [row[0] for row in conn.execute("SELECT name FROM projects WHERE status='COMPLETED'").fetchall()]

if not project_list:
    st.warning("No completed projects available. Please ensure the worker has processed at least one project.")
    st.stop()

selected_project = st.sidebar.selectbox("Select Project", project_list)

# --- LOAD THERMAL DATA ---
results_df = db.get_results_for_project(selected_project, module="THERMAL")

if results_df.empty:
    st.info(f"No thermal anomalies detected in {selected_project}. All components operating within normal temperature ranges.")
else:
    # --- LAYOUT: Metrics and Map ---
    col_metrics, col_map = st.columns([1, 3])

    with col_metrics:
        st.subheader("Thermal Metrics")
        critical_count = len(results_df[results_df['severity'] == 'HIGH'])
        st.metric("Critical Hotspots", critical_count, delta=f"{critical_count} alerts", delta_color="inverse")

        st.write("---")
        st.write("**Active Alerts:**")
        # Displaying a list of alerts with color coding based on severity
        for _, row in results_df.iterrows():
            color = "🔴" if row['severity'] == "HIGH" else "🟠"
            st.markdown(f"{color} **{row['severity']}**: {row['description']}")

    with col_map:
        st.subheader("Anomalies Map (Landsat TIRS)")

        # Centering the map
        m = leafmap.Map(
            center=[results_df.iloc[0]['latitude'], results_df.iloc[0]['longitude']],
            zoom=15,
            google_map="HYBRID"
        )

        # Mapping hotspots with a 'heat' color scheme
        # HIGH = Red, MEDIUM = Orange
        m.add_points_from_xy(
            results_df,
            x="longitude",
            y="latitude",
            color_column="severity",
            palette=["#FF4B4B", "#FFA500"], # Custom Red and Orange
            icon_names=["fire"],
            add_legend=True
        )

        m.to_streamlit(height=600)



# --- TECHNICAL FOOTNOTE ---
st.divider()
st.caption("Data source: Landsat 8-9 OLI/TIRS Collection 2 Level-2. Analysis detects surface temperature deviations relative to the local mean.")

if st.button("⬅ Return to Dashboard"):
    st.switch_page("app.py")