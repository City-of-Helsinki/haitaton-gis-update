import logging

from modules.config import Config
from modules.gis_validate_deploy import GisProcessor

class SpecialTransportRoutes(GisProcessor):
    """Process special transport routes."""

    logger = logging.getLogger(__name__)

    def __init__(self, cfg: Config):
        self._module = "special_transport_routes"
        self._filename = cfg.target_buffer_file(self._module)
        GisProcessor.__init__(self, cfg)