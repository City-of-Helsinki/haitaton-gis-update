"""Main entrypoint script for material processing.
"""
import logging
import os
import sys

from modules.config import Config
from modules.gis_processing import GisProcessor

from modules.autoliikennemaarat import MakaAutoliikennemaarat
from modules.hsl import HslBuses
from modules.ylre_katualueet import YlreKatualueet
from modules.ylre_katuosat import YlreKatuosat
from modules.tram_infra import TramInfra
from modules.tram_lines import TramLines
from modules.cycling_infra import CycleInfra
from modules.liikennevaylat import Liikennevaylat
from modules.central_business_area import CentralBusinessAreas
from modules.special_transport_routes import SpecialTransportRoutes
from modules.critical_areas import CriticalAreas

DEFAULT_DEPLOYMENT_PROFILE = "local_development"


def process_item(item: str, cfg: Config):
    logger.info("Processing item: %s", item)
    gis_processor = instantiate_processor(item, cfg)
    gis_processor.process()
    gis_processor.persist_to_database()
    gis_processor.save_to_file()
    pass


def instantiate_processor(item: str, cfg: Config) -> GisProcessor:
    """Instantiate correct class for processing data."""
    if item == "hsl":
        return HslBuses(cfg, validate_gtfs=False)
    elif item == "maka_autoliikennemaarat":
        return MakaAutoliikennemaarat(cfg)
    elif item == "ylre_katuosat":
        return YlreKatuosat(cfg)
    elif item == "ylre_katualueet":
        return YlreKatualueet(cfg)
    elif item == "tram_infra":
        return TramInfra(cfg)
    elif item == "tram_lines":
        return TramLines(cfg)
    elif item == "cycle_infra":
        return CycleInfra(cfg)
    elif item == "liikennevaylat":
        return Liikennevaylat(cfg)
    elif item == "central_business_area":
        return CentralBusinessAreas(cfg)
    elif item == "special_transport_routes":
        return SpecialTransportRoutes(cfg)
    elif item == "critical_areas":
        return CriticalAreas(cfg)
    else:
        logger.error("Configuration not recognized: %s", item)


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)-5s - %(name)-15s - %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    logger = logging.getLogger(__name__)

    deployment_profile = os.environ.get("TORMAYS_DEPLOYMENT_PROFILE")
    use_deployment_profile = DEFAULT_DEPLOYMENT_PROFILE
    if deployment_profile in ["local_docker_development", "local_development", "docker_development"]:
        use_deployment_profile = deployment_profile
    else:
        logger.info(
            "Deployment profile environment variable is not set, defaulting to %s",
            DEFAULT_DEPLOYMENT_PROFILE,
        )

    cfg = Config().with_deployment_profile(use_deployment_profile)

    for item in sys.argv[1:]:
        process_item(item, cfg)
