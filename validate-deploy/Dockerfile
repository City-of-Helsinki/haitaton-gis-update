FROM python:3.10

RUN apt-get update \
    && apt-get install -y gdal-bin libgdal-dev \
    && apt-get install --only-upgrade -y ca-certificates

WORKDIR /opt
COPY ./validate-deploy/requirements.txt /opt
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install -r requirements.txt
WORKDIR /haitaton-gis

ENTRYPOINT [ "sh", "/haitaton-gis-validate-deploy/validate_deploy_data.sh" ]