from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_catalog_service
from app.schemas.product import ProductOut
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def list_products(
    service: CatalogService = Depends(get_catalog_service),
) -> list[ProductOut]:
    return await service.get_all_products()


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    service: CatalogService = Depends(get_catalog_service),
) -> ProductOut:
    product = await service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )
    return product
