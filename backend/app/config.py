from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tactile_api_base: str = "http://118.31.57.25/tactile/api"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 168
    database_url: str = "sqlite+aiosqlite:///./data/writer.db"
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
