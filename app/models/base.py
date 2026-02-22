from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from ..config import settings

Base = declarative_base()
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)
