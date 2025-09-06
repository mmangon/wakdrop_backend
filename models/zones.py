from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base

class Zone(Base):
    """
    Zones géographiques de Wakfu
    """
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    min_level = Column(Integer, nullable=True)  # Niveau minimum recommandé
    max_level = Column(Integer, nullable=True)  # Niveau maximum recommandé
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relation vers les monstres via MonsterZone
    monster_zones = relationship("MonsterZone", back_populates="zone", cascade="all, delete-orphan")

class MonsterZone(Base):
    """
    Association between monsters and zones (many-to-many)
    Un monstre peut être dans plusieurs zones, une zone peut avoir plusieurs monstres
    """
    __tablename__ = "monster_zones"
    
    id = Column(Integer, primary_key=True, index=True)
    monster_id = Column(Integer, nullable=False, index=True)  # ID du monstre depuis monster_drops
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    
    # Informations spécifiques à cette combinaison monstre/zone
    spawn_frequency = Column(String(50), nullable=True)  # "Common", "Rare", "Boss", etc.
    notes = Column(Text, nullable=True)  # Notes spécifiques
    
    # Relations
    zone = relationship("Zone", back_populates="monster_zones")