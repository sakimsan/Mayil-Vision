import streamlit as st
import leafmap.foliumap as leafmap
import pandas as pd
from pathlib import Path
from src.database.db_manager import DBManager

# --- CONFIGURATION ---
st.set_page_config(page_title="GroundGuard Monitoring", layout="wide")

DB_PATH = Path("data/system/global_registry.sqlite")
db = DBManager(DB_PATH)

st.title("🛰️ GroundGuard: Ground Stability & Radar Analysis")
st.markdown("Monitoring of ground subsidence and surface deformation using Sentinel-1 SAR (Synthetic Aperture Radar).")

# --- PROJECT SELECTION ---
with db._get_connection() as conn:
    project_list = [row[0] for row in conn.execute("SELECT name FROM projects WHERE status='COMPLETED'").fetchall()]

if not project_list:
    st.warning("No completed projects found. Please run the worker to generate stability data.")
    st.stop()

selected_project = st.sidebar.selectbox("Select Project", project_list)

# --- LOAD RADAR DATA ---
results_df = db.get_results_for_project(selected_project, module="GROUND")

if results_df.empty:
    st.info(f"No significant ground movement detected in {selected_project}. Infrastructure foundations appear stable.")
else:
    # --- LAYOUT: Stability Overview and Map ---
    col_info, col_map = st.columns([1, 2])

    with col_info:
        st.subheader("Stability Analysis")
        st.write("Radar backscatter analysis indicates potential surface changes at specific coordinates.")

        # Displaying the findings in a clear list
        for idx, row in results_df.iterrows():
            st.warning(f"**Anomaly #{idx+1}**")
            st.write(f"Location: {row['latitude']:.4f}, {row['longitude']:.4f}")
            st.write(f"Status: **{row['severity']} Risk**")
            st.write(f"Observation: {row['description']}")
            st.write("---")

        st.info("💡 **Tip:** SAR (Synthetic Aperture Radar) is all-weather capable and can detect movements through clouds and darkness.")

    with col_map:
        st.subheader("Deformation Map")

        # Initialize map
        m = leafmap.Map(
            center=[results_df.iloc[0]['latitude'], results_df.iloc[0]['longitude']],
            zoom=14,
            google_map="HYBRID"
        )

        # Plot radar anomalies
        # We use a distinct icon to differentiate radar from thermal or gas
        m.add_points_from_xy(
            results_df,
            x="longitude",
            y="latitude",
            color_column="severity",
            icon_names=["info-circle"],
            add_legend=True
        )

        m.to_streamlit(height=600)



# --- FOOTER ---
if st.button("⬅ Back to Main Dashboard"):
    st.switch_page("app.py")