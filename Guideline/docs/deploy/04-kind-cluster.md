# Phase 4: Kind Kubernetes Cluster

## What

A local Kubernetes 1.37 control plane via **kind** (Kubernetes in Docker), with the application images pre-loaded so the cluster runs fully registry-independent, plus the ingress-nginx controller and metrics-server addons.

## Why

kind provides a genuine Kubernetes API, scheduler, kubelet, and CNI — every manifest, Helm chart, NetworkPolicy, HPA, and PDB from the repository executes for real. Pre-loading images removes any registry dependency, making the deployment reproducible on an air-gapped workstation.

## How

```bash
# 1. Create the cluster with ingress port mappings (NodePort 30080/30443 → host)
kind create cluster --name shoplite --config - <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 30080
    hostPort: 30080
    protocol: TCP
  - containerPort: 30443
    hostPort: 30443
    protocol: TCP
EOF

# 2. Retag built images to the registry names the Helm chart expects, then load into the node
for s in web catalog-api order-worker; do
  docker tag shoplite-app-$s:latest 904907793701.dkr.ecr.ap-southeast-1.amazonaws.com/shoplite-$s:dev-latest
done
kind load docker-image 904907793701.dkr.ecr.ap-southeast-1.amazonaws.com/shoplite-{web,catalog-api,order-worker}:dev-latest --name shoplite

# 3. Addons: ingress controller (kind flavor) + metrics-server (for HPA)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

# 4. Pin the ingress service to the mapped NodePorts
kubectl patch svc ingress-nginx-controller -n ingress-nginx --type merge \
  -p='{"spec":{"type":"NodePort","ports":[
    {"name":"http","port":80,"nodePort":30080,"protocol":"TCP","targetPort":"http"},
    {"name":"https","port":443,"nodePort":30443,"protocol":"TCP","targetPort":"https"}]}}'
```

### Registry-independent image policy

The dev values set `pullPolicy: IfNotPresent` so kubelet satisfies image requests from the node's local containerd store — no registry credentials required. (`Always` is retained for production values where images come from ECR.)

## Evidence

<img src="/screenshots/Q5-kubernetes-helm/workloads-running.png" alt="Cluster workloads" width="440">

## Gate

`kubectl get nodes` shows `shoplite-control-plane Ready v1.37.0`; ingress answers `http://localhost:30080/` with HTTP 200.

Next: [Phase 5 — Helm & Observability](/deploy/05-helm-observability).
