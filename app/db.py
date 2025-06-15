from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.config import DATABASE_URL
from contextlib import contextmanager

logger.debug(f"Connecting to database: {DATABASE_URL}")
@contextmanager
try:
    engine = create_engine(DATABASE_URL)
    logger.debug("Database engine created successfully")
except Exception as e:
    logger.error(f"Error creating database engine: {e}", exc_info=True)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize database: {e}")

def get_db():
    logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()
