# ALT Repoteka Service

Service for tracking package versions across ALT Linux repositories.

## Overview

This project consists of two components:

- **Loader** – fetches package metadata from the public [Repoteka API](https://rdb.altlinux.org/repoteka) and stores it in PostgreSQL.
- **API** – a FastAPI application that answers three questions about package versions and repositories.

The service is designed to run in Kubernetes with horizontal scaling (3 replicas of the API).

## Features

- **Question 1:** Given a package name, type (binary/source) and target EVR, returns all branches where the package version is older.
- **Question 2:** Given a branch and a maintainer email, returns packages in that branch that are older than in Sisyphus.
- **Question 3:** Given a list of source packages, returns how many days they are behind Sisyphus (based on build time or last update).

## Requirements

- Python 3.8+
- PostgreSQL (local or containerized)
- Docker (for container image)
- Kubernetes cluster (for deployment)

## Installation on ALT Linux

### Scenario 1: Clean system

```bash
# Install system dependencies
apt-get update
apt-get install -y python3 python3-pip postgresql postgresql-contrib

# Clone the repository
git clone https://github.com/yourusername/alt-repoteka-service.git
cd alt-repoteka-service

# Install Python dependencies
pip3 install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Initialize database and load data
python3 -m src.cli.main load

# Run the API server
python3 -m src.cli.main serve