import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from os import path
from shapely.validation import make_valid

from modules.config import Config
from modules.gis_processing import GisProcessor
from modules.common import *

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


class CriticalAreas(GisProcessor):
    """Process critical areas."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._process_result_lines = None
        self._process_result_polygons = None
        self._debug_result_lines = None
        self._module = "critical_areas"

        self._store_original_data = cfg.store_orinal_data(self._module)

        self._areas = gpd.read_file("/local_data/tormays_critical_area_polys.gpkg")
        self._orig = self._areas

    def process(self):
        self._process_result_polygons = self._areas

    def persist_to_database(self):
        connection = create_engine(self._cfg.pg_conn_uri())

        if self._store_original_data is not False:
            self._orig.rename_geometry('geom', inplace=True)
            # persist original data
            self._orig.to_postgis(
                self._store_original_data,
                connection,
                "public",
                if_exists="replace",
                index=True,
                index_label="fid",
                )

    def save_to_file(self):
        """Save processing results to file."""

        # tormays GIS material
        target_buffer_file_name = self._cfg.target_buffer_file(self._module)
        tormays_polygons = self._process_result_polygons.reset_index(drop=True)
        tormays_polygons.to_file(target_buffer_file_name, driver="GPKG")