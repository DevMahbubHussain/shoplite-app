from app.models.product import Product
from app.observability.logging import logger
from app.repositories.product_repository import ProductRepositoryProtocol
from app.schemas.product import ProductOut

INITIAL_PRODUCTS: list[dict[str, str | float | int]] = [
    {"name": "Ultra-Slim Laptop Pro", "description": "14-inch M3 powerhouse with 32GB RAM and 1TB SSD", "price": 1499.99, "stock": 50},
    {"name": "Ergonomic Mechanical Keyboard", "description": "Wireless mechanical keyboard with hot-swappable switches", "price": 129.50, "stock": 120},
    {"name": "Noise-Cancelling Headphones", "description": "Over-ear wireless headphones with 40-hour battery life", "price": 249.00, "stock": 85},
    {"name": "4K Ultra-Wide Monitor", "description": "34-inch curved display with 144Hz refresh rate", "price": 599.99, "stock": 40},
    {"name": "Precision Wireless Mouse", "description": "Ergonomic high-DPI mouse with magnetic scroll wheel", "price": 79.99, "stock": 200},
    {"name": "USB-C Dual 4K Docking Station", "description": "12-in-1 multi-port hub with 100W Power Delivery", "price": 159.00, "stock": 75},
    {"name": "Studio Quality USB Microphone", "description": "Cardioid condenser mic with built-in pop filter", "price": 109.95, "stock": 90},
    {"name": "1080p AI Auto-Focus Webcam", "description": "Full HD webcam with dual noise-cancelling mics", "price": 69.50, "stock": 110},
    {"name": "Adjustable Aluminum Laptop Stand", "description": "Foldable ergonomic riser for laptops and tablets", "price": 39.99, "stock": 300},
    {"name": "High-Speed Qi Wireless Charger", "description": "15W fast charging pad with LED status indicator", "price": 29.99, "stock": 250},
    {"name": "Smart LED Desk Lamp", "description": "Dimmable eye-caring desk lamp with color temperature control", "price": 49.99, "stock": 140},
    {"name": "Surge Protector Power Strip", "description": "8 AC outlets and 4 USB fast charge ports", "price": 34.50, "stock": 180},
]


class CatalogService:
    def __init__(self, repository: ProductRepositoryProtocol) -> None:
        self.repository = repository

    async def get_all_products(self) -> list[ProductOut]:
        products = await self.repository.get_all()
        return [ProductOut.model_validate(p) for p in products]

    async def get_product_by_id(self, product_id: int) -> ProductOut | None:
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None
        return ProductOut.model_validate(product)

    async def seed_initial_products_if_empty(self) -> int:
        count = await self.repository.count()
        if count == 0:
            products_to_seed = [
                Product(
                    name=str(item["name"]),
                    description=str(item["description"]),
                    price=float(item["price"]),
                    stock=int(item["stock"]),
                )
                for item in INITIAL_PRODUCTS
            ]
            await self.repository.bulk_create(products_to_seed)
            logger.info(f"Seeded {len(products_to_seed)} initial catalog products")
            return len(products_to_seed)
        return 0
