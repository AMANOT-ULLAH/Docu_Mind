from pydantic import BaseModel, Field
from typing import Literal, Optional

class PageResult(BaseModel):
    page_number: int
    method: Literal["digital", "ocr", "table"]
    text: str
    confidence: Optional[float] = None
    low_conf_words: Optional[float] = None   # সন্দেহজনক শব্দের শতাংশ

class ExtractionResult(BaseModel):
    file_name: str
    file_type: Literal["pdf", "image", "excel", "csv", "unknown"]
    file_hash: str
    status: Literal["success", "partial", "failed"]
    pages: list[PageResult] = Field(default_factory=list)
    tables: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    processing_seconds: float = 0.0