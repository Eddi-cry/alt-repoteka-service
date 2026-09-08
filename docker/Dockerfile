FROM registry.altlinux.org/sisyphus/alt

# Install system dependencies (using native ALT Linux packages)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-module-pip \
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
    python3-module-asyncpg \
    glibc \
    glibc-core \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Default command (can be overridden by docker-compose)
CMD ["python3", "-m", "src.cli.main", "serve"]
