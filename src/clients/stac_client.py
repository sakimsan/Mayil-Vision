import pystac_client
import planetary_computer
from typing import List, Optional

class STACClient:
    """
    Client to interact with Microsoft Planetary Computer STAC API.
    """
    def __init__(self):
        self.api_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
        # The client needs to sign requests to access the data assets
        self.client = pystac_client.Client.open(
            self.api_url,
            modifier=planetary_computer.sign_inplace
        )

    def search_imagery(self, bbox: List[float], datetime: str, collections: List[str], cloud_cover: int = 10):
        """
        Search for satellite imagery within a bounding box and time range.
        :param bbox: [min_lon, min_lat, max_lon, max_lat]
        :param datetime: "YYYY-MM-DD/YYYY-MM-DD"
        :param collections: e.g. ["sentinel-2-l2a"]
        :param cloud_cover: Max allowed cloud cover in percent
        """
        search = self.client.search(
            bbox=bbox,
            datetime=datetime,
            collections=collections,
            query={"eo:cloud_cover": {"lt": cloud_cover}}
        )
        return search.item_collection()