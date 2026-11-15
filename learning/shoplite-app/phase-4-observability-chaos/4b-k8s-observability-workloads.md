# Phase 4B: Kubernetes Observability Workloads & Prometheus ServiceMonitors — Deep Dive & Staff SRE Knowledge Base

> **Module:** ShopLite Cloud-Native E-Commerce Platform  
> **Repository:** `shoplite-app`  
> **Phase:** 4B — Kubernetes Observability Workloads, ServiceMonitors & Scraping (Question 6 / Milestone 4)  
> **Branch:** `feature/observability-k8s-workloads`  
> **Parent Branch:** `feature/observability-stack`

---

## 1. What Was Implemented

In this sub-phase, we integrated the ShopLite Kubernetes Helm chart (`helm/shoplite/`) with Prometheus Operator declarative scraping primitives:

1. **Worker Metrics ClusterIP Service (`helm/shoplite/templates/order-worker-service.yaml`):**
   - Created a dedicated ClusterIP Service for `order-worker` exposing TCP port `9102` (`name: metrics`).
   - Enabled Prometheus Operator to discover and route scrape requests to worker pods even though the worker is a headless asynchronous queue consumer without public HTTP endpoints.
2. **Prometheus Operator ServiceMonitors (`helm/shoplite/templates/servicemonitors.yaml`):**
   - Configured `ServiceMonitor` for `catalog-api`: targeting endpoint `http` (port 8000) on `/metrics` with 15s scrape interval.
   - Configured `ServiceMonitor` for `order-worker`: targeting endpoint `metrics` (port 9102) on `/metrics` with 15s scrape interval.
   - Attached Prometheus Operator label `release: prometheus` for automatic discovery by the Prometheus custom resource selector.
3. **NetworkPolicy Hardening for Scraper Ingress (`helm/shoplite/templates/networkpolicy.yaml`):**
   - Added ingress policy for `order-worker` pods permitting TCP traffic on port 9102.
   - Maintained strict zero-trust boundary on PostgreSQL (`5432`) and Redis (`6379`), which remain completely inaccessible to Prometheus scrapers.
4. **Verification Gate:**
   - Validated Helm chart syntax via `helm lint helm/shoplite` (0 failures).
   - Validated template rendering against both `values-dev.yaml` and `values-prod.yaml`.

---

## 2. Why This Is Critical (AWS Well-Architected Framework Alignment)

### A. Operational Excellence (OPS04, OPS05)
- **Declarative Service Discovery vs Static Targets:** In dynamic cloud-native environments, pods are continuously scaled, rescheduled, and replaced. Static Prometheus scrape targets (`targets: ['10.0.1.5:8000']`) fail immediately. The `ServiceMonitor` CRD decouples scraping configuration from infrastructure by using Kubernetes label selectors (`matchLabels`) to track endpoints dynamically through the Kubernetes API.
- **Dedicated Metrics Port for Headless Workers:** Asynchronous consumers traditionally run headless without Kubernetes services. Exposing a dedicated metrics port through a ClusterIP Service provides a clean, standard target for Prometheus Operator without opening arbitrary cluster access.

### B. Security Pillar (SEC05)
- **Zero-Trust Network Microsegmentation (C2):** Even while opening ingress for metric scrapers on ports 8000 and 9102, NetworkPolicy ensures that data-layer stores (PostgreSQL and Redis) cannot be reached from any monitoring namespace or external pod, enforcing defense-in-depth.

---

## 3. Staff SRE / Cloud Architect Interview Questions & Model Answers

### Q1: How does the Prometheus Operator discover and scrape workloads using `ServiceMonitor`?
**Answer:**
1. The Prometheus Operator manages a custom resource definition (CRD) called `Prometheus`. The `Prometheus` resource defines a `serviceMonitorSelector` (e.g. `matchLabels: {release: prometheus}`).
2. An application deploys a `ServiceMonitor` CRD specifying target labels (e.g., `app.kubernetes.io/component: catalog-api`) and endpoint details (`port: http`, `path: /metrics`, `interval: 15s`).
3. The Prometheus Operator watches for new or modified `ServiceMonitor` objects that match its selector.
4. When a match occurs, the Operator queries Kubernetes `Endpoints` / `EndpointSlices` backing the referenced `Service`, dynamically translates them into Prometheus scrape configuration stanzas, and signals Prometheus to reload its configuration without restarting the container.

### Q2: What is the difference between `ServiceMonitor` and `PodMonitor` in Prometheus Operator?
**Answer:**
- **`ServiceMonitor`:** Requires a Kubernetes `Service` object that routes to the target pods. It discovers target IP addresses by watching the Kubernetes `Endpoints` or `EndpointSlice` resources associated with that Service.
- **`PodMonitor`:** Scrapes pods directly using `podSelector` without needing a Kubernetes `Service` abstraction.
- **When to use which:** `ServiceMonitor` is the industry standard because production workloads typically have Services for traffic routing, stable DNS names, and standardized port naming. `PodMonitor` is used primarily for daemonsets or ephemeral batch jobs that have no associated Kubernetes Service.

### Q3: Why does a headless queue worker need a Kubernetes `Service` in a production cluster?
**Answer:**
Although an asynchronous worker does not accept user traffic, Prometheus needs a mechanism for endpoint discovery:
1. Creating a `ClusterIP` Service with port `9102` (`name: metrics`) registers each worker pod in the Kubernetes `Endpoints` registry.
2. This allows `ServiceMonitor` to discover worker replicas automatically as the Horizontal Pod Autoscaler (HPA) scales workers up or down.
3. It preserves network isolation: only port 9102 is exposed to cluster internal scrapers, while the worker application continues to process orders asynchronously from Redis.
