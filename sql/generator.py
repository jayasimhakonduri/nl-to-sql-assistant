"""
NL-to-SQL Generator
- Loads DB schema dynamically
- Builds schema-aware system prompt
- Calls Azure OpenAI to generate SQL
- Validates SQL for safety
- Executes query via asyncpg
- Returns formatted results
"""
import asyncio
import asyncpg
from openai import AsyncAzureOpenAI
from loguru import logger
from typing import Any

from sql.validator import SQLValidator
from sql.config import settings


SYSTEM_PROMPT_TEMPLATE = """You are an expert SQL assistant for PostgreSQL databases.
You will be given a database schema and a natural language question.
Your job is to write a correct, optimized, read-only SELECT query.

Rules:
1. Only write SELECT statements. NEVER write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE.
2. Always use table aliases for readability.
3. Add a LIMIT clause if the question doesn't specify a count (default LIMIT 100).
4. Use proper JOIN types based on the question context.
5. For date/time filtering, use PostgreSQL date functions (NOW(), DATE_TRUNC, INTERVAL).
6. Return ONLY the SQL query — no explanation, no markdown, no backticks.

Database Schema:
{schema}
"""


class NLToSQLGenerator:
    def __init__(self):
        self.openai: AsyncAzureOpenAI | None = None
        self.db_pool: asyncpg.Pool | None = None
        self.validator = SQLValidator()
        self._schema_cache: dict[str, str] = {}

    async def initialize(self):
        self.openai = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
        self.db_pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=2, max_size=10)
        logger.info("NLToSQLGenerator initialized.")

    async def close(self):
        if self.db_pool:
            await self.db_pool.close()

    # ── Schema loading ─────────────────────────────────────────
    async def get_schema(self, database: str) -> str:
        if database in self._schema_cache:
            return self._schema_cache[database]

        schema_query = """
            SELECT
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                col_description(
                    ('"' || t.table_schema || '"."' || t.table_name || '"')::regclass,
                    c.ordinal_position
                ) AS column_comment
            FROM information_schema.tables t
            JOIN information_schema.columns c
                ON t.table_name = c.table_name AND t.table_schema = c.table_schema
            WHERE t.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name, c.ordinal_position;
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(schema_query)

        # Format schema as readable DDL-like text
        tables: dict = {}
        for row in rows:
            tname = row["table_name"]
            if tname not in tables:
                tables[tname] = []
            nullable = "" if row["is_nullable"] == "YES" else " NOT NULL"
            comment = f"  -- {row['column_comment']}" if row["column_comment"] else ""
            tables[tname].append(
                f"    {row['column_name']} {row['data_type'].upper()}{nullable}{comment}"
            )

        schema_text = "\n\n".join([
            f"Table: {tname}\n(\n" + ",\n".join(cols) + "\n)"
            for tname, cols in tables.items()
        ])

        self._schema_cache[database] = schema_text
        return schema_text

    # ── SQL generation ─────────────────────────────────────────
    async def _generate_sql(self, question: str, schema: str) -> str:
        system = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)
        response = await self.openai.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            max_tokens=500,
            temperature=0.0,    # Deterministic SQL generation
        )
        sql = response.choices[0].message.content.strip()
        # Strip any accidental markdown
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql

    # ── Execution ──────────────────────────────────────────────
    async def _execute(self, sql: str, max_rows: int) -> dict[str, Any]:
        limited_sql = sql.rstrip(";")
        if "limit" not in limited_sql.lower():
            limited_sql += f" LIMIT {max_rows}"

        async with self.db_pool.acquire() as conn:
            # Get explain plan
            explain_rows = await conn.fetch(f"EXPLAIN {limited_sql}")
            explain_plan = [r["QUERY PLAN"] for r in explain_rows]

            # Execute
            rows = await conn.fetch(limited_sql)

        if not rows:
            return {"columns": [], "rows": [], "row_count": 0, "explain_plan": explain_plan}

        columns = list(rows[0].keys())
        data = [dict(row) for row in rows]

        # Convert non-serializable types
        for row in data:
            for k, v in row.items():
                if hasattr(v, "isoformat"):
                    row[k] = v.isoformat()
                elif not isinstance(v, (str, int, float, bool, type(None))):
                    row[k] = str(v)

        return {
            "columns": columns,
            "rows": data,
            "row_count": len(data),
            "explain_plan": explain_plan,
        }

    # ── Public: query ──────────────────────────────────────────
    async def query(self, question: str, database: str,
                    explain: bool, max_rows: int) -> dict:
        schema = await self.get_schema(database)
        sql = await self._generate_sql(question, schema)
        logger.info(f"Generated SQL: {sql}")

        # Validate before executing
        validation = self.validator.validate(sql)
        if not validation["is_safe"]:
            raise ValueError(f"Unsafe SQL generated: {validation['reason']}")

        result = await self._execute(sql, max_rows)

        return {
            "question": question,
            "sql": sql,
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": result["row_count"],
            "explain_plan": result["explain_plan"] if explain else [],
            "is_safe": True,
            "database": database,
        }
