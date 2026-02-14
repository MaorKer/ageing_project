FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /work

# Install the project (and deps) into the container.
COPY pyproject.toml README.md /work/
COPY src /work/src

RUN python -m pip install --upgrade pip \
  && python -m pip install ".[dev]"
