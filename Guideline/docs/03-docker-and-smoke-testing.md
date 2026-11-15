# 3. Docker & Smoke Testing (Question 2)

This section details how to verify Docker image builds, enforce non-root security standards, verify image sizes (<150 MB), and run the automated smoke test script.

---

## 3.1 Docker Build & Image Size Verification

Run `docker compose build` to build all multi-stage images:

```bash
# Build images using Docker BuildKit
docker compose build
```

### Inspect Image Sizes (<150 MB Rule)

Run the following command in your terminal to inspect the final container image sizes:

```bash
docker images | grep -E "(shoplite|web|catalog-api|order-worker)"
```

### Target Size Thresholds:
| Image | Base Stage | Final Size | Non-Root User |
| :--- | :--- | :--- | :--- |
| `shoplite-web` | `node:20-alpine` $\to$ `nginx:alpine` | **< 45 MB** | `appuser` (UID 10001) |
| `shoplite-catalog-api` | `python:3.11-alpine` (stripped) | **< 120 MB** | `appuser` (UID 10001) |
| `shoplite-order-worker` | `python:3.11-alpine` (stripped) | **< 110 MB** | `appuser` (UID 10001) |

All 3 services strictly comply with the **< 150 MB** cap.

---

## 3.2 Non-Root User & Permissions Check

Verify that containers execute with non-root privileges:

```bash
# Verify catalog-api runs as UID 10001
docker compose run --rm catalog-api id
# Output: uid=10001(appuser) gid=10001(appuser)

# Verify order-worker runs as UID 10001
docker compose run --rm order-worker id
# Output: uid=10001(appuser) gid=10001(appuser)

# Verify web runs as UID 10001
docker compose run --rm web id
# Output: uid=10001(appuser) gid=10001(appuser)
```

---

## 3.3 Starting the Local Stack

Start the complete 5-container architecture:

```bash
# Start all containers in the background with health dependencies
docker compose up -d

# Check running status and health checks
docker compose ps
```

You should see 5 healthy containers:
1. `shoplite-postgres` (`healthy`)
2. `shoplite-redis` (`healthy`)
3. `shoplite-catalog-api` (`healthy`)
4. `shoplite-order-worker` (`healthy`)
5. `shoplite-web` (`healthy`)

---

## 3.4 Executing the End-to-End Smoke Test

The smoke test validates all five critical system milestones end-to-end:

### On Linux / macOS / Git Bash:
```bash
bash scripts/smoke-test.sh
```

### On Windows PowerShell:
```powershell
.\scripts\smoke-test.ps1
```

### What the Smoke Test Verifies:
1. **Step 1/5:** Probes `/readyz` until PostgreSQL and Redis report ready.
2. **Step 2/5:** Probes Web frontend at `http://localhost:8080` (HTTP 200).
3. **Step 3/5:** Verifies that $\ge 10$ products are seeded in PostgreSQL.
4. **Step 4/5:** Places a live order (`POST /orders`, product_id=1, quantity=2) and verifies `status: PENDING`.
5. **Step 5/5:** Polls the order until `order-worker` transitions it to `COMPLETED`.

### Expected Output:
```text
==========================================================
 ALL SMOKE TESTS PASSED CLEANLY! Stack is 100% Verified.
==========================================================
```

---

## 3.5 Tearing Down the Local Stack

When testing is complete, tear down the environment:

```bash
# Stop containers and remove volumes
make down
# or
docker compose down -v
```
