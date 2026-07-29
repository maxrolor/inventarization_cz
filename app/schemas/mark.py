from pydantic import BaseModel

class MarkBalanceOut(BaseModel):
    gtin: str
    total_quantity: int
