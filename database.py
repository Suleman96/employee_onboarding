from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR  = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{(DATA_DIR / 'employees.db').as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

_now = lambda: datetime.now(timezone.utc)  # noqa: E731  — used as column default


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    # ── Personal ──────────────────────────────────────────────────────────────
    first_name    = Column(String, nullable=True)
    middle_name   = Column(String, nullable=True)
    last_name     = Column(String, nullable=True)
    gender        = Column(String, nullable=True, default="unspecified")
    date_of_birth = Column(String, nullable=True)
    place_of_birth   = Column(String, nullable=True)
    country_of_birth = Column(String, nullable=True)
    nationality      = Column(String, nullable=True)
    marital_status   = Column(String, nullable=True)

    # ── Identity documents ────────────────────────────────────────────────────
    ausweis_number        = Column(String, nullable=True)
    ausweis_expiry_date   = Column(String, nullable=True)
    reise_pass_number     = Column(String, nullable=True)
    reise_pass_expiry_date = Column(String, nullable=True)
    working_permit_number = Column(String, nullable=True)
    working_permit_expiry = Column(String, nullable=True)
    visa_number           = Column(String, nullable=True)
    visa_expiry           = Column(String, nullable=True)

    # ── Contact ───────────────────────────────────────────────────────────────
    street_and_house_number  = Column(String, nullable=True)
    phone                    = Column(String, nullable=True)
    emergency_contact_name   = Column(String, nullable=True)
    emergency_contact_phone  = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    city     = Column(String, nullable=True)
    email    = Column(String, nullable=True, unique=True)
    country  = Column(String, nullable=True, default="Deutschland")

    # ── Insurance & tax ───────────────────────────────────────────────────────
    krankenkasse            = Column(String,  nullable=True)
    krankenkasse_nummer     = Column(String,  nullable=True)
    steuer_id               = Column(String,  nullable=True)
    steuerklasse            = Column(Integer, nullable=True)
    sozialversicherungsnummer = Column(String, nullable=True)

    # ── Banking ───────────────────────────────────────────────────────────────
    bank_name           = Column(String, nullable=True)
    bank_bic            = Column(String, nullable=True)
    bank_account_holder = Column(String, nullable=True)
    bank_iban           = Column(String, nullable=True)

    # ── Employment ────────────────────────────────────────────────────────────
    work_city             = Column(String,  nullable=True)
    department            = Column(String,  nullable=True)
    employment_type       = Column(String,  nullable=True)
    occupation            = Column(String,  nullable=True)
    position_level        = Column(String,  nullable=True)
    weekly_hours          = Column(Float,   nullable=True)
    work_days_per_week    = Column(Float,   nullable=True)
    daily_hours           = Column(Float,   nullable=True)
    start_date            = Column(String,  nullable=True)
    contract_type         = Column(String,  nullable=True, default="temporary")
    hotel_name            = Column(String,  nullable=True)
    end_date              = Column(String,  nullable=True)
    probation_period_months = Column(Integer, nullable=True)
    previous_employer     = Column(String,  nullable=True)
    education_level       = Column(String,  nullable=True)

    # ── Accessibility ─────────────────────────────────────────────────────────
    disabled = Column(Boolean, nullable=True, default=False)

    # ── System ────────────────────────────────────────────────────────────────
    status   = Column(String, nullable=True, default="draft")
    ordio_id = Column(String, nullable=True)

    last_contract_path                  = Column(String,   nullable=True)
    last_contract_generated_at          = Column(DateTime, nullable=True)
    last_contract_pdf_path              = Column(String,   nullable=True)
    last_contract_pdf_path_generated_at = Column(DateTime, nullable=True)

    upload_session_dir         = Column(String, nullable=True)  # employee upload root
    latest_upload_session_dir  = Column(String, nullable=True)  # latest uploads/.../upload_NNNN/
    collected_docs_docx = Column(String, nullable=True)  # path to collected/<slug>.docx

    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String,   nullable=True)
    is_deleted  = Column(Boolean,  default=False)
    deleted_reason = Column(String, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id           = Column(Integer, primary_key=True)
    action       = Column(String)   # create / update / delete / approve / reject
    employee_id  = Column(Integer)
    details      = Column(Text)     # JSON string of what changed
    performed_by = Column(String)
    timestamp    = Column(DateTime, default=_now)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    # Add columns that may not exist in older databases (safe no-op if already present)
    with engine.connect() as conn:
        for ddl in [
            "ALTER TABLE employees ADD COLUMN upload_session_dir TEXT",
            "ALTER TABLE employees ADD COLUMN latest_upload_session_dir TEXT",
            "ALTER TABLE employees ADD COLUMN collected_docs_docx TEXT",
        ]:
            try:
                conn.execute(text(ddl))
                conn.commit()
            except Exception:
                pass  # column already exists


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
