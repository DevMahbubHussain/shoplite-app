export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  stock: number;
  created_at: string;
}

export type OrderStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface Order {
  id: number;
  product_id: number;
  quantity: number;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
}

export interface HealthStatus {
  status: string;
  database?: string;
  redis?: string;
}
