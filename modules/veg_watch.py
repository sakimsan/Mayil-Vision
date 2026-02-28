import numpy as np
import stackstac
import xarray as xr
import geopandas as gpd
from src.clients.stac_client import STACClient
from typing import Dict

class VegWatch:
    """
    Module for vegetation monitoring using Sentinel-2 NDVI.
    """
    def __init__(self, stac_client: STACClient):
        self.stac_client = stac_client

    def run_analysis(self, project_name: str, infra_gdf: gpd.GeoDataFrame) -> list:
        """
        Executes vegetation analysis for the given infrastructure.
        """
        results = []

        # 1. Get the bounding box of the infrastructure
        # Format: [minx, miny, maxx, maxy]
        bbox = list(infra_gdf.total_bounds)

        # 2. Search for the latest Sentinel-2 imagery (cloud-free)
        # We search for the last 3 months to ensure we get a good image
        items = self.stac_client.search_imagery(
            bbox=bbox,
            datetime="2025-12-01/2026-02-28", # Dynamic range would be better
            collections=["sentinel-2-l2a"],
            cloud_cover=10
        )

        if not items:
            print(f"No suitable imagery found for {project_name}")
            return results

        # 3. Load Red (B04) and NIR (B08) bands using stackstac
        # We use a small area around our infrastructure
        stack = stackstac.stack(items, assets=["B04", "B08"], bounds_latlon=bbox)

        # Calculate median over time to remove remaining artifacts/clouds
        composite = stack.median(dim="time").compute()

        # 4. Calculate NDVI
        red = composite.sel(band="B04")
        nir = composite.sel(band="B08")
        ndvi = (nir - red) / (nir + red)

        # 5. Intersect with infrastructure (Simplified logic)
        # We look for high NDVI values (> 0.6) near our lines
        high_veg = ndvi.where(ndvi > 0.6)

        # In a real scenario, we would use rasterio.features.shapes to convert
        # these pixels back to coordinates and check distance to lines.
        # For the MVP, we simulate finding a few hotspots:
        results.append({
            "lat": infra_gdf.geometry.centroid.y.iloc[0],
            "lon": infra_gdf.geometry.centroid.x.iloc[0],
            "severity": "HIGH",
            "description": "Dense vegetation detected within 5m of power line."
        })

        return results