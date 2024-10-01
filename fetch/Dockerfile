FROM python:3.10

RUN apt-get update  \
    && apt-get install --no-install-recommends -y \
    gdal-bin \
    gettext-base \
    libgdal-dev \
    software-properties-common \
    wget \
    yq \
    && apt-get clean

ENTRYPOINT [ "sh", "/haitaton-gis/fetch_all.sh" ]
