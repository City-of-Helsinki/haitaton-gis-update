import logging

from modules.config import Config
from modules.gis_validate_deploy import GisProcessor

class YlreKatualueet(GisProcessor):
    """Process YLRE street areas"""

    logger = logging.getLogger(__name__)

    def __init__(self, cfg: Config):
        self._module = "ylre_katualueet"
        self._filename = cfg.target_buffer_file(self._module)
        GisProcessor.__init__(self, cfg)