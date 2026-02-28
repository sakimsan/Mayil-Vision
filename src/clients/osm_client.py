import osmnx as ox
import geopandas as gpd
from pathlib import Path

class OSMClient:
    """
    Client to fetch infrastructure data from OpenStreetMap using OSMnx.
    """
    def fetch_power_data(self, place_name: str, power_type: str = "line") -> gpd.GeoDataFrame:
        """
        Fetch power infrastructure for a given location.
        :param place_name: City or Region name (e.g., "Berlin, Germany")
        :param power_type: OSM tag value (e.g., "line", "tower", "substation")
        """
        # Define tags for the Overpass API query
        tags = {"power": power_type}

        # Download geometries from OSM
        print(f"Fetching {power_type} data for {place_name}...")
        gdf = ox.features_from_place(place_name, tags=tags)

        # Filter for relevant geometries and drop unneeded columns
        relevant_geoms = ['LineString', 'MultiLineString', 'Point']
        gdf = gdf[gdf.geometry.type.isin(relevant_geoms)].copy()

        return gdf

    def save_to_project(self, gdf: gpd.GeoDataFrame, project_raw_path: Path, filename: str):
        """
        Saves the GeoDataFrame as a GeoJSON file in the project directory.
        """
        output_file = project_raw_path / f"{filename}.geojson"
        gdf.to_file(output_file, driver='GeoJSON')
        print(f"Data saved to {output_file}")