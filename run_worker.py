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

# Configure logging for professional console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # 1. Initialize System Infrastructure
    DB_PATH = Path("data/system/global_registry.sqlite")
    db = DBManager(DB_PATH)
    osm = OSMClient()
    stac = STACClient()

    # 2. Initialize Analysis Engines
    veg_watch = VegWatch(stac)
    gas_watch = GasWatch(stac)

    logger.info("Worker 2.5 started. Polling database for new infrastructure projects...")

    while True:
        # Fetch all projects marked as 'PENDING'
        pending_projects = db.get_pending_projects()

        for project_name in pending_projects:
            logger.info(f"🚀 Starting Multi-Sensor Analysis for: {project_name}")

            try:
                # Update status to block other workers/processes
                db.update_project_status(project_name, "PROCESSING")
                paths = get_project_dir(project_name)

                # --- STEP A: Infrastructure Data Ingestion ---
                raw_file = paths["raw"] / "infrastructure.geojson"
                if not raw_file.exists():
                    logger.info(f"[{project_name}] No local data. Fetching from OpenStreetMap...")
                    gdf = osm.fetch_power_data(project_name)
                    osm.save_to_project(gdf, paths["raw"], "infrastructure")
                else:
                    gdf = gpd.read_file(raw_file)

                # --- STEP B: Vegetation Monitoring (Sentinel-2) ---
                logger.info(f"[{project_name}] Executing VegWatch (NDVI Analysis)...")
                veg_results = veg_watch.run_analysis(project_name, gdf)
                for res in veg_results:
                    db.save_analysis_result(project_name, "VEG", res["lat"], res["lon"], res["severity"], res["description"])

                # --- STEP C: Methane Emission Monitoring (Sentinel-5P) ---
                logger.info(f"[{project_name}] Executing GasWatch (CH4 Detection)...")
                gas_results = gas_watch.run_analysis(project_name, gdf)
                for res in gas_results:
                    db.save_analysis_result(project_name, "GAS", res["lat"], res["lon"], res["severity"], res["description"])

                # --- STEP D: Finalization ---
                db.update_project_status(project_name, "COMPLETED")
                logger.info(f"✅ Project {project_name} successfully processed. {len(veg_results) + len(gas_results)} hotspots found.")

            except Exception as e:
                logger.error(f"❌ Critical failure in project {project_name}: {str(e)}")
                db.update_project_status(project_name, "FAILED")

        # Sleep for 30 seconds to avoid high CPU load / API rate limits
        time.sleep(30)

if __name__ == "__main__":
    main()