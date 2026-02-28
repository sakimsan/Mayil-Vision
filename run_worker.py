import time
import logging
import geopandas as gpd
from pathlib import Path

# Import our custom infrastructure
from src.database.db_manager import DBManager
from src.clients.osm_client import OSMClient
from src.clients.stac_client import STACClient
from src.utils import get_project_dir

# Import the analysis modules
from modules.veg_watch import VegWatch

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # 1. Initialize Infrastructure
    DB_PATH = Path("data/system/global_registry.sqlite")
    db = DBManager(DB_PATH)
    osm = OSMClient()
    stac = STACClient()

    # 2. Initialize Analysis Modules
    veg_watch = VegWatch(stac)

    logger.info("Worker 2.0 started. Monitoring for pending analysis tasks...")

    while True:
        pending_projects = db.get_pending_projects()

        for project_name in pending_projects:
            logger.info(f"--- Starting Analysis: {project_name} ---")

            try:
                db.update_project_status(project_name, "PROCESSING")
                paths = get_project_dir(project_name)

                # A. Ensure Raw Data exists
                raw_file = paths["raw"] / "infrastructure.geojson"
                if not raw_file.exists():
                    logger.info(f"[{project_name}] Fetching OSM data...")
                    gdf = osm.fetch_power_data(project_name)
                    osm.save_to_project(gdf, paths["raw"], "infrastructure")
                else:
                    gdf = gpd.read_file(raw_file)

                # B. Run Vegetation Analysis
                logger.info(f"[{project_name}] Running VegWatch (Sentinel-2)...")
                veg_results = veg_watch.run_analysis(project_name, gdf)

                # C. Save Results to Database
                for res in veg_results:
                    db.save_analysis_result(
                        project_name=project_name,
                        module="VEG",
                        lat=res["lat"],
                        lon=res["lon"],
                        sev=res["severity"],
                        desc=res["description"]
                    )

                logger.info(f"[{project_name}] Found {len(veg_results)} vegetation hotspots.")

                # D. Finalize Project
                db.update_project_status(project_name, "COMPLETED")
                logger.info(f"Successfully finished all modules for: {project_name}")

            except Exception as e:
                logger.error(f"Critical error in project {project_name}: {str(e)}")
                db.update_project_status(project_name, "FAILED")

        # Wait before next check
        time.sleep(30)

if __name__ == "__main__":
    main()