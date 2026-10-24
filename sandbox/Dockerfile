FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ nodejs \
    && rm -rf /var/lib/apt/lists/*
USER 65534:65534
WORKDIR /work
