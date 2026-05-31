"""Pydantic models for NL-to-SQL API"""
from pydantic import BaseModel, Field
from typing import List, Any, Optional


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    database: str = Field(default="finops")
    explain: bool = Field(default=False)
    max_rows: int = Field(default=100, ge=1, le=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the top 5 most expensive AWS services this month?",
                "database": "finops",
                "explain": True,
                "max_rows": 50,
            }
        }


class QueryResponse(BaseModel):
    question: str
    sql: str
    columns: List[str]
    rows: List[dict]
    row_count: int
    explain_plan: List[str]
    is_safe: bool
    database: str


class SchemaRequest(BaseModel):
    database: str
