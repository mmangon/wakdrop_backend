from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/wakdrop")
    wakfu_cdn_base_url: str = "https://wakfu.cdn.ankama.com/gamedata"
    wakfu_version: str = "1.88.1.39"
    
    class Config:
        env_file = ".env"

settings = Settings()