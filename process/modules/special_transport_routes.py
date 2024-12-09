import geopandas as gpd
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
#from shapely.validation import explain_validity
from os import path
from shapely.validation import make_valid
from shapely.geometry import MultiPolygon, Polygon, GeometryCollection

from modules.config import Config
from modules.gis_processing import GisProcessor
from modules.common import *

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


class SpecialTransportRoutes(GisProcessor):
    """Process special transport routes."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._process_result_lines = None
        self._process_result_polygons = None
        self._debug_result_lines = None
        self._module = "special_transport_routes"

        file_name = cfg.local_file(self._module)
        self._store_original_data = cfg.store_orinal_data(self._module)
        self._ylre_street_class_buffer = cfg.ylre_street_class_buffer(self._module)

        # check that ylre_katualueet file is available
        if not path.exists(self._cfg.target_buffer_file("ylre_katualueet")):
            raise FileNotFoundError("ylre katualueet polygon not found")

        # Loading ylre_katualueet dataset
        ylre_katualueet_filename = cfg.target_buffer_file("ylre_katualueet")
        self._ylre_katualueet = gpd.read_file(ylre_katualueet_filename)
        self._ylre_katualueet_sindex = self._ylre_katualueet.sindex

        # Buffering configuration
        self._buffers = self._cfg.buffer_class_values(self._module)

        if len(self._buffers) != 3:
            raise ValueError("Unknown number of buffer values")

        # Buffering classes
        self._buffer_class_vaylatyp2_values = {
            "maantie": ["Maantie",],
            "katu": ["Katu",],
            "yksityistie": ["Yksityistie", "Kevyen liikenteen väylä"],
        }

        # Following columns can be dropped from liikennevaylat data
        self._dropped_columns = [
            "nimi_1",
            "pnro",
            "kunta",
            "vaylatyypp",
            "toiminnall",
            "toiminnal2",
            "muuntaja2",
            "tuleva2",
            "varareitti2",
            "muokattu",
            "datanomistaja",
            "paivitetty_tietopalveluun",
            "ylre_class",
            "kadun_nimi",
            "gml_id",
            "id",
        ]

        self._lines = gpd.read_file(file_name)
        self._lines["vaylatyyp2"] = self._lines["vaylatyyp2"].str.replace("\n", "")

        # Drop one invalid data line
        self._lines = self._lines.drop(self._lines[(self._lines["id"] == 1500) | ((self._lines["nimi_1"] == "Metsälä-Etelä-Oulunkylä") & (self._lines["vaylatyyp2"] == "Kevyen liikenteen väylä"))].index)

        self._orig = self._lines

    def _keep_rows_base_on_hierarchy_list(self, types, shapes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        retval = shapes.copy()
        mask = retval["hierarkia"].isin(types)
        retval = retval[mask]
        return retval

    def _drop_not_used_classes_base_on_main_and_sub_types(self, main_and_sub_types, shapes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        retval = shapes.copy()
        for main_type, sub_types in main_and_sub_types.items():
            for sub_type in sub_types:
                retval.drop(
                    retval[
                        (retval["paatyyppi"] == main_type)
                        & (retval["alatyyppi"] == sub_type)
                    ].index,
                    axis=0,
                    inplace=True,
                )

        return retval

    def _drop_unnecessary_columns(self, columns_to_drop: list[str], shapes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        retval = shapes.copy()
        retval.drop(columns_to_drop, axis=1, inplace=True)

        return retval

    def _buffering(self, lines: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        # Buffer lines
        target_infra_polys = lines.copy()
        retval = target_infra_polys[0:0]
        for buffer_class, buffer_value in self._buffers.items():
            buffered_items = target_infra_polys.loc[target_infra_polys["vaylatyyp2"].isin(self._buffer_class_vaylatyp2_values[buffer_class])].copy()
            buffered_items["geometry"] = buffered_items.buffer(buffer_value)
            retval = gpd.GeoDataFrame(pd.concat([retval, buffered_items], ignore_index=True))

        return retval

    def _check_and_set_ylre_classes_id(self, lines: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        attrs = ["ylre_class", "kadun_nimi"]
        ylre_katualueet_dissolved = self._ylre_katualueet.dissolve(by=attrs)
        ylre_katualueet_dissolved["geometry"] = ylre_katualueet_dissolved.buffer(15)
        joined_result = gpd.sjoin(lines, ylre_katualueet_dissolved, predicate='within')

        retval = lines.merge(joined_result[['gml_id','ylre_class','kadun_nimi']], how='left', left_on='gml_id', right_on='gml_id')

        return retval

    def _makeValid(self, data, geom_column):
        data[geom_column] = data.apply(lambda row: make_valid(row[geom_column]) if not row[geom_column].is_valid else row[geom_column], axis=1)
        return(data)

    def process(self):
        self._process_result_lines = self._lines

        # Drop dublicates
        self._process_result_lines.drop_duplicates(subset=["gml_id"], inplace=True)

        # Mark objects which are within YLRE katualueet areas
        self._process_result_lines = self._check_and_set_ylre_classes_id(self._process_result_lines)

        # Buffer lines using buffer configuration
        target_infra_polys = self._process_result_lines.copy()
        target_infra_polys = self._buffering(target_infra_polys)

        # Clip by using YLRE katuosa areas
        geometryToClipAttrsDissolve = ["mitlev", "mitpit", "mitkor", "muuntaja", "tuleva", "varareitti", "vaylatyyp2", "nimi"]
        maskAttrsDissolve = ["ylre_class"]
        target_infra_polys = clipAreasByAreas(target_infra_polys, self._ylre_katualueet, geometryToClipAttrsDissolve, maskAttrsDissolve, "gml_id", "ylre_class", False)
        target_infra_polys = target_infra_polys[target_infra_polys.geometry.type != 'Point']

        # Drop unnecessary columns
        target_infra_polys = self._drop_unnecessary_columns(
            self._dropped_columns, target_infra_polys
        )

        # Dissolve geometries base on attributes listed
        attrs = ["mitlev", "mitpit", "mitkor", "muuntaja", "tuleva", "varareitti", "vaylatyyp2", "nimi", ]
        for attr in attrs:
            target_infra_polys[attr] = target_infra_polys[attr].fillna("")

        target_infra_polys = target_infra_polys.dissolve(by=attrs, aggfunc="sum", as_index=False)

        # Explode multipolygon to polygons
        target_infra_polys = target_infra_polys.explode(ignore_index=True)

        # Validate geometry
        target_infra_polys = self._makeValid(target_infra_polys, "geometry")
        target_infra_polys = makeValid(target_infra_polys)

        target_infra_polys = target_infra_polys[~target_infra_polys.is_empty]
        # save to instance
        self._process_result_polygons = target_infra_polys

    def persist_to_database(self):
        connection = create_engine(self._cfg.pg_conn_uri(), future=True)

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
        # Central transport routes as debug material
        target_infra_file_name = self._cfg.target_file(self._module)
        target_lines = self._process_result_lines.reset_index(drop=True)
        target_lines.to_file(target_infra_file_name, driver="GPKG")

        # tormays GIS material
        target_buffer_file_name = self._cfg.target_buffer_file(self._module)
        tormays_polygons = self._process_result_polygons.reset_index(drop=True)
        tormays_polygons.to_file(target_buffer_file_name, driver="GPKG")