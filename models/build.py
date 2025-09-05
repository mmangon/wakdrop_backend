from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from core.database import Base

class Build(Base):
    __tablename__ = "builds"
    
    id = Column(Integer, primary_key=True, index=True)
    zenith_url = Column(String, unique=True, index=True, nullable=False)
    zenith_id = Column(String, index=True, nullable=False)
    items_ids = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())