import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text

from modules.config import Config
from modules.gis_processing import GisProcessor

# SettingWithCopyWarning warning disabling
pd.options.mode.chained_assignment = None

# Select only following tag values:
# tram = Urban tram
# light_rail = Light rail

TRAM_TYPES = ["tram", "light_rail"]

# Following commented lines kept as a backup of the older implementation where was different version of gdal used.
#def dict_values_to_list(d: dict) -> dict:
#    """Transform dict values to list."""
#    return {k: [v] for k, v in d.items()}
#
#
#def other_tag_to_dict(tags: str) -> dict:
#    """Split OSM tags to dict."""
#    tags = tags[1:-1]
#    return {
#        k: v for k, v in [s.split('"=>"') for s in tags.split('","')] if v is not None
#    }

class TramInfra(GisProcessor):
    """Process tram infra."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._process_result_lines = None
        self._process_result_polygons = None
        self._debug_result_lines = None
        self._orig = None
        # Loading ylre_katualueet dataset
        ylre_katualueet_filename = cfg.target_buffer_file("ylre_katualueet")
        self._ylre_katualueet = gpd.read_file(ylre_katualueet_filename)
        self._ylre_katualueet_sindex = self._ylre_katualueet.sindex

        self._module = "tram_infra"
        self._store_original_data = cfg.store_orinal_data(self._module)
        file_name = cfg.local_file(self._module)
        self._lines = gpd.read_file(file_name)

    def _clipAreasByAreas(self, geometryToClip: gpd.GeoDataFrame, mask: gpd.GeoDataFrame, geometryToClipAttrsDissolve, maskAttrsDissolve, mergeIdField, geometryToClipCheckAttr=None) -> gpd.GeoDataFrame:
        geometry = geometryToClip[~geometryToClip.is_empty]
        for attr in maskAttrsDissolve:
            mask[attr] = mask[attr].fillna("")

        if maskAttrsDissolve:
            mask_dissolved = mask.dissolve(by=maskAttrsDissolve, as_index=False)
        else:
            mask_dissolved = mask

        mask_dissolved = mask_dissolved.explode(ignore_index=True)

        if geometryToClipCheckAttr is not None:
            geometryToClipOnlyCheckObjects = geometry[geometry[geometryToClipCheckAttr].notnull()]
            geometryToClipNotCheckObjects = geometry.loc[~geometry[geometryToClipCheckAttr].notnull()]
        else:
            geometryToClipOnlyCheckObjects = geometry

        geometryToClipOnlyCheckObjects = geometryToClipOnlyCheckObjects.explode(ignore_index=True)
        # Actual clipping:
        clipped_result=gpd.clip(geometryToClipOnlyCheckObjects, mask_dissolved)
        clipped_result = clipped_result.explode(ignore_index=True)
        clipped_result.geometry = clipped_result.apply(lambda row: make_valid(row.geometry) if not row.geometry.is_valid else row.geometry, axis=1)
        geometryToClipOnlyCheckObjects.geometry = geometryToClipOnlyCheckObjects.apply(lambda row: make_valid(row.geometry) if not row.geometry.is_valid else row.geometry, axis=1)

        # Getting objects which were not clipped
        merged = geometryToClipOnlyCheckObjects.merge(clipped_result, how="outer", indicator=True, on=mergeIdField, suffixes=("", "_right"))
        not_clipped = merged[merged["_merge"] == "left_only"].copy()
        not_clipped.drop("_merge", axis=1, inplace=True)
        common_columns = set(geometryToClipOnlyCheckObjects.columns).intersection(not_clipped.columns)
        common_columns.add(geometryToClipOnlyCheckObjects.geometry.name)
        common_columns_list = list(common_columns)
        not_clipped = not_clipped[common_columns_list].copy()

        # Adding clipped results to objects which were not checked at all
        if geometryToClipCheckAttr is not None:
            retval = gpd.GeoDataFrame(pd.concat([geometryToClipNotCheckObjects, clipped_result], ignore_index=True))
        else:
            retval = clipped_result

        # Adding not clipped objects
        retval = gpd.GeoDataFrame(pd.concat([retval, not_clipped], ignore_index=True))
        for attr in geometryToClipAttrsDissolve:
            retval[attr] = retval[attr].fillna("")
        if geometryToClipAttrsDissolve:
            retval = retval.dissolve(by=geometryToClipAttrsDissolve, as_index=False)
        retval = retval.explode(ignore_index=True)

        return retval

    def process(self):
        lines = self._lines
        # New implementation of getting only tram lines:
        trams = lines.loc[lines["railway"].isin(TRAM_TYPES)]

        # Following commented lines kept as a backup of the older implementation where was different version of gdal used.
        #lines_with_tags = lines[~lines.other_tags.isna()].copy()

        #lines_with_tags["tag_dict"] = lines_with_tags.apply(
        #    lambda r: other_tag_to_dict(r.other_tags), axis=1
        #)
        #lines_with_tags_tram_index = lines_with_tags.apply(
        #    lambda r: any(tag_value in r.tag_dict.get("railway", []) for tag_value in TRAM_TYPES), axis=1
        #)
        #tram_lines = lines_with_tags[lines_with_tags_tram_index]

        #df_list = []
        #for i, r in tram_lines.iterrows():
        #    df_list.append(pd.DataFrame(dict_values_to_list(r.tag_dict)))
        #df_new = pd.concat(df_list)
        #df_new.index = tram_lines.index
        #trams = tram_lines.join(df_new, how="inner").drop(["tag_dict"], axis=1)
        trams["infra"] = 1
        trams = trams.astype({"infra": "int32"})
        self._process_result_lines = trams.loc[:, ["infra", "geometry"]]
        self._orig = trams

        # Mark objects which are within YLRE katualueet areas
        self._process_result_lines["id"] = self._process_result_lines.index + 1 # Adding temporary id field for clipping
        self._process_result_lines = gpd.overlay(self._process_result_lines, self._ylre_katualueet, how='union', keep_geom_type=True).explode().reset_index(drop=True)

        # Buffering configuration
        buffers = self._cfg.buffer(self._module)
        if len(buffers) != 1:
            raise ValueError("Unkown number of buffer values")

        # buffer lines
        target_infra_polys = self._process_result_lines.copy()
        target_infra_polys["geometry"] = target_infra_polys.buffer(buffers[0])

        # Clip by using YLRE katualueet areas
        geometryToClipAttrsDissolve = ["infra"]
        maskAttrsDissolve = ["ylre_class"]
        target_infra_polys = self._clipAreasByAreas(target_infra_polys, self._ylre_katualueet, geometryToClipAttrsDissolve, maskAttrsDissolve, "id", "ylre_class")
        target_infra_polys.drop(columns=["id", "ylre_class", "kadun_nimi"], inplace=True) # Dropping temporary id field
        for attr in geometryToClipAttrsDissolve:
            target_infra_polys[attr] = target_infra_polys[attr].fillna("")
        target_infra_polys = target_infra_polys.dissolve(by=geometryToClipAttrsDissolve, as_index=False)

        # Only intersecting objects to Helsinki area are important
        # read Helsinki geographical region and reproject
        try:
            helsinki_region_polygon = gpd.read_file(
                filename=self._cfg.local_file("hki")
            ).to_crs(self._cfg.crs())
        except Exception as e:
            print("Area polygon file not found!")
            raise e

        target_infra_polys = gpd.clip(target_infra_polys, helsinki_region_polygon)

        target_infra_polys = target_infra_polys.explode(ignore_index=True)

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
        # tram line infra as debug material
        target_infra_file_name = self._cfg.target_file(self._module)

        tram_lines = self._process_result_lines.reset_index(drop=True)

        schema = gpd.io.file.infer_schema(tram_lines)
        schema["properties"]["infra"] = "int32"

        tram_lines.to_file(target_infra_file_name, schema=schema, driver="GPKG")

        # tormays GIS material
        target_buffer_file_name = self._cfg.target_buffer_file(self._module)

        # instruct Geopandas for correct data type in file write
        # fid is originally as index, obtain fid as column...
        tormays_polygons = self._process_result_polygons.reset_index(drop=True)

        schema = gpd.io.file.infer_schema(tormays_polygons)
        schema["properties"]["infra"] = "int32"

        tormays_polygons.to_file(target_buffer_file_name, schema=schema, driver="GPKG")
