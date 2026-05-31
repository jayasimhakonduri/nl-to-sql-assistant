"""
NL-to-SQL Data Assistant — FastAPI Application
Converts natural language questions into safe, optimized SQL queries
using Azure OpenAI + schema-aware prompting.
Author: Jaya Simha Konduri
"""
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from sql.generator import NLToSQLGenerator
from sql.models import QueryRequest, QueryResponse, SchemaRequest
from sql.auth import verify_api_key
from sql.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing NL-to-SQL Assistant...")
    app.state.generator = NLToSQLGenerator()
    await app.state.generator.initialize()
    logger.info("NL-to-SQL ready.")
    yield
    await app.state.generator.close()


app = FastAPI(
    title="NL-to-SQL Data Assistant",
    description=(
        "Natural language query engine over relational databases. "
        "Schema-aware SQL generation with safety validation, explain plans, "
        "and result formatting. Built with Azure OpenAI + FastAPI + PostgreSQL."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nl-to-sql"}


@app.post("/api/v1/query", response_model=QueryResponse)
async def natural_language_query(
    request: QueryRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Convert a natural language question into SQL and execute it.
    - Schema-aware: loads table definitions before generating SQL
    - Safety validated: blocks DDL/DML, only allows SELECT
    - Explain plan: optionally returns query plan for transparency
    - Result formatted: returns tabular data with column names
    """
    try:
        gen: NLToSQLGenerator = app.state.generator
        result = await gen.query(
            question=request.question,
            database=request.database,
            explain=request.explain,
            max_rows=request.max_rows,
        )
        return QueryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"NL-to-SQL error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/validate-sql")
async def validate_sql(
    sql: str,
    api_key: str = Depends(verify_api_key),
):
    """Validate SQL for safety without executing it."""
    from sql.validator import SQLValidator
    validator = SQLValidator()
    result = validator.validate(sql)
    return result


@app.get("/api/v1/schema/{database}")
async def get_schema(
    database: str,
    api_key: str = Depends(verify_api_key),
):
    """Return the schema (tables + columns) for the given database."""
    gen: NLToSQLGenerator = app.state.generator
    schema = await gen.get_schema(database)
    return {"database": database, "schema": schema}


@app.get("/api/v1/examples")
async def get_example_queries():
    """Return example NL questions to help users get started."""
    return {
        "examples": [
            "What are the top 10 most expensive AWS services this month?",
            "Show total cloud spend by team for Q4 2024",
            "Which Azure VMs have been running for more than 30 days?",
            "What is the daily cost trend for EC2 over the last 7 days?",
            "List all resources tagged with project=marketing and their costs",
            "Compare cloud spend between AWS and Azure for each month in 2024",
        ]
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
