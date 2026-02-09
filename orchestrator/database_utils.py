from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schemas.database import Base  # This fixes the "Base is not defined" error
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./a2a_mcp.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)