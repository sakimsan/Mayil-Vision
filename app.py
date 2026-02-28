import streamlit as st
import geopandas as gpd
from pathlib import Path
from src.database.db_manager import DBManager
from src.clients.osm_client import OSMClient
from src.utils import get_project_dir

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="Energy Intelligence Platform", layout="wide")

DB_PATH = Path("data/system/global_registry.sqlite")
db = DBManager(DB_PATH)
osm_client = OSMClient()

# --- SIDEBAR: Project Selection ---
st.sidebar.title("Navigation")
st.sidebar.markdown("---")

# Fetch all projects from DB to populate the selector
# Note: We'll add a helper to db_manager later to get all names
with db._get_connection() as conn:
    project_list = [row[0] for row in conn.execute("SELECT name FROM projects ORDER BY created_at DESC").fetchall()]

selected_project = st.sidebar.selectbox(
    "Select Active Project",
    ["-- Create New Project --"] + project_list
)

# --- MAIN INTERFACE ---
st.title("⚡ Energy Intelligence Platform")
st.markdown("Automated Infrastructure Monitoring via Multi-Sensor Satellite Fusion")

if selected_project == "-- Create New Project --":
    st.header("📂 Create New Monitoring Project")

    col1, col2 = st.columns(2)

    with col1:
        project_name = st.text_input("Project Name", placeholder="e.g., Berlin_North_Grid")
        method = st.radio("Inbound Data Method", ["OSM Wizard (Search)", "Manual GeoJSON Upload"])

    with col2:
        if method == "OSM Wizard (Search)":
            location_query = st.text_input("Location Search", placeholder="e.g., Hamburg, Germany")
            infra_type = st.multiselect("Infrastructure Types", ["line", "tower", "substation"], default=["line"])
        else:
            uploaded_file = st.file_uploader("Upload Infrastructure (GeoJSON)", type=["geojson"])

    if st.button("Initialize Analysis Pipeline"):
        if not project_name:
            st.error("Please provide a project name.")
        else:
            # 1. Create directory structure
            paths = get_project_dir(project_name)

            # 2. Handle Data Ingestion
            success = False
            if method == "OSM Wizard (Search)" and location_query:
                with st.spinner(f"Fetching {infra_type} data for {location_query} from OSM..."):
                    try:
                        # For simplicity, we fetch the first selected type
                        gdf = osm_client.fetch_power_data(location_query, infra_type[0])
                        osm_client.save_to_project(gdf, paths["raw"], "infrastructure")
                        success = True
                    except Exception as e:
                        st.error(f"OSM Fetch failed: {e}")

            elif method == "Manual GeoJSON Upload" and uploaded_file:
                with open(paths["raw"] / "infrastructure.geojson", "wb") as f:
                    f.write(uploaded_file.getbuffer())
                success = True

            # 3. Register in Database
            if success:
                db.register_project(project_name)
                st.success(f"Project '{project_name}' registered! The Background Worker will start the analysis shortly.")
                st.rerun()

else:
    # --- PROJECT DASHBOARD ---
    st.header(f"📊 Project: {selected_project}")

    # Show Project Status
    with db._get_connection() as conn:
        status = conn.execute("SELECT status FROM projects WHERE name = ?", (selected_project,)).fetchone()[0]

    st.info(f"Current Status: **{status}**")

    if status == "COMPLETED":
        st.subheader("Analysis Summary")
        # Load results from database
        results_df = db.get_results_for_project(selected_project)

        if not results_df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Hotspots", len(results_df))
            c2.metric("High Severity", len(results_df[results_df['severity'] == 'HIGH']))
            c3.metric("Medium Severity", len(results_df[results_df['severity'] == 'MEDIUM']))

            st.dataframe(results_df[['module_type', 'severity', 'description', 'detected_at']], use_container_width=True)

            # Placeholder for the Map (We will implement this in the /pages files)
            st.button("View Detailed Interactive Map", on_click=lambda: st.switch_page("pages/1_VegWatch_UI.py"))
        else:
            st.warning("No anomalies detected in this project area.")

    elif status == "PROCESSING":
        st.warning("Worker is currently analyzing satellite imagery. Please refresh in a few minutes.")
        if st.button("🔄 Check Status"):
            st.rerun()

    elif status == "PENDING":
        st.write("Project is in queue. Waiting for Worker to pick up the task.")