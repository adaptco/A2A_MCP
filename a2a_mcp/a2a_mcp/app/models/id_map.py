from sqlalchemy import Column, Integer, String, JSON

from .base import Base


class IdMap(Base):
    __tablename__ = "id_map"

    id = Column(Integer, primary_key=True, index=True)
    monday_item_id = Column(String, unique=True, nullable=False)
    airtable_id = Column(String, nullable=True)
    clickup_id = Column(String, nullable=True)
    notion_id = Column(String, nullable=True)
    github_refs = Column(JSON, default=list)
