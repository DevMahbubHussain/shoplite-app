import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom Business & Observability Metrics
export const ordersCreated = new Counter('shoplite_orders_created');
export const errorRate = new Rate('shoplite_error_rate');
export const orderLatency = new Trend('shoplite_order_creation_duration_ms');

// Workload Configuration: Target >= 20 RPS across 25 Virtual Users
export const options = {
  stages: [
    { duration: __ENV.RAMPUP || '1m', target: 25 },       // Ramp up to 25 VUs
    { duration: __ENV.DURATION || '13m', target: 25 },    // Sustain target load >= 20 RPS
    { duration: __ENV.COOLDOWN || '1m', target: 0 },      // Ramp down cleanly
  ],
  thresholds: {
    // Golden Signals Alert Thresholds (from monitoring/alert-rules/alerts.yaml)
    http_req_duration: ['p(95)<1000'],   // HighLatency alert fires if p95 > 1000ms
    http_req_failed: ['rate<0.05'],      // HighErrorRate alert fires if 5xx > 5%
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // 1. Fetch Product Catalog (Traffic generation for GET /products)
  const productsRes = http.get(`${BASE_URL}/products`, { headers });
  const productsOk = check(productsRes, {
    'GET /products status is 200': (r) => r.status === 200,
  });
  errorRate.add(!productsOk);

  let products = [];
  try {
    products = JSON.parse(productsRes.body);
  } catch (e) {
    // Body parsing fallback
  }

  // 2. Fetch Single Product Detail (Simulates user browsing, exercises CHAOS_LATENCY_MS)
  const productId = products.length > 0 ? products[Math.floor(Math.random() * products.length)].id : 1;
  const productDetailRes = http.get(`${BASE_URL}/products/${productId}`, { headers });
  check(productDetailRes, {
    'GET /products/{id} status is 200': (r) => r.status === 200,
  });

  // 3. Place Order (Traffic generation for POST /orders, exercises CHAOS_ERROR_RATE & queue depth)
  // ~30% of user sessions proceed to checkout
  if (Math.random() < 0.35) {
    const orderPayload = JSON.stringify({
      product_id: productId,
      quantity: Math.floor(Math.random() * 3) + 1,
    });

    const orderStart = new Date().getTime();
    const orderRes = http.post(`${BASE_URL}/orders`, orderPayload, { headers });
    const orderDuration = new Date().getTime() - orderStart;
    orderLatency.add(orderDuration);

    const orderSuccess = check(orderRes, {
      'POST /orders status is 201': (r) => r.status === 201,
    });
    errorRate.add(!orderSuccess);

    if (orderSuccess) {
      ordersCreated.add(1);
      try {
        const orderData = JSON.parse(orderRes.body);
        const orderId = orderData.order_id || orderData.id;

        // 4. Poll Order Status (Simulates frontend polling widget)
        if (orderId) {
          sleep(0.5);
          const statusRes = http.get(`${BASE_URL}/orders/${orderId}`, { headers });
          check(statusRes, {
            'GET /orders/{id} status is 200': (r) => r.status === 200,
          });
        }
      } catch (e) {
        // Parse error handling
      }
    }
  }

  // Pacing: Sleep 0.5s to 1.2s to sustain smooth throughput across 25 VUs (~20-30 RPS)
  sleep(Math.random() * 0.7 + 0.5);
}
