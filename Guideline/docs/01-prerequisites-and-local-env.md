# 1. Prerequisites & CLI Environment Setup

This section details every tool required and the exact commands to prepare your terminal environment before running tests.

---

## 1.1 Tooling Requirements

Verify that the following CLI utilities are installed on your workstation:

| Utility | Minimum Version | Verification Command | Purpose |
| :--- | :--- | :--- | :--- |
| **Python** | 3.11+ / 3.12 / 3.13 | `python --version` | Running FastAPI, Worker & Pytest |
| **Docker & Compose** | 24.0+ | `docker version && docker compose version` | Containerization & local stack |
| **Terraform** | 1.5+ | `terraform version` | AWS IaC validation & planning |
| **Helm** | 3.12+ | `helm version` | Linting & packaging K8s charts |
| **Kubectl** | 1.28+ | `kubectl version --client` | Inspecting cluster resources |
| **k6** | 0.45+ | `k6 version` | Synthetic load testing & chaos traffic |
| **Git & curl & jq** | Latest | `git --version && curl --version && jq --version` | GitOps workflows & HTTP inspection |

---

## 1.2 Repository Clone & Virtual Environment Setup

Open your terminal and execute:

```bash
# 1. Clone the application repository
git clone https://github.com/DevMahbubHussain/shoplite-app.git
cd shoplite-app

# 2. Clone the companion GitOps repository into the root or alongside
git clone https://github.com/DevMahbubHussain/shoplite-gitops.git

# 3. Create a local Python virtual environment
python -m venv .venv

# 4. Activate the virtual environment
# On Linux / macOS:
source .venv/bin/activate

# On Windows PowerShell:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& .\.venv\Scripts\Activate.ps1

# 5. Upgrade pip and install all microservice dependencies
pip install --upgrade pip
pip install -r services/catalog-api/requirements.txt
pip install -r services/order-worker/requirements.txt
pip install pytest pytest-asyncio
```

---

## 1.3 Environment Variables Configuration

Copy the sample environment file to `.env`:

```bash
cp .env.example .env
```

Ensure the baseline variables are active:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=shoplite
POSTGRES_PASSWORD=shoplite_password
POSTGRES_DB=shoplite_db

REDIS_HOST=localhost
REDIS_PORT=6379

OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=catalog-api
LOG_LEVEL=INFO

# Chaos flags (Default: Disabled)
CHAOS_LATENCY_MS=0
CHAOS_ERROR_RATE=0.0
CHAOS_SLOW_DB=false
CHAOS_MEMORY_LEAK=false
```
