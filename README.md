# ALT Repoteka Service

[![Docker Pulls](https://img.shields.io/docker/pulls/maksonchikw67/repoteka-service)](https://hub.docker.com/r/maksonchikw67/repoteka-service)

Service for tracking package versions across ALT Linux repositories.  
It fetches metadata from the public [Repoteka API](https://rdb.altlinux.org/repoteka/openapi.json), stores it in PostgreSQL, and provides a FastAPI interface to answer three specific questions about package versions and repository branches.

## Overview

This project consists of two components:

- **Loader** – fetches package metadata (binary and source) for supported branches, processes it, and stores it in PostgreSQL.
- **API** – a FastAPI application that only interacts with the database and answers the three questions described below.

The service is designed to run in **Kubernetes** with horizontal scaling (3 replicas of the API).

## Features

- **Question 1:** Given a package name, type (`binary` or `source`) and a target EVR (epoch, version, release), returns all branches where the package version is older than the target.
- **Question 2:** Given a branch name and a maintainer email, returns packages in that branch that are older than in the Sisyphus branch.
- **Question 3:** Given a list of source package names, returns how many days each package is behind Sisyphus (based on build time or last update timestamp).

## Quick Start (Docker)

The easiest way to try the service is using the pre‑built image and `docker-compose`:

```bash
# Download docker-compose.yml
curl -O https://raw.githubusercontent.com/Eddi-cry/alt-repoteka-service/main/docker-compose.yml

# Start PostgreSQL and the API
docker-compose up -d

# Load data (this may take ~15 minutes)
docker-compose exec api python3 -m src.cli.main load

# Check if the API is healthy
curl http://localhost:8000/health
```

Now you can query the API at `http://localhost:8000`.

## Requirements

- **Python 3.8+** (for local development)
- **PostgreSQL** (local or containerised)
- **Docker** (for building and running the container image)
- **Kubernetes** cluster (for deployment, e.g., kind, minikube, or Docker Desktop)

## Installation on ALT Linux

The following instructions are for installing the service directly on an ALT Linux system (without containers).

### Scenario 1: Clean system

```bash
# Install system dependencies
apt-get update
apt-get install -y python3 python3-pip postgresql postgresql-contrib

# Clone the repository
git clone https://github.com/Eddi-cry/alt-repoteka-service.git
cd alt-repoteka-service

# Install Python dependencies
pip3 install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials (see Configuration section)

# Initialize the database and load data
python3 -m src.cli.main load

# Start the API server
python3 -m src.cli.main serve
```

### Scenario 2: System with outdated package base

```bash
# First update the package list and upgrade existing packages
apt-get update
apt-get upgrade -y

# Then install the required packages (if not already present)
apt-get install -y python3 python3-pip postgresql postgresql-contrib

# Proceed with the same steps as Scenario 1
```

## Configuration

The application uses environment variables for configuration. You can provide them via a `.env` file (for local development) or directly as environment variables (for containers).

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=repoteka
DB_USER=postgres
DB_PASSWORD=your_password

REPOTEKA_URL=https://rdb.altlinux.org/repoteka

API_HOST=0.0.0.0
API_PORT=8000
```

In Kubernetes, these are provided via `ConfigMap` and `Secret` (see the `k8s/` folder).

## Usage

### CLI

The project provides a command‑line interface:

```bash
# Load data from Repoteka
python3 -m src.cli.main load

# Start the API server
python3 -m src.cli.main serve

# Check service status
python3 -m src.cli.main status
```

### API Endpoints

All endpoints return JSON.

#### 1. Check package status across branches

```
GET /api/package-status
```

**Parameters:**
- `package_name` (required) – package name, e.g., `curl`
- `package_type` – `binary` or `source` (default: `binary`)
- `target_version` (required) – target version, e.g., `8.21.0`
- `target_release` (required) – target release, e.g., `alt1`
- `target_epoch` – epoch (default: `0`)

**Example:**
```bash
curl "http://localhost:8000/api/package-status?package_name=curl&package_type=binary&target_version=8.21.0&target_release=alt1"
```

**Response (example):**
```json
{
  "package": "curl",
  "type": "binary",
  "target": "0:8.21.0-alt1",
  "outdated_in": [
    {"branch": "p10", "current_version": "8.12.0-alt2", "arch": "x86_64"},
    {"branch": "c10f2", "current_version": "8.12.1-alt2", "arch": "x86_64"}
  ]
}
```

#### 2. Outdated packages for a maintainer

```
GET /api/maintainer-outdated
```

**Parameters:**
- `branch` (required) – branch name, e.g., `p10`
- `maintainer_email` (required) – maintainer email

**Example:**
```bash
curl "http://localhost:8000/api/maintainer-outdated?branch=p10&maintainer_email=aas@altlinux.org"
```

**Response:**
```json
{
  "branch": "p10",
  "maintainer": "aas@altlinux.org",
  "outdated_packages": [
    {"name": "libcurl", "current": "8.12.0-alt2", "sisyphus": "8.21.0-alt1", "arch": "x86_64"},
    ...
  ],
  "count": 42
}
```

#### 3. Days outdated for source packages

```
GET /api/outdated-days
```

**Parameters:**
- `packages` (required, can be repeated) – list of source package names

**Example:**
```bash
curl "http://localhost:8000/api/outdated-days?packages=curl&packages=openssl"
```

**Response (example):**
```json
{
  "curl": {
    "p10": {"days": 120, "branch_version": "8.12.0-alt2", "sisyphus_version": "8.21.0-alt1"},
    "c10f2": {"days": 115, "branch_version": "8.12.1-alt2", "sisyphus_version": "8.21.0-alt1"}
  },
  "openssl": {}
}
```

### Health checks

- `GET /health` – returns `{"status":"ok"}`
- `GET /ready` – returns `{"status":"ready"}` when the database is reachable

## Docker

### Build the image locally

```bash
docker build -f docker/Dockerfile -t repoteka-service:latest .
```

The image is based on `registry.altlinux.org/sisyphus/alt` and includes all necessary Python modules.  
A pre‑built image is available at `maksonchikw67/repoteka-service:latest`.

### Run the API container

```bash
docker run -d --name repoteka-api -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e DB_PORT=5432 \
  -e DB_NAME=repoteka \
  -e DB_USER=postgres \
  -e DB_PASSWORD=your_password \
  maksonchikw67/repoteka-service:latest
```

> **Note:** On Linux, use `--network=host` or specify the actual PostgreSQL IP instead of `host.docker.internal`.

## Kubernetes

The repository includes a full set of Kubernetes manifests in the `k8s/` directory:

- `namespace.yaml` – creates the `repoteka` namespace
- `configmap.yaml` – non‑sensitive configuration
- `secret.yaml` – database password (base64‑encoded)
- `postgres-deployment.yaml` and `postgres-service.yaml` – PostgreSQL deployment
- `loader-job.yaml` – one‑time job to load data
- `api-deployment.yaml` – API deployment with **3 replicas** (horizontal scaling)
- `api-service.yaml` – internal service (ClusterIP)

### Deploy to Kubernetes

```bash
kubectl create namespace repoteka
kubectl apply -f k8s/
```

### Verify the deployment

```bash
kubectl get pods,svc -n repoteka
```

Example output (as proof of successful deployment):

```
NAME                                READY   STATUS    RESTARTS   AGE
pod/postgres-556fbff5d6-rpn5c       1/1     Running   0          105m
pod/repoteka-api-6b45bf8bfb-7h228   1/1     Running   0          26m
pod/repoteka-api-6b45bf8bfb-dwt6z   1/1     Running   0          26m
pod/repoteka-api-6b45bf8bfb-pjf59   1/1     Running   0          26m

NAME                       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/postgres-service   ClusterIP   10.96.170.73    <none>        5432/TCP   151m
service/repoteka-api       ClusterIP   10.96.135.121   <none>        8000/TCP   150m
```

### Access the API

Use port‑forwarding to access the API locally:

```bash
kubectl port-forward -n repoteka service/repoteka-api 8000:8000
```

Then test with `curl` as shown in the API examples.

## Repository

Source code: [https://github.com/Eddi-cry/alt-repoteka-service](https://github.com/Eddi-cry/alt-repoteka-service)

