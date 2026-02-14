FROM rocker/r-ver:4.3.3

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq \
  && apt-get install -y -qq --no-install-recommends \
    git \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
  && rm -rf /var/lib/apt/lists/*

RUN R -q -e "install.packages(c('remotes','dplyr','yaml','countrycode'), repos='https://cloud.r-project.org'); remotes::install_github('PPgp/wpp2024')"

WORKDIR /work
