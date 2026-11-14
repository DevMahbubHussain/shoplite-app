#!/usr/bin/env bash
# ShopLite Observability Stack Deployment Automation
# Namespace: monitoring
set -euo pipefail

echo "=========================================================="
echo "Installing / Upgrading ShopLite Observability Stack"
echo "=========================================================="

kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
helm repo add grafana https://grafana.github.io/helm-charts --force-update
helm repo update

echo "--> 1. Deploying Kube-Prometheus-Stack (Prometheus, Alertmanager, Grafana)..."
helm upgrade --install shoplite-prom prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values monitoring/kube-prometheus-stack-values.yaml \
  --wait --timeout 10m

echo "--> 2. Deploying Grafana Loki..."
helm upgrade --install loki grafana/loki \
  --namespace monitoring \
  --values monitoring/loki-values.yaml \
  --wait --timeout 5m

echo "--> 3. Deploying Grafana Promtail..."
helm upgrade --install promtail grafana/promtail \
  --namespace monitoring \
  --values monitoring/promtail-values.yaml \
  --wait --timeout 5m

echo "--> 4. Deploying Grafana Tempo..."
helm upgrade --install tempo grafana/tempo \
  --namespace monitoring \
  --values monitoring/tempo-values.yaml \
  --wait --timeout 5m

echo "=========================================================="
echo "Observability Stack Installed Successfully!"
echo "Grafana Endpoint:   http://<ingress-or-node-ip>:3000 (admin / ShopLiteMonitoring2026!)"
echo "Prometheus Target:  http://shoplite-prom-kube-prometh-prometheus.monitoring:9090"
echo "Loki Target:        http://loki.monitoring:3100"
echo "Tempo Target:       http://tempo.monitoring:3100 (OTLP gRPC: 4317)"
echo "=========================================================="
