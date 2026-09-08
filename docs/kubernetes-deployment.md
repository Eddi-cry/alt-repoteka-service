# Kubernetes Deployment Guide

## Overview

This guide describes how to deploy ALT Repoteka Service to Kubernetes with the optimized manifests.

## Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured to access the cluster
- At least 4GB RAM and 2 CPU cores available

---

## Quick Start

### 1. Create namespace and secrets

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secret (replace YOUR_PASSWORD)
kubectl create secret generic db-secrets \
  --from-literal=password=YOUR_PASSWORD \
  -n repoteka
```

### 2. Deploy infrastructure

```bash
# Apply all manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
```

### 3. Wait for PostgreSQL to be ready

```bash
kubectl wait --for=condition=ready pod -l app=postgres -n repoteka --timeout=120s
```

### 4. Load data

```bash
# Run loader job
kubectl apply -f k8s/loader-job.yaml

# Watch job progress
kubectl logs -f job/repoteka-loader -n repoteka
```

### 5. Deploy API

```bash
# Deploy API (3 replicas)
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml

# Wait for API to be ready
kubectl wait --for=condition=ready pod -l app=repoteka-api -n repoteka --timeout=120s
```

### 6. Test the deployment

```bash
# Port-forward to access API
kubectl port-forward -n repoteka service/repoteka-api 8000:8000

# Test health endpoint
curl http://localhost:8000/health
```

---

## What Changed in Manifests

### API Deployment

**Added:**
- ✅ Resource limits/requests (100m-500m CPU, 256Mi-512Mi memory)
- ✅ RollingUpdate strategy with maxSurge=1, maxUnavailable=0 (zero downtime)
- ✅ Startup probe (150s max startup time)
- ✅ Improved liveness probe (30s period, 5s timeout)
- ✅ PodAntiAffinity to spread pods across nodes
- ✅ All environment variables from ConfigMap

**Fixed:**
- ⚠️ Liveness probe now has longer timeout to avoid killing pods during slow queries
- ⚠️ Added startup probe for slow-starting containers

### ConfigMap

**Changed:**
- Now properly structured with key-value pairs
- Used by all deployments via `configMapKeyRef`

### PostgreSQL Deployment

**Added:**
- ✅ Resource limits/requests (250m-1000m CPU, 512Mi-1Gi memory)
- ✅ PersistentVolumeClaim for data persistence
- ✅ Liveness and readiness probes with `pg_isready`
- ✅ Recreate strategy (no multiple instances)
- ✅ PGDATA path configuration

**Fixed:**
- ⚠️ Uses PVC instead of emptyDir (data survives pod restarts)

### Loader Job

**Added:**
- ✅ Resource limits (500m-2000m CPU, 1-2Gi memory)
- ✅ backoffLimit=2 (retry on failure)
- ✅ ttlSecondsAfterFinished=3600 (auto-cleanup)
- ✅ All environment variables from ConfigMap

---

## Resource Requirements

### Minimum Cluster Resources

| Component | Requests | Limits |
|-----------|----------|--------|
| API (3 replicas) | 300m CPU, 768Mi memory | 1500m CPU, 1.5Gi memory |
| PostgreSQL | 250m CPU, 512Mi memory | 1000m CPU, 1Gi memory |
| Loader Job | 500m CPU, 1Gi memory | 2000m CPU, 2Gi memory |
| **Total** | **1050m CPU, 2.25Gi memory** | **4500m CPU, 4.5Gi memory** |

---

## Monitoring

### Check deployment status

```bash
# Check all resources
kubectl get all -n repoteka

# Check pod logs
kubectl logs -l app=repoteka-api -n repoteka --tail=100

# Check events
kubectl get events -n repoteka --sort-by='.lastTimestamp'
```

### Expected output after successful deployment

```
NAME                                READY   STATUS      RESTARTS   AGE
pod/postgres-<hash>                 1/1     Running     0          5m
pod/repoteka-api-<hash>            1/1     Running     0          2m
pod/repoteka-api-<hash>            1/1     Running     0          2m
pod/repoteka-api-<hash>            1/1     Running     0          2m
pod/repoteka-loader-<hash>         0/1     Completed   0          3m

NAME                       TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/postgres-service   ClusterIP   10.96.x.x       <none>        5432/TCP   5m
service/repoteka-api       ClusterIP   10.96.x.x       <none>        8000/TCP   2m
```

---

## Troubleshooting

### API pods not starting

```bash
# Check pod status
kubectl describe pod -l app=repoteka-api -n repoteka

# Check logs
kubectl logs -l app=repoteka-api -n repoteka
```

### Database connection issues

```bash
# Check PostgreSQL status
kubectl exec -it deployment/postgres -n repoteka -- psql -U postgres -d repoteka -c "SELECT 1;"
```

### Loader job failed

```bash
# Check job logs
kubectl logs job/repoteka-loader -n repoteka

# Re-run job
kubectl delete job repoteka-loader -n repoteka
kubectl apply -f k8s/loader-job.yaml
```

---

## Cleanup

```bash
# Delete all resources
kubectl delete namespace repoteka
```

---

## Production Recommendations

1. **Use Ingress** for external access instead of port-forward
2. **Enable HPA** (Horizontal Pod Autoscaler) for API
3. **Use StorageClass** with proper backup/snapshot capabilities
4. **Add monitoring** (Prometheus + Grafana)
5. **Use NetworkPolicies** to restrict inter-pod communication
6. **Add resource quotas** at namespace level
7. **Use separate namespaces** for dev/staging/prod
