import time
import logging
from pathlib import Path
from src.database.db_manager import DBManager
from src.clients.osm_client import OSMClient
from src.utils import get_project_dir

# Setup logging to see what the worker is doing in the console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Configuration
    DB_PATH = Path("data/system/global_registry.sqlite")
    db = DBManager(DB_PATH)
    osm = OSMClient()

    logger.info("Worker started. Waiting for pending projects...")

    while True:
        # 1. Check database for projects with status 'PENDING'
        pending_projects = db.get_pending_projects()

        for project_name in pending_projects:
            logger.info(f"Processing project: {project_name}")

            try:
                # Update status to show we are working on it
                db.update_project_status(project_name, "PROCESSING")

                # Get project paths
                paths = get_project_dir(project_name)

                # 2. Check if raw data exists, otherwise fetch from OSM
                # Note: In a real scenario, we might check if a file was uploaded first
                raw_file = paths["raw"] / "infrastructure.geojson"
                if not raw_file.exists():
                    logger.info(f"No raw data found for {project_name}. Triggering OSM Wizard...")
                    # For this example, we assume the project name is the location
                    # In the final UI, we will store the specific location in the DB
                    gdf = osm.fetch_power_data(project_name)
                    osm.save_to_project(gdf, paths["raw"], "infrastructure")

                # 3. RUN ANALYSIS MODULES (Placeholders for now)
                # This is where we will later call veg_watch.run(), gas_watch.run() etc.
                logger.info(f"Running analysis modules for {project_name}...")

                # Simulating work...
                time.sleep(2)

                # 4. Finalize
                db.update_project_status(project_name, "COMPLETED")
                logger.info(f"Successfully finished project: {project_name}")

            except Exception as e:
                logger.error(f"Error processing {project_name}: {str(e)}")
                db.update_project_status(project_name, "FAILED")

        # Wait 30 seconds before checking the database again
        time.sleep(30)

if __name__ == "__main__":
    main()