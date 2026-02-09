from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from schemas.database import Base, ArtifactModel
import os
```.

class DBManager:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        # This is the correct way to trigger table creation
        Base.metadata.create_all(bind=self.engine)
