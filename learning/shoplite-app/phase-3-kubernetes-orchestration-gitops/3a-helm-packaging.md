# Phase 3A: Kubernetes Orchestration & Helm Packaging — Deep Dive & Staff SRE Knowledge Base

> **Module:** ShopLite Cloud-Native E-Commerce Platform  
> **Repository:** `shoplite-app`  
> **Phase:** 3A — Unified Helm Packaging & Workload Orchestration (Assessment Milestone 3 / Question 5)  
> **Branch:** `feature/k8s-helm-workloads`

---

## 1. What Was Implemented

We engineered a production-ready, unified Helm chart (`helm/shoplite/`) encapsulating all ShopLite microservices, queues, databases, autoscalers, and zero-trust policies:

```text
helm/shoplite/
├── Chart.yaml                  # apiVersion: v2, appVersion: 1.0.0
├── values.yaml                 # Base production defaults
├── values-dev.yaml             # Dev overrides (single replicas, smaller requests, HPA/PDB disabled)
├── values-prod.yaml            # Prod overrides (HA replicas, 10Gi PVC, HPA 2-6, PDB minAvailable: 1)
└── templates/
    ├── _helpers.tpl            # Standard naming and labeling conventions
    ├── configmap.yaml          # Non-sensitive runtime environment variables
    ├── secret.yaml             # Database credentials and async SQLAlchemy URLs
    ├── postgres-service.yaml   # ClusterIP service on port 5432
    ├── postgres-statefulset.yaml # 1-node PostgreSQL 15 StatefulSet with persistent VolumeClaimTemplate
    ├── redis-service.yaml      # ClusterIP service on port 6379
    ├── redis-deployment.yaml   # In-memory Redis 7 queue broker with ping probes
    ├── catalog-api-service.yaml# ClusterIP service on port 8000
    ├── catalog-api-deployment.yaml # FastAPI backend with non-root UID 10001, read-only root, probes
    ├── order-worker-deployment.yaml # Headless queue consumer with 30s graceful termination
    ├── web-service.yaml        # ClusterIP service on port 80
    ├── web-deployment.yaml     # Non-root Next.js static Nginx frontend on port 8080
    ├── ingress.yaml            # Ingress-nginx routing / to web and /api to catalog-api
    ├── hpa.yaml                # HorizontalPodAutoscaler for order-worker (CPU target 70%)
    ├── pdb.yaml                # PodDisruptionBudget for catalog-api and order-worker
    └── networkpolicy.yaml      # Zero-trust network boundary isolating PostgreSQL and Redis
```

---

## 2. Why This Is Critical (AWS Well-Architected Framework Alignment)

### A. Security Pillar (SEC01, SEC03, SEC05)
1. **Container Hardening & Non-Root Protocols (C5):**
   - Every application pod runs with:
     ```yaml
     securityContext:
       runAsNonRoot: true
       runAsUser: 10001
       readOnlyRootFilesystem: true
       allowPrivilegeEscalation: false
       capabilities:
         drop: ["ALL"]
     ```
   - Prevents container breakout: even if an attacker achieves remote code execution in FastAPI or Nginx, they cannot escalate privileges or overwrite binary files on the root filesystem.
2. **Kubernetes NetworkPolicy Enforcement (C2):**
   - Direct access to PostgreSQL (`5432`) and Redis (`6379`) is blocked for all pods in the cluster except `catalog-api` and `order-worker`.
   - The frontend `web` pods and external ingress pods have zero network route to the database or cache.
3. **Secret Decoupling:**
   - Passwords and database connection strings are mounted via Kubernetes `Secret` references (`secretKeyRef`), keeping Git repositories free of plain-text credentials.

### B. Reliability Pillar (REL05, REL07, REL11)
1. **Graceful Worker Termination (C9):**
   - `order-worker` specifies `terminationGracePeriodSeconds: 30`. When Kubernetes drains a node or scales down, the worker finishes committing in-flight orders to PostgreSQL and Redis before the container receives `SIGKILL`.
2. **PodDisruptionBudget (PDB):**
   - `minAvailable: 1` guarantees that Kubernetes node upgrades, cluster maintenance, or spot instance evictions never cause downtime by taking down all backend pods at once.
3. **Horizontal Pod Autoscaling (HPA):**
   - Automatically scales `order-worker` from 2 to 6 replicas when CPU utilization exceeds 70%, preventing queue backlog build-up during traffic spikes.
4. **StatefulSet for PostgreSQL:**
   - Ensures stable network identity (`shoplite-postgres-0`), ordered graceful deployment, and persistent disk binding across pod restarts via `volumeClaimTemplates`.

### C. Operational Excellence (OPS04, OPS05)
1. **Liveness & Readiness Probes:**
   - `catalog-api`: `/healthz` tests pod liveness; `/readyz` validates that PostgreSQL and Redis are responsive before traffic is routed to the pod.
   - Faulty pods are automatically removed from endpoints by kube-proxy without serving 502/503 errors to users.

---

## 3. Staff SRE / Cloud Architect Interview Questions & Model Answers

### Q1: Why use a StatefulSet instead of a Deployment for PostgreSQL in Kubernetes?
**Answer:**
A `Deployment` treats all pod replicas as fungible, stateless instances sharing identical specifications. In contrast, a `StatefulSet` provides three critical guarantees required by stateful relational databases:
1. **Stable Network Identifiers:** Pods receive deterministic, persistent DNS names (`postgres-0`, `postgres-1`) that persist across rescheduling.
2. **Dedicated Storage Volumes:** Each replica gets its own dedicated `PersistentVolume` via `volumeClaimTemplates` that re-attaches to the exact same pod name upon node failure, preventing dual-write corruption.
3. **Ordered Deployment and Termination:** Replicas are started sequentially ($0 \to 1 \to 2$) and terminated in reverse order ($2 \to 1 \to 0$), essential for leader election and replication streams.

### Q2: Why is `readOnlyRootFilesystem: true` recommended for production, and how do applications write temporary files?
**Answer:**
Setting `readOnlyRootFilesystem: true` prevents an attacker or misbehaving process from modifying application code, modifying configuration files, or installing unauthorized packages/binaries inside the container. 
For applications that require temporary scratch space (such as Python bytecode caches, `/tmp` Unix sockets, or Nginx client body buffers), an in-memory `emptyDir` volume is explicitly mounted to `/tmp` and `/var/cache/nginx`. This keeps the root filesystem immutable while isolating transient runtime writes to memory or an ephemeral node volume.

### Q3: How does Kubernetes NetworkPolicy enforce defense-in-depth in an e-commerce architecture?
**Answer:**
By default, Kubernetes implements an open flat networking model where all pods can communicate with all other pods across namespaces. In an e-commerce environment, this creates severe blast radius risks: a compromised frontend web pod could directly connect to the PostgreSQL database on port 5432 and dump customer credentials. 
By applying an ingress `NetworkPolicy` to the PostgreSQL and Redis pods with `podSelector` restricting source traffic to `component: catalog-api` and `component: order-worker`, the CNI (e.g. Calico/Cilium) programs Linux eBPF or iptables rules on each host to drop unauthorized packets at the kernel level, enforcing strict microsegmentation.
