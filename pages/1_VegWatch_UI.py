import streamlit as st
import leafmap.foliumap as leafmap
import pandas as pd
from pathlib import Path
from src.database.db_manager import DBManager

# --- CONFIGURATION ---
st.set_page_config(page_title="VegWatch Analysis", layout="wide")

DB_PATH = Path("data/system/global_registry.sqlite")
db = DBManager(DB_PATH)

st.title("🌿 VegWatch: Vegetation Monitoring")
st.markdown("Detailed NDVI analysis and encroachment detection for power lines.")

# --- PROJECT SELECTION (Session Sync) ---
# We check if a project was already selected in the main app.py
with db._get_connection() as conn:
    project_list = [row[0] for row in conn.execute("SELECT name FROM projects WHERE status='COMPLETED'").fetchall()]

if not project_list:
    st.warning("No completed projects found. Please run the worker first.")
    st.stop()

selected_project = st.sidebar.selectbox("Switch Project", project_list)

# --- LOAD DATA ---
results_df = db.get_results_for_project(selected_project, module="VEG")

if results_df.empty:
    st.info(f"No vegetation anomalies found for project: {selected_project}")
else:
    # --- LAYOUT: Map and Table ---
    col_map, col_stats = st.columns([3, 1])

    with col_stats:
        st.subheader("Summary")
        st.metric("Detected Hotspots", len(results_df))

        # Filter by severity
        severity = st.selectbox("Filter by Severity", ["All", "HIGH", "MEDIUM", "LOW"])
        if severity != "All":
            display_df = results_df[results_df['severity'] == severity]
        else:
            display_df = results_df

        st.write("Recent Alerts:")
        st.dataframe(display_df[['severity', 'description']], hide_index=True)

    with col_map:
        st.subheader("Interactive Hotspot Map")

        # Initialize the map centered on the first result
        m = leafmap.Map(
            center=[results_df.iloc[0]['latitude'], results_df.iloc[0]['longitude']],
            zoom=14,
            google_map="HYBRID" # Better for seeing actual trees
        )

        # Add hotspots as markers
        # In a real app, you would add the actual satellite tile here too
        m.add_points_from_xy(
            display_df,
            x="longitude",
            y="latitude",
            color_column="severity",
            icon_names=["exclamation-triangle"],
            add_legend=True
        )

        m.to_streamlit(height=600)

# --- ACTIONS ---
st.divider()
if st.button("⬅ Back to Global Overview"):
    st.switch_page("app.py")