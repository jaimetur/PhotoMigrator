FROM python:3.11-slim

WORKDIR /app

# (Optional) install tzdata
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Etc/UTC

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY docs/ ./docs/
COPY help/ ./help/
COPY gpth_tool/ ./gpth_tool/
COPY Config.ini ./default_config.ini
COPY docker/docker.conf ./default_docker.conf
COPY README.md ./docs/README.md

COPY docker/docker_entrypoint.sh /docker_entrypoint.sh

RUN chmod +x ./gpth_tool/*
RUN chmod +x /docker_entrypoint.sh

ENTRYPOINT ["/docker_entrypoint.sh"]
