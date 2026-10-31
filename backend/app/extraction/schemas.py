from typing import Literal, Optional
from pydantic import BaseModel


class TextField(BaseModel):
    value: Optional[str]        # না পেলে null
    evidence: Optional[str]     # document থেকে হুবহু যে অংশ দেখে value নিয়েছে
    confidence: Literal["high", "medium", "low"]


class NumberField(BaseModel):
    value: Optional[float]
    evidence: Optional[str]
    confidence: Literal["high", "medium", "low"]


class LineItem(BaseModel):
    description: Optional[str]
    quantity: Optional[float]
    unit_price: Optional[float]
    amount: Optional[float]
    evidence: Optional[str]


class InvoiceExtraction(BaseModel):
    invoice_number: TextField
    invoice_date: TextField     # YYYY-MM-DD
    supplier_name: TextField
    customer_name: TextField
    subtotal: NumberField
    tax: NumberField
    total: NumberField
    currency: TextField         # যেমন BDT, USD
    line_items: list[LineItem]
    notes: list[str]            # অস্পষ্ট বা সন্দেহজনক কিছু থাকলে