from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./modelfactory.db"

engine       = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

class Base(DeclarativeBase):
    pass

def init_db():
    from backend.database.models import (
        ModelRecord, TrainingSession, ActionSequence,
        CheckpointRecord, MacroRecord, LiveRunRecord
    )
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
