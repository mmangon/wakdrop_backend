from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from core.database import Base

class CachedItem(Base):
    __tablename__ = "cached_items"
    
    id = Column(Integer, primary_key=True, index=True)
    wakfu_id = Column(Integer, unique=True, index=True, nullable=False)
    data_json = Column(JSON, nullable=False)
    obtention_type = Column(String, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

class FarmAnalysis(Base):
    __tablename__ = "farm_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(Integer, index=True, nullable=False)
    item_id = Column(Integer, nullable=False)
    obtention_type = Column(String, nullable=False)  # "craft", "drop", "shop", "quest"
    farm_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())