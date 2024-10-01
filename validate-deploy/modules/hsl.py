import logging

from modules.config import Config
from modules.gis_validate_deploy import GisProcessor

class HslBuses(GisProcessor):
    """Process HSL bus lines."""

    logger = logging.getLogger(__name__)

    def __init__(self, cfg: Config):
        self._module = "hsl"
        self._filename = cfg.target_buffer_file(self._module)
        GisProcessor.__init__(self, cfg)