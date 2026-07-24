FROM registry.altlinux.org/sisyphus/alt:latest

RUN apt-get update && apt-get install -y \
    python3 \
    python3-module-psycopg2 \
    python3-module-rpm \
    python3-module-fastapi \
    python3-module-uvicorn \
    python3-module-sqlalchemy \
    python3-module-aiohttp \
    python3-module-click \
    python3-module-pydantic \
    python3-module-pydantic-settings \
    python3-module-python-dotenv \
    glibc-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

ENV PYTHONPATH=/app
ENV CONFIG_PATH=/app/config/config.yaml

CMD ["python3", "-m", "src.cli.main", "serve"]