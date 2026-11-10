'use client';

import { useEffect, useState } from 'react';
import { checkSystemHealth, createOrder, getOrder, getProducts } from '@/lib/api';
import { HealthStatus, Order, Product } from '@/types';

export default function HomePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [health, setHealth] = useState<HealthStatus>({ status: 'checking' });
  const [selectedProductId, setSelectedProductId] = useState<number | ''>('');
  const [quantity, setQuantity] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [recentOrders, setRecentOrders] = useState<Order[]>([]);
  const [lookupId, setLookupId] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Poll system health
  useEffect(() => {
    async function updateHealth() {
      const h = await checkSystemHealth();
      setHealth(h);
    }
    updateHealth();
    const interval = setInterval(updateHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // Fetch product catalog
  useEffect(() => {
    async function loadCatalog() {
      try {
        const items = await getProducts();
        setProducts(items);
        if (items.length > 0 && selectedProductId === '') {
          setSelectedProductId(items[0].id);
        }
      } catch (err: any) {
        console.error('Failed to load products:', err);
      }
    }
    loadCatalog();
  }, []);

  // Poll active order until terminal status
  useEffect(() => {
    if (!activeOrder || activeOrder.status === 'COMPLETED' || activeOrder.status === 'FAILED') {
      return;
    }

    const timer = setInterval(async () => {
      try {
        const updated = await getOrder(activeOrder.id);
        setActiveOrder(updated);

        // Update in recent orders list
        setRecentOrders((prev) =>
          prev.map((o) => (o.id === updated.id ? updated : o))
        );

        if (updated.status === 'COMPLETED') {
          setSuccessMsg(`Order #${updated.id} completed successfully by order-worker!`);
          clearInterval(timer);
        }
      } catch (err) {
        console.error('Error polling order:', err);
      }
    }, 1500);

    return () => clearInterval(timer);
  }, [activeOrder]);

  async function handleSubmitOrder(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProductId) return;

    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const newOrder = await createOrder(Number(selectedProductId), quantity);
      setActiveOrder(newOrder);
      setRecentOrders((prev) => [newOrder, ...prev.filter((o) => o.id !== newOrder.id)]);
      setSuccessMsg(`Order #${newOrder.id} placed! Status: PENDING (enqueued to Redis)`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to place order');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLookup() {
    const id = parseInt(lookupId, 10);
    if (isNaN(id) || id <= 0) return;

    setErrorMsg(null);
    try {
      const order = await getOrder(id);
      setActiveOrder(order);
    } catch (err: any) {
      setErrorMsg(err.message || `Order #${id} not found`);
    }
  }

  return (
    <>
      <header className="header">
        <div className="header-inner">
          <div className="brand">
            <span className="brand-logo">⚡</span>
            <div>
              <span className="brand-title">ShopLite</span>
              <span className="brand-sub">Build · Ship · Observe · Recover</span>
            </div>
          </div>
          <div className="header-status">
            <div
              className={`status-badge ${
                health.status === 'ok' ? 'healthy' : 'unhealthy'
              }`}
            >
              <span className="pulse-dot"></span>
              <span>
                {health.status === 'ok' ? 'API Online' : 'System Connecting...'}
              </span>
            </div>
          </div>
        </div>
      </header>

      <main className="container">
        <section className="hero-banner">
          <div className="hero-content">
            <span className="hero-tag">High-Throughput Storefront</span>
            <h1>Engineered for Resilience & Observability</h1>
            <p>
              Microservices order processing pipeline powered by Next.js, FastAPI,
              PostgreSQL, Redis reliable queues, and OpenTelemetry distributed tracing.
            </p>
          </div>
        </section>

        {errorMsg && (
          <div style={{ padding: '1rem', background: 'rgba(244,63,94,0.15)', border: '1px solid #f43f5e', borderRadius: '8px', marginBottom: '1.5rem', color: '#f43f5e', fontSize: '0.9rem' }}>
            {errorMsg}
          </div>
        )}
        {successMsg && (
          <div style={{ padding: '1rem', background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', borderRadius: '8px', marginBottom: '1.5rem', color: '#10b981', fontSize: '0.9rem' }}>
            {successMsg}
          </div>
        )}

        <div className="app-layout">
          {/* Catalog Section */}
          <section className="catalog-section">
            <div className="section-header">
              <h2>Product Catalog</h2>
              <span className="item-count">
                {products.length > 0 ? `${products.length} Products Available` : 'Loading...'}
              </span>
            </div>

            <div className="product-grid">
              {products.map((p) => (
                <div key={p.id} className="product-card">
                  <div className="product-info">
                    <h3>{p.name}</h3>
                    <p className="product-desc">{p.description}</p>
                  </div>
                  <div>
                    <div className="product-meta">
                      <span className="product-price">${p.price.toFixed(2)}</span>
                      <span className="product-stock">{p.stock} in stock</span>
                    </div>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setSelectedProductId(p.id);
                        setQuantity(1);
                        window.scrollTo({ top: 300, behavior: 'smooth' });
                      }}
                    >
                      Select to Order
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Order Actions Sidebar */}
          <aside className="sidebar-section">
            <div className="card">
              <div className="card-header">
                <h3>Place Quick Order</h3>
              </div>
              <form onSubmit={handleSubmitOrder} className="order-form">
                <div className="form-group">
                  <label htmlFor="productSelect">Select Product</label>
                  <select
                    id="productSelect"
                    value={selectedProductId}
                    onChange={(e) => setSelectedProductId(Number(e.target.value))}
                    required
                  >
                    <option value="">-- Choose Product --</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} (${p.price.toFixed(2)})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="orderQty">Quantity</label>
                  <input
                    id="orderQty"
                    type="number"
                    min="1"
                    max="10"
                    value={quantity}
                    onChange={(e) => setQuantity(Number(e.target.value))}
                    required
                  />
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting || !selectedProductId}
                  className="btn btn-primary"
                >
                  {isSubmitting ? 'Submitting to Queue...' : 'Submit Order'}
                </button>
              </form>
            </div>

            <div className="card">
              <div className="card-header">
                <h3>Live Order Tracker</h3>
              </div>
              <div className="lookup-form">
                <input
                  type="number"
                  placeholder="Order ID"
                  value={lookupId}
                  onChange={(e) => setLookupId(e.target.value)}
                />
                <button type="button" onClick={handleLookup} className="btn btn-secondary">
                  Track
                </button>
              </div>

              {activeOrder && (
                <div className="active-order-display">
                  <div className="order-info-row">
                    <span className="info-label">Order ID:</span>
                    <span className="mono">#{activeOrder.id}</span>
                  </div>
                  <div className="order-info-row">
                    <span className="info-label">Product ID:</span>
                    <span className="mono">{activeOrder.product_id}</span>
                  </div>
                  <div className="order-info-row">
                    <span className="info-label">Quantity:</span>
                    <span>{activeOrder.quantity}</span>
                  </div>
                  <div className="order-info-row">
                    <span className="info-label">Status:</span>
                    <span
                      className={`status-pill ${
                        activeOrder.status === 'COMPLETED'
                          ? 'status-completed'
                          : activeOrder.status === 'FAILED'
                          ? 'status-failed'
                          : 'status-pending'
                      }`}
                    >
                      {activeOrder.status}
                    </span>
                  </div>
                </div>
              )}

              <div className="recent-orders">
                <h4>Recent Session Orders</h4>
                <ul className="recent-list">
                  {recentOrders.length === 0 ? (
                    <li className="empty-state">No orders placed in this session</li>
                  ) : (
                    recentOrders.map((o) => (
                      <li
                        key={o.id}
                        className="recent-item"
                        onClick={() => setActiveOrder(o)}
                      >
                        <span className="mono">Order #{o.id}</span>
                        <span
                          className={`status-pill ${
                            o.status === 'COMPLETED'
                              ? 'status-completed'
                              : o.status === 'FAILED'
                              ? 'status-failed'
                              : 'status-pending'
                          }`}
                        >
                          {o.status}
                        </span>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>
          </aside>
        </div>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <span>ShopLite Next.js Web Storefront — Static Export on Non-Root Nginx</span>
          <span className="mono">catalog-api :8000 | order-worker :9102 | web :8080</span>
        </div>
      </footer>
    </>
  );
}
