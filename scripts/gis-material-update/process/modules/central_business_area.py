import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine


from modules.config import Config


class CentralBusinessAreas:
    """Process Central Business Areas"""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._process_result_polygons = None
        self._module = "central_business_area"

        filename = cfg.local_file(self._module)
        self._store_original_data = cfg.store_orinal_data(self._module)
        self._layer = cfg.layer(self._module)
        df = gpd.read_file(filename, layer=self._layer)
        self._orig = df

        self._kantakaupunki_peruspiiri_nimi = [
            "VIRONNIEMI",
            "REIJOLA",
            "KALLIO",
            "KAMPINMALMI",
            "ULLANLINNA",
            "PASILA",
            "TAKA-TÖÖLÖ",
            "VANHAKAUPUNKI",
            "VALLILA",
            "ALPPIHARJU",
        ]
        self._kantakaupunki_not_osaalue_nimi = [
            "SUOMENLINNA",
            "LÄNSISAARET",
        ]
        # only listed peruspiiri areas are included except two listed osaalue areas:
        self._df = df[
            (
                df["peruspiiri_nimi_fi"]
                .str.upper()
                .isin(self._kantakaupunki_peruspiiri_nimi)
            )
            & (
                ~df["osaalue_nimi_fi"]
                .str.upper()
                .isin(self._kantakaupunki_not_osaalue_nimi)
            )
        ].loc[
            :,
            [
                "tunnus",
                "osaalue_tunnus",
                "osaalue_nimi_fi",
                "osaalue_nimi_se",
                "peruspiiri_nimi_fi",
                "peruspiiri_nimi_se",
                "suurpiiri_nimi_fi",
                "suurpiiri_nimi_se",
                "geometry",
            ],
        ]
        self._df["central_business_area"] = 1
        self._df["fid"] = self._df.reset_index().index
        self._df = self._df[
            [
                "fid",
                "central_business_area",
                "tunnus",
                "osaalue_tunnus",
                "osaalue_nimi_fi",
                "osaalue_nimi_se",
                "peruspiiri_nimi_fi",
                "peruspiiri_nimi_se",
                "suurpiiri_nimi_fi",
                "suurpiiri_nimi_se",
                "geometry",
            ]
        ]
        self._df = self._df.set_index("fid")

    def process(self):
        # no buffering or further processing needed
        self._process_result = self._df.copy()
        self._process_result_polygons = self._process_result

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
        # write processed data to file
        file_name = self._cfg.target_file(self._module)
        self._df.to_file(file_name, driver="GPKG")
