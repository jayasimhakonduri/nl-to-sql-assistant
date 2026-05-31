"""NL-to-SQL Configuration"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/finops"
    API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
