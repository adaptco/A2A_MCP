from sqlalchemy import create_all
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from schemas.database import Base
import os

# Using SQLite for Phase 1 local dev, can easily swap to Postgres via ENV
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./a2a_mcp.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
