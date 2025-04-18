from abc import ABC, abstractmethod
from modules.common import validate_data_count_limits, validate_minimal, deploy
import geopandas as gpd


class GisProcessor(ABC):
    """This class helps keeping interface consistent."""

    @property
    @abstractmethod
    def logger(self):
        """A logger object (can be a class attribute) to log messages to."""

    def __init__(self, cfg):
        self._tormays_table_org = cfg.tormays_table_org(self._module)
        self._validate_limit_min = cfg.validate_limit_min(self._module)
        self._validate_limit_max = cfg.validate_limit_max(self._module)
        self._force_deploy = cfg.force_deploy()
        self._pg_conn_uri = cfg.pg_conn_uri()

    def get_temp_data(self):
        self._tormays_file_temp = gpd.read_file(self._filename)
        self._tormays_file_temp.rename_geometry("geom", inplace=True)

    def validate_deploy(self):
        if self._force_deploy == "True":
            validate_result = validate_minimal(
                self._module, self._tormays_file_temp, self._filename, self.logger
            )
        elif self._force_deploy == "False":
            # validate data amount: is it between given limits
            validate_result = validate_data_count_limits(
                self._module,
                self._pg_conn_uri,
                self._tormays_table_org,
                self._tormays_file_temp,
                self._validate_limit_min,
                self._validate_limit_max,
                self._filename,
                self.logger,
            )
        else:
            self.logger.error("Unexpected value for _force_deploy: %s", self._force_deploy)

        # Valid --> deploy
        if validate_result is True:
            deploy(
                self._pg_conn_uri,
                self._tormays_table_org,
                self._tormays_file_temp,
                self.logger,
            )
        else:
            self.logger.error("Validation failed (%s). No deploy.", self._module)
