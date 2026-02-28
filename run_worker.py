import time
import logging
import geopandas as gpd
from pathlib import Path

# --- INTERNAL IMPORTS ---
from src.database.db_manager import DBManager
from src.clients.osm_client import OSMClient
from src.clients.stac_client import STACClient
from src.utils import get_project_dir

# --- ANALYSIS MODULES ---
from modules.veg_watch import VegWatch
from modules.gas_watch import GasWatch
from modules.thermal_alert import ThermalAlert
from modules.ground_guard import GroundGuard

# Configure logging for professional backend monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # 1. Initialize System Infrastructure
    # Ensure the system directory exists for the global database
    DB_PATH = Path("data/system/global_registry.sqlite")
    db = DBManager(DB_PATH)

    # Initialize API Clients
    osm = OSMClient()
    stac = STACClient()

    # 2. Initialize All 4 Analysis Engines
    veg_watch = VegWatch(stac)
    gas_watch = GasWatch(stac)
    thermal_alert = ThermalAlert(stac)
    ground_guard = GroundGuard(stac)

    logger.info("Worker 4.0 (Full Suite) started. Polling for infrastructure projects...")

    while True:
        # Check for projects that need processing
        pending_projects = db.get_pending_projects()

        for project_name in pending_projects:
            logger.info(f"🚀 Starting Full-Spectrum Analysis for: {project_name}")

            try:
                # Lock project by setting status to PROCESSING
                db.update_project_status(project_name, "PROCESSING")
                paths = get_project_dir(project_name)

                # --- STEP A: Infrastructure Data Ingestion ---
                raw_file = paths["raw"] / "infrastructure.geojson"
                if not raw_file.exists():
                    logger.info(f"[{project_name}] Fetching OSM data as fallback...")
                    gdf = osm.fetch_power_data(project_name)
                    osm.save_to_project(gdf, paths["raw"], "infrastructure")
                else:
                    gdf = gpd.read_file(raw_file)

                # --- STEP B: Vegetation Monitoring (Sentinel-2) ---
                logger.info(f"[{project_name}] Executing VegWatch (NDVI)...")
                veg_results = veg_watch.run_analysis(project_name, gdf)
                for res in veg_results:
                    db.save_analysis_result(project_name, "VEG", res["lat"], res["lon"], res["severity"], res["description"])

                # --- STEP C: Methane Emission Monitoring (Sentinel-5P) ---
                logger.info(f"[{project_name}] Executing GasWatch (CH4)...")
                gas_results = gas_watch.run_analysis(project_name, gdf)
                for res in gas_results:
                    db.save_analysis_result(project_name, "GAS", res["lat"], res["lon"], res["severity"], res["description"])

                # --- STEP D: Thermal Anomaly Detection (Landsat 8/9) ---
                logger.info(f"[{project_name}] Executing ThermalAlert (LST)...")
                thermal_results = thermal_alert.run_analysis(project_name, gdf)
                for res in thermal_results:
                    db.save_analysis_result(project_name, "THERMAL", res["lat"], res["lon"], res["severity"], res["description"])

                # --- STEP E: Ground Stability Monitoring (Sentinel-1 SAR) ---
                logger.info(f"[{project_name}] Executing GroundGuard (Radar)...")
                ground_results = ground_guard.run_analysis(project_name, gdf)
                for res in ground_results:
                    db.save_analysis_result(project_name, "GROUND", res["lat"], res["lon"], res["severity"], res["description"])

                # --- STEP F: Finalization ---
                db.update_project_status(project_name, "COMPLETED")
                total_alerts = len(veg_results) + len(gas_results) + len(thermal_results) + len(ground_results)
                logger.info(f"✅ {project_name} finished. Total hotspots archived: {total_alerts}")

            except Exception as e:
                logger.error(f"❌ Critical error in {project_name}: {str(e)}")
                db.update_project_status(project_name, "FAILED")

        # Cycle wait time
        time.sleep(30)

if __name__ == "__main__":
    main()