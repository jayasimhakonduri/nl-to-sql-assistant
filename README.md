# 🔍 NL-to-SQL Data Assistant

> Natural language query engine over PostgreSQL databases. Ask questions in plain English — get back SQL + results. Built with **Azure OpenAI GPT-4o**, **FastAPI**, and **asyncpg**. Reduced ad-hoc SQL requests by **70%** in production.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green) ![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-purple) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)

---

## 🧠 How It Works

```
User: "What are the top 10 most expensive AWS services this month?"
         │
         ▼
  1. Load DB schema (tables + columns) from PostgreSQL
         │
         ▼
  2. Schema-aware prompt → Azure OpenAI GPT-4o
         │
         ▼
  3. Generated SQL:
     SELECT service, SUM(cost_usd) AS total
     FROM billing_daily_rollup
     WHERE provider = 'aws'
       AND date >= DATE_TRUNC('month', NOW())
     GROUP BY service
     ORDER BY total DESC
     LIMIT 10
         │
         ▼
  4. Safety validation (SELECT-only, no DDL/DML)
         │
         ▼
  5. Execute + return results as JSON table
```

## ✨ Key Features

| Feature | Detail |
|---|---|
| Schema-aware | Reads live DB schema before generating SQL — no hallucinated columns |
| Safety first | SQLValidator blocks all non-SELECT queries (INSERT, DROP, etc.) |
| Explain plan | Optionally returns PostgreSQL EXPLAIN output |
| Multi-DB | Supports different databases via `database` param |
| Zero-shot | No fine-tuning needed — GPT-4o + schema prompt is enough |
| Async end-to-end | asyncpg + AsyncAzureOpenAI |

## 📊 Production Impact

- **70% reduction** in ad-hoc SQL requests from non-technical users
- Self-serve analytics for FinOps, Product, and Business teams
- Powers natural language access to 100M+ billing records

## 🚀 Quick Start

```bash
git clone https://github.com/jayasimhakonduri/nl-to-sql-assistant
cd nl-to-sql-assistant
pip install -r requirements.txt
cp .env.example .env
python main.py   # API at http://localhost:8002/docs
```

## 📡 API Examples

### Ask a question
```bash
curl -X POST http://localhost:8002/api/v1/query \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show total cloud spend by team for Q4 2024",
    "database": "finops",
    "explain": true,
    "max_rows": 50
  }'
```

Response:
```json
{
  "question": "Show total cloud spend by team for Q4 2024",
  "sql": "SELECT tag_team, SUM(total_cost_usd) AS spend FROM billing_daily_rollup WHERE date BETWEEN '2024-10-01' AND '2024-12-31' GROUP BY tag_team ORDER BY spend DESC LIMIT 50",
  "columns": ["tag_team", "spend"],
  "rows": [{"tag_team": "platform", "spend": 42000.5}, ...],
  "row_count": 8,
  "explain_plan": ["GroupAggregate  (cost=12.45..14.23 rows=8)"],
  "is_safe": true
}
```

### Validate SQL without running it
```bash
curl -X POST "http://localhost:8002/api/v1/validate-sql?sql=DROP+TABLE+billing" \
  -H "X-API-Key: your-key"
# Returns: {"is_safe": false, "reason": "Only SELECT statements are allowed. Got: DROP"}
```

## 📁 Project Structure

```
nl-to-sql-assistant/
├── main.py              # FastAPI app + routes
├── sql/
│   ├── generator.py     # Schema load + GPT-4o SQL gen + execution
│   ├── validator.py     # SQL safety checker (SELECT-only enforcement)
│   ├── models.py        # Pydantic request/response schemas
│   ├── config.py        # Settings from .env
│   └── auth.py          # API key auth
└── requirements.txt
```

---

Built by [Jaya Simha Konduri](https://linkedin.com/in/jaya-simha-713234130) · [Portfolio](https://jayasimhakonduri.github.io)
