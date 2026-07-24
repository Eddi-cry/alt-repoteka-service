# ALT Repoteka Service

Service for tracking package versions across ALT Linux repositories.

[![Docker Pulls](https://img.shields.io/docker/pulls/maksonchikw67/repoteka-service)](https://hub.docker.com/r/maksonchikw67/repoteka-service)

## Overview

This project consists of two components:

- **Loader** – fetches package metadata from the public [Repoteka API]([https://rdb.altlinux.org/repoteka](https://rdb.altlinux.org/repoteka/openapi.json)) and stores it in PostgreSQL.
- **API** – a FastAPI application that answers three questions about package versions and repositories.

The service is designed to run in Kubernetes with horizontal scaling (3 replicas of the API).

## Features

- **Question 1:** Given a package name, type (binary/source) and target EVR, returns all branches where the package version is older.
- **Question 2:** Given a branch and a maintainer email, returns packages in that branch that are older than in Sisyphus.
- **Question 3:** Given a list of source packages, returns how many days they are behind Sisyphus (based on build time or last update).

## Quick Start (Docker)

The easiest way to run the service is using the pre-built image:

```bash
# Start PostgreSQL and API together with docker-compose
curl -O https://raw.githubusercontent.com/yourusername/alt-repoteka-service/main/docker-compose.yml
docker-compose up -d

# Load data (this may take ~15 minutes)
docker-compose exec api python3 -m src.cli.main load

# Check API
curl http://localhost:8000/health
