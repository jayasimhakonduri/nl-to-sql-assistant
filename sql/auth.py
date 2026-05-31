"""API key auth for NL-to-SQL service."""
from fastapi import Header, HTTPException, status
from sql.config import settings

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")
    return x_api_key
