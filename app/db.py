from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.config import DATABASE_URL
from app.models import Base, Sprint, Word

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def start_sprint(duration_days: int, topic: str) -> int:
    session = Session()
    sprint = Sprint(topic=topic, ends_at=datetime.utcnow() + timedelta(days=duration_days))
    session.add(sprint)
    session.commit()
    sprint_id = sprint.id
    session.close()
    return sprint_id

def end_sprint(sprint_id: int):
    session = Session()
    session.execute(update(Sprint).where(Sprint.id == sprint_id).values(active=False))
    session.commit()
    session.close()

def get_active_sprints() -> list[int]:
    session = Session()
    now = datetime.utcnow()
    result = session.scalars(select(Sprint.id).where(Sprint.active == True, Sprint.ends_at > now)).all()
    session.close()
    return result

def add_word(user_id: int, sprint_id: int, text: str, language: str):
    session = Session()
    word = Word(user_id=user_id, sprint_id=sprint_id, text=text, language=language)
    session.add(word)
    session.commit()
    session.close()

def get_words_for_sprint(sprint_id: int) -> list[tuple[str, str]]:
    session = Session()
    words = session.query(Word.text, Word.language).filter_by(sprint_id=sprint_id).all()
    session.close()
    return words
