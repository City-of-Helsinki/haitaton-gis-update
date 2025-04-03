FROM ghcr.io/osgeo/gdal:ubuntu-small-latest

ENV TORMAYS_DEPLOYMENT_PROFILE=docker_development

RUN apt-get update  \
    && apt-get install --no-install-recommends -y \
    g++ \
    gettext-base \
    python3-dev \
    python3-venv \
    wget \
    yq \
    && apt-get clean

WORKDIR /opt
COPY ./automation/requirements.txt /opt
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install -r requirements.txt

# Clean-up
RUN apt-get remove -y --purge g++
RUN apt-get autoremove -y
RUN rm -rfv /var/lib/apt/lists/*

COPY ./automation/automation.sh /haitaton-automation/
COPY ./config.yaml /haitaton-gis/
COPY ./config.yaml /haitaton-gis-validate-deploy/
COPY ./fetch/fetch_all.sh /haitaton-gis/
COPY ./fetch/fetch_data.sh /haitaton-gis/
COPY ./process/process_data.py /haitaton-gis/
COPY ./process/process_data.sh /haitaton-gis/
COPY ./osm_vrt_clip.vrt /haitaton-gis/
COPY ./process/modules/ /haitaton-gis/modules/
COPY ./validate-deploy/validate_deploy_data.py /haitaton-gis-validate-deploy/
COPY ./validate-deploy/validate_deploy_data.sh /haitaton-gis-validate-deploy/
COPY ./validate-deploy/modules/ /haitaton-gis-validate-deploy/modules/
COPY ./data/train_depots.gpkg /local_data/
COPY ./data/tormays_critical_area_polys.gpkg /local_data/

RUN mkdir -p /downloads /gis-output /local_data \
    && chown -R :0 /downloads /gis-output /local_data /haitaton-automation \
    && chmod -R g+w /downloads /gis-output /local_data /haitaton-automation

WORKDIR /haitaton-automation

ENTRYPOINT [ "sh", "/haitaton-automation/automation.sh" ]
