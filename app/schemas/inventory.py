from pydantic import BaseModel

class InventoryOut(BaseModel):
    product_name: str
    quantity: int
    price: float
