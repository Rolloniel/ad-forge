from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://adforge:password@localhost:5432/adforge"
    openai_api_key: str = ""
    fal_key: str = ""
    heygen_api_key: str = ""
    elevenlabs_api_key: str = ""
    adforge_api_key: str = "dev-key"
    worker_count: int = 3

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
