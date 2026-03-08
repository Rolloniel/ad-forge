from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgres://adforge:password@localhost:5432/adforge"
    OPENAI_API_KEY: str = ""
    FAL_KEY: str = ""
    HEYGEN_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    ADFORGE_API_KEY: str = ""
    WORKER_COUNT: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
