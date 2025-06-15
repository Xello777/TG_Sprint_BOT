from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class SprintStatus(enum.Enum):
    active = "active"
    completed = "completed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)  # Telegram user ID
    username = Column(String, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

class Sprint(Base):
    __tablename__ = "sprints"
    id = Column(Integer, primary_key=True)
    duration = Column(Integer)  # 1, 7, or 30 days
    theme = Column(String)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    status = Column(Enum(SprintStatus), default=SprintStatus.active)

class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    sprint_id = Column(Integer, ForeignKey("sprints.id"))
    words = Column(String)
    language = Column(String)
    submitted_at = Column(DateTime, default=datetime.utcnow)
