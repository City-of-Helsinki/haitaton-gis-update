import logging

from modules.config import Config
from modules.gis_validate_deploy import GisProcessor

class CriticalAreas(GisProcessor):
    """Process critical areas."""

    logger = logging.getLogger(__name__)

    def __init__(self, cfg: Config):
        self._module = "critical_areas"
        self._filename = cfg.target_buffer_file(self._module)
        GisProcessor.__init__(self, cfg)