from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/fastapi_db")
DEVELOPMENT = os.getenv("DEVELOPMENT", "true").lower() == "true"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=DEVELOPMENT
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
