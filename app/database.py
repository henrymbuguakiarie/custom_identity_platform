from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings

DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/database_name"

class Settings(BaseSettings):
    database_url: str = DATABASE_URL
settings = Settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()