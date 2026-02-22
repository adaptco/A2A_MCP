from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONDAY_TOKEN: str = ""
    MONDAY_BOARD_ID: int = 0
    AIRTABLE_API_KEY: str = ""
    AIRTABLE_BASE_ID: str = ""
    AIRTABLE_TABLE: str = "Monday Tasks"
    PORT: int = 8080
    ENV: str = "dev"
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    ALLOW_MONDAY_WRITES: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
