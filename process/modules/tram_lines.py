import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import gtfs_kit as gk
from shapely.errors import ShapelyDeprecationWarning
from shapely.geometry import LineString, Point
import warnings
import fiona

from modules.config import Config
from modules.gis_processing import GisProcessor

# Select only following route_type values(HSL):
# 0 = Urban tram
# 900 = Light rail

TRAM_ROUTE_TYPE = [0, 900]

class TramLines(GisProcessor):
    """Process tram lines, i.e. schedule information."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._process_result_lines = None
        self._process_result_polygons = None
        self._debug_result_lines = None
        self._orig = None
        self._module = "tram_lines"
        self._store_original_data = cfg.store_orinal_data(self._module)

        # Loading ylre_katualueet dataset
        ylre_katualueet_filename = cfg.target_buffer_file("ylre_katualueet")
        self._ylre_katualueet = gpd.read_file(ylre_katualueet_filename)
        self._ylre_katualueet_sindex = self._ylre_katualueet.sindex

        file_name = cfg.local_file(self._module)
        self._feed = gk.read_feed(file_name, dist_units="km")

    def _tram_trips(self) -> pd.DataFrame:
        """Pick tram trips from schedule data."""
        feed = self._feed
        tram_routes = (
            feed.routes[feed.routes.route_type.isin(TRAM_ROUTE_TYPE)]
            .route_id.unique()
            .tolist()
        )
        trip_shapes = (
            feed.trips.groupby(["shape_id", "direction_id", "route_id"], as_index=False)
            .first()
            .sort_values("route_id")
        )
        tram_trips = trip_shapes[trip_shapes.route_id.isin(tram_routes)]
        return tram_trips

    def _line_shapes(self) -> gpd.GeoDataFrame:
        """Form line geometries from schedule data."""
        shp_sorted = self._feed.shapes.sort_values(["shape_id", "shape_pt_sequence"])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

            shp_sorted["geometry"] = shp_sorted.apply(
                lambda p: Point(p.shape_pt_lon, p.shape_pt_lat), axis=1
            )
            shp_lines = gpd.GeoDataFrame(
                shp_sorted.groupby(["shape_id"])["geometry"].apply(
                    lambda x: LineString(x.tolist())
                ),
                geometry="geometry",
            )
        shp_lines = shp_lines.set_crs(epsg=4326)
        shp_lines = shp_lines.to_crs(self._cfg.crs())
        return shp_lines

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
        tram_trips = self._tram_trips()
        line_shapes = self._line_shapes()
        shapes_and_trips = tram_trips.join(line_shapes, on="shape_id", how="left")
        shapes_and_trips = gpd.GeoDataFrame(shapes_and_trips, geometry="geometry")

        shapes_and_trips["lines"] = 1
        self._orig = shapes_and_trips
        shapes_and_trips = shapes_and_trips.loc[:, ["lines", "geometry"]]
        shapes_and_trips = shapes_and_trips.astype({"lines": "int32"})

        self._process_result_lines = shapes_and_trips

        # Mark objects which are within YLRE katualueet areas
        self._process_result_lines["id"] = self._process_result_lines.index + 1 # Adding temporary id field for clipping
        self._process_result_lines = gpd.overlay(self._process_result_lines, self._ylre_katualueet, how="union", keep_geom_type=True).explode().reset_index(drop=True)

        buffers = self._cfg.buffer(self._module)
        if len(buffers) != 1:
            raise ValueError("Unknown number of buffer values")

        # buffer lines
        target_lines_polys = self._process_result_lines.copy()
        target_lines_polys["geometry"] = target_lines_polys.buffer(buffers[0])

        # Clip by using YLRE katualueet areas
        geometryToClipAttrsDissolve = ["lines"]
        maskAttrsDissolve = ["ylre_class"]
        target_lines_polys = self._clipAreasByAreas(target_lines_polys, self._ylre_katualueet, geometryToClipAttrsDissolve, maskAttrsDissolve, "id", "ylre_class")
        target_lines_polys.drop(columns=["id", "ylre_class", "kadun_nimi"], inplace=True) # Dropping temporary id field
        for attr in geometryToClipAttrsDissolve:
            target_lines_polys[attr] = target_lines_polys[attr].fillna("")
        target_lines_polys = target_lines_polys.dissolve(by=geometryToClipAttrsDissolve, as_index=False)

        # Only intersecting routes to Helsinki area are important
        # read Helsinki geographical region and reproject
        try:
            helsinki_region_polygon = gpd.read_file(
                filename=self._cfg.local_file("hki")
            ).to_crs(self._cfg.crs())
        except Exception as e:
            print("Area polygon file not found!")
            raise e

        target_lines_polys = gpd.clip(target_lines_polys, helsinki_region_polygon)

        target_lines_polys = target_lines_polys.explode(ignore_index=True)

        # save to instance
        self._process_result_polygons = target_lines_polys

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
        schema["properties"]["lines"] = "int32"

        tram_lines.to_file(target_infra_file_name, schema=schema, engine="fiona", driver="GPKG")

        # tormays GIS material
        target_buffer_file_name = self._cfg.target_buffer_file(self._module)

        # instruct Geopandas for correct data type in file write
        # fid is originally as index, obtain fid as column...
        tormays_polygons = self._process_result_polygons.reset_index(drop=True)

        schema = gpd.io.file.infer_schema(tormays_polygons)
        schema["properties"]["lines"] = "int32"

        tormays_polygons.to_file(target_buffer_file_name, schema=schema, engine="fiona", driver="GPKG")
