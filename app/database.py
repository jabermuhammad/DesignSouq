import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app import config as _config  # ensure .env is loaded

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.hlfoqhbqqmuksqnmfrgj:YourStrongAdminPass123!@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=disable",
)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
