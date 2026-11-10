# ShopLite — Architectural Blueprints & Diagrams

This directory contains the complete architectural documentation, system designs, and interaction models for the **ShopLite** platform.

---

## 1. Directory Index

| Document | Focus Area | Contents & Modeling |
| :--- | :--- | :--- |
| **[01-full-system-architecture.md](01-full-system-architecture.md)** | **High-Level Design (HLD)** | Multi-AZ AWS VPC topology, public ALB, private Kubernetes cluster, NetworkPolicy isolation, GitOps reconciliation with ArgoCD, and distributed observability stack. |
| **[02-api-low-level-design.md](02-api-low-level-design.md)** | **Low-Level Design (LLD)** | OOP and SOLID class diagrams, Routers $\to$ Services $\to$ Repositories layered architecture, Pydantic v2 DTOs, and the Redis reliable queue consumer protocol. |
| **[03-usecase-and-sequence-diagrams.md](03-usecase-and-sequence-diagrams.md)** | **Use Cases & Sequences** | Actor-to-capability use case diagram, plus the complete end-to-end W3C distributed trace sequence from order placement to fulfillment in Tempo. |
| **[shoplite-system-architecture.svg](shoplite-system-architecture.svg)** | **Vector Master Diagram** | Standalone high-resolution SVG diagram suitable for offline viewing, documentation exports, and live presentations. |

---

## 2. Architecture Overview & Network Boundaries

```
                      Internet
                         │
                ┌────────▼────────┐
                │   Public ALB    │ (AWS Application Load Balancer - 2 AZs)
                └────────┬────────┘
                         │ HTTP / HTTPS
                ┌────────▼────────────────────────────────────────┐
                │ Ingress Controller (ingress-nginx)              │
                └────────┬───────────────────────────────┬────────┘
                         │ path: /                       │ path: /api
             ┌───────────▼───────────┐       ┌───────────▼───────────┐
             │  web (Nginx Alpine)   │       │  catalog-api (FastAPI)│
             │  (Stateless Frontend) │       │  (OpenTelemetry SDK)  │
             └───────────────────────┘       └─────┬───────────┬─────┘
                                                   │           │
                           ┌───────────────────────┘           └───────────────────────┐
                           │                                                           │
                  SQL      │                                        RPUSH              │
             ┌─────────────▼─────────────┐                             ┌───────────────▼──────────────┐
             │ postgres (PostgreSQL 16)  │                             │ redis (Redis 7.2 Alpine)     │
             │ StatefulSet + PVC (Seed)  │                             │ List: orders:pending         │
             └─────────────▲─────────────┘                             └───────────────▲──────────────┘
                           │                                                           │
                           │ SQL UPDATE (Status)                 BRPOPLPUSH / LREM     │
                           └───────────────────────┌───────────────────────────────────┘
                                                   │
                                     ┌─────────────┴─────────────┐
                                     │ order-worker (Python Async│
                                     │ + OpenTelemetry Context)  │
                                     └───────────────────────────┘
```

---

## 3. Live Demonstration Guide (10-Minute Walkthrough)

When presenting this architecture during live evaluations, refer to the diagrams in this folder:

1. **Architecture Walkthrough (2 min):**
   - Open [01-full-system-architecture.md](01-full-system-architecture.md) or [shoplite-system-architecture.svg](shoplite-system-architecture.svg).
   - Trace external ingress from ALB $\to$ Ingress $\to$ `web` & `catalog-api`.
   - Highlight the strict Kubernetes `NetworkPolicy` protecting PostgreSQL and Redis.
2. **Asynchronous Order Flow & OOP Design (2 min):**
   - Open [02-api-low-level-design.md](02-api-low-level-design.md).
   - Explain the SOLID separation: Routers (HTTP transport) $\to$ Services (business rules) $\to$ Repositories (persistence).
   - Demonstrate the reliable Redis list pattern (`LPUSH` $\to$ `BRPOPLPUSH` $\to$ `LREM`) and startup sweep.
3. **End-to-End Tracing & Telemetry (2 min):**
   - Open [03-usecase-and-sequence-diagrams.md](03-usecase-and-sequence-diagrams.md).
   - Walk through the W3C `traceparent` propagation from the API into Redis and into the worker span.
   - Show how Loki logs link directly to Tempo traces via the derived `trace_id` field.
4. **GitOps & Self-Healing (2 min):**
   - Show how GitHub Actions builds and pushes image tags to `shoplite-gitops`.
   - Explain how ArgoCD reconciles the cluster state without any `kubectl apply` in the CI pipeline.
5. **Observability & RCA (2 min):**
   - Explain how Alertmanager alerts map to Golden Signals panels and runbooks during chaos injection.
