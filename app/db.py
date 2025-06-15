from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL
from app.models import Base  # Import Base for table creation
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug(f"Connecting to database: {DATABASE_URL}")
try:
    engine = create_engine(DATABASE_URL)
    logger.debug("Database engine created successfully")
except Exception as e:
    logger.error(f"Error creating database engine: {e}", exc_info=True)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    logger.debug("Initializing database tables")
    try:
        Base.metadata.create_all(bind=engine)
        logger.debug("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}", exc_info=True)
        raise

def get_db():
    logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()
