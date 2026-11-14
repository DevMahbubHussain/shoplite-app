import { HealthStatus, Order, Product } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

export async function checkSystemHealth(): Promise<HealthStatus> {
  try {
    const res = await fetch(`${API_BASE}/healthz`, { cache: 'no-store' });
    if (!res.ok) throw new Error('API unreachable');
    return await res.json();
  } catch (err) {
    return { status: 'unreachable' };
  }
}

export async function getProducts(): Promise<Product[]> {
  const res = await fetch(`${API_BASE}/products`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch products: ${res.statusText}`);
  }
  return await res.json();
}

export async function createOrder(productId: number, quantity: number): Promise<Order> {
  const res = await fetch(`${API_BASE}/orders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ product_id: productId, quantity }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to submit order (${res.status})`);
  }

  return await res.json();
}

export async function getOrder(orderId: number): Promise<Order> {
  const res = await fetch(`${API_BASE}/orders/${orderId}`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Order #${orderId} not found`);
  }
  return await res.json();
}
