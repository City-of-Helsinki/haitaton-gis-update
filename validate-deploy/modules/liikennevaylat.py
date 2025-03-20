import logging

from modules.config import Config
from modules.gis_validate_deploy import GisProcessor

class Liikennevaylat(GisProcessor):
    """Process street classes infra."""

    logger = logging.getLogger(__name__)

    def __init__(self, cfg: Config):
        self._module = "liikennevaylat"
        self._filename = cfg.target_buffer_file(self._module)
        GisProcessor.__init__(self, cfg)