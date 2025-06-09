# === models.py ===

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timedelta

Base = declarative_base()


class Sprint(Base):
    __tablename__ = "sprints"
    id = Column(Integer, primary_key=True)
    topic = Column(String, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    active = Column(Boolean, default=True)
    words = relationship("Word", back_populates="sprint")


class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=False)
    text = Column(String, nullable=False)
    language = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sprint = relationship("Sprint", back_populates="words")


