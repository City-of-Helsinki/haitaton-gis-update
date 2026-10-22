FROM ghcr.io/osgeo/gdal:ubuntu-small-3.13.2

ENV TORMAYS_DEPLOYMENT_PROFILE=docker_development

RUN apt-get update  \
    && apt-get install --no-install-recommends -y \
    g++ \
    gettext-base \
    wget \
    yq \
    build-essential \
    zlib1g-dev \
    libssl-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libffi-dev \
    liblzma-dev \
    ca-certificates \
    && apt-get clean

# Build Python 3.10 from source: process/, fetch/, and validate-deploy/ all pin
# `FROM python:3.10`, but this image's base (Ubuntu 26.04) ships Python 3.14 as
# its system python3, which is too new for this GDAL/pyogrio/fiona stack -
# pyogrio segfaults reading OFTDate columns under it. Building from source avoids
# depending on a PPA having packages for this Ubuntu release.
ARG PYTHON_VERSION=3.10.16
RUN wget -q https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
    && tar -xzf Python-${PYTHON_VERSION}.tgz \
    && cd Python-${PYTHON_VERSION} \
    && ./configure --enable-optimizations --with-ensurepip=install \
    && make -j"$(nproc)" \
    && make altinstall \
    && cd .. \
    && rm -rf Python-${PYTHON_VERSION} Python-${PYTHON_VERSION}.tgz

WORKDIR /opt
COPY ./automation/requirements.txt /opt
RUN python3.10 -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install -r requirements.txt

# Clean-up
RUN apt-get remove -y --purge g++ build-essential
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
