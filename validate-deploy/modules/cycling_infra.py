import logging

from modules.config import Config
from modules.gis_validate_deploy import GisProcessor

class CycleInfra(GisProcessor):
    """Process cycle route infra."""

    logger = logging.getLogger(__name__)

    def __init__(self, cfg: Config):
        self._module = "cycle_infra"
        self._filename = cfg.target_buffer_file(self._module)
        GisProcessor.__init__(self, cfg)