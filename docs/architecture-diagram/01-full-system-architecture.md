# High-Level System Architecture (HLD) — ShopLite

This document details the complete end-to-end production architecture for **ShopLite**, covering the AWS cloud network, private Kubernetes compute cluster, decoupled microservices, GitOps delivery pipeline, and distributed observability mesh.

---

## 1. High-Level Architecture Topology

```mermaid
flowchart TD
    subgraph InternetLayer ["Public Internet"]
        Client["Web Browser / Client Traffic"]
        Dev["DevOps Engineer / Git Commit"]
    end

    subgraph AWS_Cloud ["AWS Cloud (Custom VPC: 10.0.0.0/16 — Multi-AZ)"]
        subgraph PublicSubnets ["Public Subnets (10.0.1.0/24 & 10.0.2.0/24)"]
            ALB["AWS Application Load Balancer (ALB)<br/>Ports 80 / 443"]
            NAT["NAT Gateway / Instance<br/>Outbound Internet Egress"]
            IGW["Internet Gateway"]
        end

        subgraph PrivateSubnets ["Private Subnets (10.0.10.0/24 & 10.0.20.0/24) — Zero Public IPs"]
            SSM["AWS Systems Manager (SSM)<br/>Session Manager Admin Access"]

            subgraph K8sCluster ["Kubernetes Cluster (v1.28+)"]
                subgraph IngressControllers ["Ingress Layer"]
                    Ingress["ingress-nginx Controller<br/>NodePort / ALB Target Group"]
                end

                subgraph Namespace_Shoplite ["Namespace: shoplite"]
                    WebPod["web Pods (2 Replicas)<br/>Nginx Alpine (Static HTML/JS)<br/>Path: / | Non-Root UID 10001"]
                    ApiPod["catalog-api Pods (>=2 Replicas)<br/>FastAPI + OpenTelemetry SDK<br/>Path: /api | Non-Root UID 10001<br/>PDB: minAvailable: 1"]
                    WorkerPod["order-worker Pods (HPA 1-4 Replicas)<br/>Python Asyncio Consumer<br/>Termination Grace: 30s"]

                    subgraph DataIsolation ["Data & Queue Layer (NetworkPolicy Enforced)"]
                        RedisQueue["redis (ClusterIP)<br/>Port 6379<br/>List: orders:pending<br/>List: orders:processing"]
                        PostgresDB["postgres (StatefulSet)<br/>Port 5432 | PVC: 5Gi<br/>Seeded Catalog (>=10 items)"]
                    end
                end

                subgraph Namespace_Monitoring ["Namespace: monitoring"]
                    Prometheus["Prometheus (kube-prometheus-stack)<br/>Scrapes ServiceMonitors (/metrics)"]
                    Alertmanager["Alertmanager<br/>5 Critical/Warning Rules"]
                    Loki["Grafana Loki<br/>Structured JSON Log Aggregation"]
                    Tempo["Grafana Tempo<br/>Distributed OTLP Traces (gRPC 4317)"]
                    Grafana["Grafana Dashboards<br/>Golden Signals + Derived Trace Links"]
                end
            end
        end
    end

    subgraph CI_CD_GitOps ["CI/CD & GitOps Delivery Mesh"]
        GitHubActions["GitHub Actions CI (shoplite-app)<br/>Lint · Test · Trivy Scan · OIDC Auth"]
        ECR["Amazon Elastic Container Registry (ECR)<br/>Images: web, catalog-api, order-worker"]
        GitOpsRepo["GitOps Repository (shoplite-gitops)<br/>envs/dev/ & envs/prod/ values.yaml"]
        ArgoCD["ArgoCD Controller<br/>Automated Sync (Dev) · Self-Healing"]
    end

    %% Ingress and Client Flows
    Client -->|HTTP / HTTPS| ALB
    ALB -->|Forward to NodePort| Ingress
    Ingress -->|Path: /| WebPod
    Ingress -->|Path: /api| ApiPod

    %% Application Microservices Data Flow
    WebPod -.->|AJAX Fetch /api/*| ApiPod
    ApiPod -->|1. Validate & Insert PENDING| PostgresDB
    ApiPod -->|2. LPUSH orders:pending + W3C Trace| RedisQueue
    WorkerPod -->|3. Atomic BRPOPLPUSH| RedisQueue
    WorkerPod -->|4. Simulated Delay 1-2s| WorkerPod
    WorkerPod -->|5. SQL UPDATE status='COMPLETED'| PostgresDB
    WorkerPod -->|6. LREM orders:processing| RedisQueue

    %% Observability Streams
    ApiPod -.->|Export Metrics /metrics| Prometheus
    WorkerPod -.->|Export Metrics| Prometheus
    ApiPod -.->|JSON Logs stdout| Loki
    WorkerPod -.->|JSON Logs stdout| Loki
    ApiPod -.->|OTLP gRPC Spans| Tempo
    WorkerPod -.->|OTLP gRPC Spans| Tempo
    Prometheus -->|Trigger Alerts| Alertmanager
    Grafana -->|Query Metrics| Prometheus
    Grafana -->|Query Logs| Loki
    Grafana -->|Query Traces| Tempo
    Loki -.->|Derived Field trace_id Link| Tempo

    %% GitOps & CI Flow
    Dev -->|git push main| GitHubActions
    GitHubActions -->|Push SHA-tagged Images| ECR
    GitHubActions -->|Update image.tag commit| GitOpsRepo
    GitOpsRepo -->|Reconcile Desired State| ArgoCD
    ArgoCD -->|Declarative Sync / Self-Heal| Namespace_Shoplite
    PrivateSubnets -.->|Outbound Package/Image Pull| NAT
    NAT --> IGW
