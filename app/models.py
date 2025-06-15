from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class SprintStatus(enum.Enum):
    active = "active"
    completed = "completed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

class Sprint(Base):
    __tablename__ = "sprints"
    id = Column(Integer, primary_key=True)
    duration = Column(Integer, nullable=False)
    theme = Column(String, nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    status = Column(Enum(SprintStatus), default=SprintStatus.active)

class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    sprint_id = Column(Integer, nullable=False)
    words = Column(String, nullable=False)
    language = Column(String, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
