from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.orm import sessionmaker, declarative_base

# Project root = folder where database.py is located
BASE_DIR = Path(__file__).resolve().parent

# Data folder inside project root
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Creates employee.db in the data/ directory if it doesn't exist yet
DATABASE_PATH = (DATA_DIR / "employees.db").resolve()
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit =False, autoflush=False)
Base = declarative_base()

class Employee(Base):
    __tablename__ = "employees"
    id            = Column(Integer, primary_key=True, index=True)
    first_name    = Column(String, nullable=True)
    last_name     = Column(String, nullable=True)
    gender        = Column(String, nullable=True, default="unspecified")
    date_of_birth = Column(String, nullable=True)
    place_of_birth   = Column(String, nullable=True)
    country_of_birth = Column(String, nullable=True)

    
    nationality       = Column(String, nullable=True)
    street_and_house_number = Column(String, nullable=True)
    phone             = Column(String, nullable=True)
    zip_code          = Column(String, nullable=True)
    city              = Column(String, nullable=True)
    email             = Column(String, nullable=True, unique=True)
    country           = Column(String, nullable=True, default="Deutschland")
    
    
    steuer_id     = Column(String, nullable=True)
    steuerklasse  = Column(Integer, nullable=True)
    iban          = Column(String, nullable=True)
    start_date    = Column(String, nullable=True)
    contract_type = Column(String, nullable=True)
    end_date      = Column(String, nullable=True)
    disabled      = Column(String, nullable=True, default=False)
    status        = Column(String, nullable=True, default="pending")
    ordio_id      = Column(String, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at   = Column(DateTime, nullable=True)
    approved_by   = Column(String, nullable=True)
    is_deleted    = Column(Boolean, default=False)
    deleted_reason= Column(String, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id           = Column(Integer, primary_key=True)
    action       = Column(String)   # create/update/delete/approve/reject
    employee_id  = Column(Integer)
    details      = Column(Text)     # JSON string of what changed
    performed_by = Column(String)   # who did this action
    timestamp    = Column(DateTime, default=datetime.utcnow)

# Creates tables if they don't exist yet — safe to run multiple times

def create_tables():
    Base.metadata.create_all(bind=engine)


# Dependency for FastAPI routes
# This function can be used in FastAPI routes to get a database session
def get_db():
    db = SessionLocal()
    try:
        # The yield statement allows the function to be used as a context manager in FastAPI routes. It provides a database session to the route handler, and after the request is processed, it ensures that the session is properly closed.
        yield db
    finally:
        # It ensures that the session is properly closed after the request is done
        db.close()

