#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
WEB_URL="${WEB_URL:-http://localhost:8080}"
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "=========================================================="
echo " Starting ShopLite End-to-End Smoke Test Suite"
echo " Target API: ${API_URL}"
echo " Target Web: ${WEB_URL}"
echo "=========================================================="

# 1. Probe /readyz until PostgreSQL and Redis report ready
echo ""
echo "[Step 1/5] Waiting for API readiness (/readyz)..."
READY=false
for i in $(seq 1 "${MAX_RETRIES}"); do
  STATUS_CODE=$(curl -s -o /tmp/readyz.json -w "%{http_code}" "${API_URL}/readyz" || true)
  if [ "${STATUS_CODE}" -eq 200 ]; then
    echo " -> API is READY (HTTP 200)"
    cat /tmp/readyz.json
    echo ""
    READY=true
    break
  fi
  echo " -> Attempt ${i}/${MAX_RETRIES}: API returned ${STATUS_CODE}, retrying in ${RETRY_INTERVAL}s..."
  sleep "${RETRY_INTERVAL}"
done

if [ "${READY}" != "true" ]; then
  echo "FAIL: API failed to report readiness within $((MAX_RETRIES * RETRY_INTERVAL))s"
  exit 1
fi

# 2. Verify static frontend responds with 200
echo ""
echo "[Step 2/5] Probing Web Frontend (${WEB_URL})..."
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${WEB_URL}" || true)
if [ "${WEB_STATUS}" -eq 200 ]; then
  echo " -> Frontend is healthy (HTTP 200)"
else
  echo "FAIL: Frontend returned HTTP ${WEB_STATUS}"
  exit 1
fi

# 3. Verify at least 10 products seeded
echo ""
echo "[Step 3/5] Verifying catalog seeding (>= 10 products)..."
PRODUCT_COUNT=$(curl -s "${API_URL}/products" | grep -o '"id":' | wc -l)
echo " -> Found ${PRODUCT_COUNT} products in database"
if [ "${PRODUCT_COUNT}" -lt 10 ]; then
  echo "FAIL: Expected >= 10 seeded products, got ${PRODUCT_COUNT}"
  exit 1
fi
echo " -> PASS: Catalog successfully seeded with ${PRODUCT_COUNT} products."

# 4. Create a test order
echo ""
echo "[Step 4/5] Placing test order (product_id=1, quantity=2)..."
ORDER_RESP=$(curl -s -X POST "${API_URL}/orders" \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}')

echo " -> Response: ${ORDER_RESP}"
ORDER_ID=$(echo "${ORDER_RESP}" | grep -o '"id":[0-9]*' | head -n1 | cut -d: -f2)

if [ -z "${ORDER_ID}" ]; then
  echo "FAIL: Could not extract order ID from response"
  exit 1
fi
echo " -> Order successfully created with ID #${ORDER_ID} (status: PENDING)"

# 5. Poll order until status is COMPLETED
echo ""
echo "[Step 5/5] Polling Order #${ORDER_ID} for completion by order-worker..."
COMPLETED=false
for i in $(seq 1 20); do
  CURRENT_STATUS=$(curl -s "${API_URL}/orders/${ORDER_ID}" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  echo " -> Polling [${i}/20]: Status is '${CURRENT_STATUS}'"
  if [ "${CURRENT_STATUS}" = "COMPLETED" ]; then
    COMPLETED=true
    break
  fi
  sleep 1
done

if [ "${COMPLETED}" != "true" ]; then
  echo "FAIL: Order #${ORDER_ID} did not reach COMPLETED status within 20s"
  exit 1
fi

echo ""
echo "=========================================================="
echo " ALL SMOKE TESTS PASSED CLEANLY! Stack is 100% Verified."
echo "=========================================================="
exit 0
