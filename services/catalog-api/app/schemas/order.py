from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(1, gt=0)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    @computed_field
    @property
    def order_id(self) -> int:
        return self.id
