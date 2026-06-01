import csv
import json
import subprocess
import time
import traceback
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from urllib.parse import quote

from config import MISTRAL_API_KEY, OCR_ENGINE
from contracts.generator import convert_docx_to_pdf, generate_contract_for_employee
from contracts.resolver import normalize_contract_attributes, resolve_template_path
from database import AuditLog, Employee, create_tables, get_db
from pipeline import process_uploaded_files
from schemas import AuditLogResponse, EmployeeCreate, EmployeeResponse

# ── Constants ────────────────────────────────────────────────────────────────

# All Employee model fields that map directly to form inputs.
# hotel_name is derived from hotel_name_select + hotel_name_custom; see _collect_form_data.
_EMPLOYEE_FIELDS = (
    "first_name", "middle_name", "last_name", "gender", "date_of_birth",
    "place_of_birth", "country_of_birth", "nationality", "marital_status",

    "ausweis_number", "ausweis_expiry_date", "reise_pass_number", "reise_pass_expiry_date",
    "working_permit_number", "working_permit_expiry", "visa_number", "visa_expiry",

    "street_and_house_number", "phone", "emergency_contact_name", "emergency_contact_phone",
    "zip_code", "city", "email", "country",

    "krankenkasse", "krankenkasse_nummer", "steuer_id", "steuerklasse", "sozialversicherungsnummer",

    "bank_name", "bank_iban", "bank_bic", "bank_account_holder",

    "work_city", "hotel_name", "department", "employment_type", "occupation", "position_level",
    "weekly_hours", "work_days_per_week", "daily_hours",
    "start_date", "contract_type", "end_date", "probation_period_months",
    "previous_employer", "education_level",

    "disabled", "status", "ordio_id",
)

_APPROVAL_REQUIRED_FIELDS = (
    "first_name", "last_name", "date_of_birth",
    "street_and_house_number", "city", "start_date",
)

# ── App setup ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    n8n_process = None
    try:
        n8n_process = subprocess.Popen("n8n", shell=True)
        print("n8n started on http://localhost:5678")
    except Exception as exc:
        print(f"Warning: n8n could not be started ({exc})")
    webbrowser.open("http://localhost:8000")
    yield
    if n8n_process:
        n8n_process.terminate()


app = FastAPI(lifespan=lifespan, title="Employee Onboarding System", version="0.1.0")
templates = Jinja2Templates(directory="templates")

_ALLOWED_OCR_ENGINES = {"rapidocr", "tesseract", "auto", "mistral"}
_ALLOWED_AI_EXTRACTORS = {"local", "mistral"}


def _normalize_upload_choice(value: str | None, allowed: set[str], default: str) -> str:
    choice = (value or default).strip().lower()
    return choice if choice in allowed else default

# ── Shared helpers ───────────────────────────────────────────────────────────

def _get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


def _audit(db: Session, action: str, employee_id: int, details: Any, performed_by: str = "system") -> None:
    db.add(AuditLog(
        action=action,
        employee_id=employee_id,
        details=details if isinstance(details, str) else json.dumps(details, ensure_ascii=False),
        performed_by=performed_by,
    ))


def normalize_hotel_name(select: str | None, custom: str | None) -> str | None:
    if select == "other":
        return (custom or "").strip() or None
    return select if select not in (None, "", "none") else None


def _collect_form_data(form_locals: dict, hotel_name_select: str, hotel_name_custom: str) -> dict:
    """
    Build a clean {field: value} dict from the handler's locals(), resolving the
    split hotel_name_select / hotel_name_custom inputs into a single hotel_name value.
    """
    data = {f: form_locals.get(f) for f in _EMPLOYEE_FIELDS if f != "hotel_name"}
    data["hotel_name"] = normalize_hotel_name(hotel_name_select, hotel_name_custom)
    if data.get("email"):
        data["email"] = data["email"].strip().lower()
    return data


def get_approval_missing_fields(employee: Employee) -> List[str]:
    return [f for f in _APPROVAL_REQUIRED_FIELDS if not getattr(employee, f, None)]


def _discover_employee_upload_sessions(employee: Employee) -> list[dict]:
    root = Path(employee.upload_session_dir) if employee.upload_session_dir else None
    session_dirs: list[Path] = []

    if root and root.exists():
        if (root / "originals").exists() or (root / "extracted_images").exists():
            session_dirs.append(root)
        session_dirs.extend(
            sorted(
                (p for p in root.iterdir() if p.is_dir() and p.name.startswith("upload_")),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        )

    latest = Path(employee.latest_upload_session_dir) if employee.latest_upload_session_dir else None
    if latest and latest.exists() and latest not in session_dirs:
        session_dirs.insert(0, latest)

    sessions = []
    seen: set[Path] = set()
    for session_dir in session_dirs:
        resolved = session_dir.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)

        originals_dir = session_dir / "originals"
        files = sorted(originals_dir.iterdir()) if originals_dir.exists() else []
        sessions.append({
            "name": session_dir.name,
            "route_name": session_dir.name,
            "path": session_dir,
            "files": [p for p in files if p.is_file()],
            "ocr_report": session_dir / "ocr_report.txt",
            "manifest": session_dir / "manifest.json",
            "modified_at": datetime.fromtimestamp(session_dir.stat().st_mtime),
        })
    return sessions


def _resolve_employee_file(employee: Employee, session_name: str, filename: str) -> Path:
    for session in _discover_employee_upload_sessions(employee):
        if session["route_name"] != session_name:
            continue
        originals_dir = (session["path"] / "originals").resolve()
        file_path = (originals_dir / filename).resolve()
        if originals_dir not in file_path.parents:
            raise HTTPException(status_code=400, detail="Invalid filename")
        if file_path.exists() and file_path.is_file():
            return file_path
    raise HTTPException(status_code=404, detail="File not found")

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    employees = db.query(Employee).order_by(Employee.created_at.desc()).all()
    return templates.TemplateResponse(request=request, name="index.html", context={"employees": employees})


@app.post("/api/employees/n8n-intake")
def create_employee_from_n8n(payload: EmployeeCreate, db: Session = Depends(get_db)):
    try:
        data = {f: getattr(payload, f, None) for f in _EMPLOYEE_FIELDS}
        data["country"]       = data.get("country") or "Deutschland"
        data["contract_type"] = data.get("contract_type") or "temporary"
        data["status"]        = data.get("status") or "draft"
        if data.get("disabled") is None:
            data["disabled"] = False

        new_employee = Employee(**data)
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)

        name = f"{new_employee.first_name or ''} {new_employee.last_name or ''}".strip()
        _audit(db, "create_from_n8n", new_employee.id, f"Created from n8n: {name}", performed_by="n8n")
        db.commit()

        return {"success": True, "employee_id": new_employee.id, "message": "Employee saved successfully"}

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "form_data": {},
            "selected_ocr_engine": "rapidocr",
            "selected_ai_extractor": "local",
            "mistral_available":     bool(MISTRAL_API_KEY),
        },
    )


@app.post("/upload/documents")
def upload_documents(
    request: Request,
    files: list[UploadFile] = File(default=[]),
    text_input: str = Form(default=""),
    employee_id: int | None = Form(default=None),
    ocr_engine:    str = Form(default="rapidocr"),
    ai_extractor:  str = Form(default="local"),
    db: Session = Depends(get_db),
):
    start = time.perf_counter()
    ocr_engine = _normalize_upload_choice(ocr_engine, _ALLOWED_OCR_ENGINES, "rapidocr")
    ai_extractor = _normalize_upload_choice(ai_extractor, _ALLOWED_AI_EXTRACTORS, "local")
    try:
        result = process_uploaded_files(
            db=db, files=files, text_input=text_input,
            employee_id=employee_id,
            ocr_engine_name=ocr_engine,
            ai_extractor_name=ai_extractor,
        )
        elapsed = time.perf_counter() - start
        print(f"Extraction completed in {elapsed:.2f}s ({elapsed/60:.2f} min)")

        log_file = Path("logs/upload_logs.csv")
        log_file.parent.mkdir(exist_ok=True)
        if not log_file.exists():
            log_file.write_text("Date,Files,Time\n")
        with log_file.open("a") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{len(files)},{elapsed/60:.2f}\n")

        return RedirectResponse(url=f"/review/{result['employee_id']}", status_code=303)

    except Exception as exc:
        traceback.print_exc()
        return templates.TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "form_data": {}, "selected_ocr_engine": ocr_engine,
                "selected_ai_extractor": ai_extractor,
                "mistral_available": bool(MISTRAL_API_KEY),
                "error_message": f"Upload processing failed: {exc}",
            },
            status_code=400,
        )


@app.post("/employees/new")
def create_employee(
    request: Request,
    first_name: str = Form(None),
    middle_name: str = Form(None),
    last_name: str = Form(None),
    gender: str = Form(None),
    date_of_birth: str = Form(None),
    place_of_birth: str = Form(None),
    country_of_birth: str = Form(None),
    nationality: str = Form(None),
    marital_status: str = Form(None),
    ausweis_number: str = Form(None),
    ausweis_expiry_date: str = Form(None),
    reise_pass_number: str = Form(None),
    reise_pass_expiry_date: str = Form(None),
    working_permit_number: str = Form(None),
    working_permit_expiry: str = Form(None),
    visa_number: str = Form(None),
    visa_expiry: str = Form(None),
    street_and_house_number: str = Form(None),
    phone: str = Form(None),
    emergency_contact_name: str = Form(None),
    emergency_contact_phone: str = Form(None),
    zip_code: str = Form(None),
    city: str = Form(None),
    email: str = Form(None),
    country: str = Form("Deutschland"),
    krankenkasse: str = Form(None),
    krankenkasse_nummer: str = Form(None),
    steuer_id: str = Form(None),
    steuerklasse: int = Form(None),
    sozialversicherungsnummer: str = Form(None),
    bank_name: str = Form(None),
    bank_iban: str = Form(None),
    bank_bic: str = Form(None),
    bank_account_holder: str = Form(None),
    hotel_name_select: str = Form(None),
    hotel_name_custom: str = Form(None),
    work_city: str = Form(None),
    department: str = Form(None),
    employment_type: str = Form(None),
    occupation: str = Form(None),
    position_level: str = Form(None),
    weekly_hours: float = Form(None),
    work_days_per_week: float = Form(None),
    daily_hours: float = Form(None),
    start_date: str = Form(None),
    contract_type: str = Form(None),
    end_date: str = Form(None),
    probation_period_months: int = Form(None),
    previous_employer: str = Form(None),
    education_level: str = Form(None),
    disabled: bool = Form(None),
    status: str = Form("draft"),
    ordio_id: str = Form(None),
    db: Session = Depends(get_db),
):
    data = _collect_form_data(locals(), hotel_name_select, hotel_name_custom)

    if data["email"]:
        existing = db.query(Employee).filter(Employee.email == data["email"]).first()
        if existing:
            return templates.TemplateResponse(
                request=request,
                name="upload.html",
                context={
                    "error_message": f"This email already exists for employee ID {existing.id}. "
                                     "Please open that record and edit it instead.",
                    "form_data": data,
                },
            )

    new_employee = Employee(**data)
    db.add(new_employee)
    try:
        db.commit()
        db.refresh(new_employee)
        name = f"{new_employee.first_name or ''} {new_employee.last_name or ''}".strip()
        _audit(db, "create", new_employee.id, f"Created Employee: {name}")
        db.commit()
        return RedirectResponse(url=f"/review/{new_employee.id}", status_code=303)

    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "error_message": "This email already exists. Please use a different email or edit the existing employee.",
                "form_data": data,
            },
        )


@app.get("/review/{employee_id}", response_class=HTMLResponse)
def review_employee(employee_id: int, request: Request, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)
    upload_sessions = [s for s in _discover_employee_upload_sessions(employee) if s["files"]]
    uploaded_files = [file for session in upload_sessions for file in session["files"]]

    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "employee": employee,
            "uploaded_files": uploaded_files,
            "upload_sessions": upload_sessions,
            "selected_ocr_engine": "rapidocr",
            "selected_ai_extractor": "local",
            "mistral_available": bool(MISTRAL_API_KEY),
            "approval_error": request.query_params.get("approval_error"),
            "approval_success": request.query_params.get("approval_success"),
        },
    )


@app.get("/review/{employee_id}/edit", response_class=HTMLResponse)
def edit_employee_page(employee_id: int, request: Request, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)
    return templates.TemplateResponse(
        request=request,
        name="edit_review.html",
        context={
            "employee": employee,
            "upload_sessions": _discover_employee_upload_sessions(employee),
            "selected_ocr_engine": "rapidocr",
            "selected_ai_extractor": "local",
            "mistral_available": bool(MISTRAL_API_KEY),
        },
    )


@app.post("/review/{employee_id}")
def update_employee(
    employee_id: int,
    request: Request,
    first_name: str = Form(None),
    middle_name: str = Form(None),
    last_name: str = Form(None),
    gender: str = Form(None),
    date_of_birth: str = Form(None),
    place_of_birth: str = Form(None),
    country_of_birth: str = Form(None),
    nationality: str = Form(None),
    marital_status: str = Form(None),
    ausweis_number: str = Form(None),
    ausweis_expiry_date: str = Form(None),
    reise_pass_number: str = Form(None),
    reise_pass_expiry_date: str = Form(None),
    working_permit_number: str = Form(None),
    working_permit_expiry: str = Form(None),
    visa_number: str = Form(None),
    visa_expiry: str = Form(None),
    phone: str = Form(None),
    emergency_contact_name: str = Form(None),
    emergency_contact_phone: str = Form(None),
    email: str = Form(None),
    street_and_house_number: str = Form(None),
    zip_code: str = Form(None),
    city: str = Form(None),
    country: str = Form("Deutschland"),
    krankenkasse: str = Form(None),
    krankenkasse_nummer: str = Form(None),
    steuer_id: str = Form(None),
    steuerklasse: int = Form(None),
    sozialversicherungsnummer: str = Form(None),
    bank_name: str = Form(None),
    bank_iban: str = Form(None),
    bank_bic: str = Form(None),
    bank_account_holder: str = Form(None),
    hotel_name_select: str = Form(None),
    hotel_name_custom: str = Form(None),
    work_city: str = Form(None),
    department: str = Form(None),
    employment_type: str = Form(None),
    occupation: str = Form(None),
    position_level: str = Form(None),
    weekly_hours: float = Form(None),
    work_days_per_week: float = Form(None),
    daily_hours: float = Form(None),
    start_date: str = Form(None),
    contract_type: str = Form(None),
    end_date: str = Form(None),
    probation_period_months: int = Form(None),
    previous_employer: str = Form(None),
    education_level: str = Form(None),
    disabled: bool = Form(None),
    status: str = Form("draft"),
    ordio_id: str = Form(None),
    db: Session = Depends(get_db),
):
    employee = _get_employee(db, employee_id)

    if email:
        conflict = db.query(Employee).filter(Employee.email == email, Employee.id != employee_id).first()
        if conflict:
            return templates.TemplateResponse(
                request=request,
                name="edit_review.html",
                context={
                    "employee": employee,
                    "upload_sessions": _discover_employee_upload_sessions(employee),
                    "selected_ocr_engine": "rapidocr",
                    "selected_ai_extractor": "local",
                    "mistral_available": bool(MISTRAL_API_KEY),
                    "error_message": "That email is already assigned to another employee.",
                },
            )

    incoming = _collect_form_data(locals(), hotel_name_select, hotel_name_custom)
    changed = {}

    for field, new_val in incoming.items():
        old_val = getattr(employee, field)

        # Allow explicitly clearing hotel_name to None
        if field == "hotel_name" and (new_val is None or new_val == ""):
            if old_val:
                changed[field] = {"old": old_val, "new": None}
                setattr(employee, field, None)
            continue

        if old_val != new_val:
            changed[field] = {"old": old_val, "new": new_val}
            setattr(employee, field, new_val)

    # Auto-bump status to under_review when data changes, unless status itself was changed
    if changed and "status" not in changed and employee.status != "under_review":
        changed["status"] = {"old": employee.status, "new": "under_review"}
        employee.status = "under_review"

    try:
        db.commit()
        db.refresh(employee)
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="edit_review.html",
            context={
                "employee": employee,
                "upload_sessions": _discover_employee_upload_sessions(employee),
                "selected_ocr_engine": "rapidocr",
                "selected_ai_extractor": "local",
                "mistral_available": bool(MISTRAL_API_KEY),
                "error_message": "An error occurred while saving. Please verify the email and try again.",
            },
        )

    _audit(db, "update", employee.id, changed)
    db.commit()
    return RedirectResponse(url=f"/review/{employee.id}", status_code=303)


@app.post("/delete-employee/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)
    name = f"{employee.first_name or ''} {employee.last_name or ''}".strip()
    _audit(db, "delete", employee.id, f"Deleted Employee: {name}")
    db.commit()
    db.delete(employee)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/employees", response_model=list[EmployeeResponse])
def list_employees(db: Session = Depends(get_db)):
    return db.query(Employee).all()


@app.get("/debug-template/{employee_id}")
def debug_template(employee_id: int, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)
    attrs = normalize_contract_attributes(employee)
    template_path = resolve_template_path(employee)
    if not template_path or not template_path.exists():
        return {"error": "No suitable template found for this employee"}
    return {"attrs": attrs, "template_path": str(template_path)}


@app.get("/generate-contract/{employee_id}")
def generate_contract(employee_id: int, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)
    try:
        output_path = generate_contract_for_employee(employee)
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}

    pdf_path = convert_docx_to_pdf(output_path)
    now = datetime.now(timezone.utc)

    employee.last_contract_path                      = str(output_path)
    employee.last_contract_generated_at              = now
    employee.last_contract_pdf_path                  = str(pdf_path)
    employee.last_contract_pdf_path_generated_at     = now

    _audit(db, "generate_contract", employee.id, {"contract_path": str(output_path)})
    db.commit()
    return RedirectResponse(url=f"/review/{employee_id}", status_code=303)


@app.get("/approve-employee/{employee_id}")
def approve_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)

    if employee.status == "approved":
        return RedirectResponse(url=f"/review/{employee.id}", status_code=303)

    missing = get_approval_missing_fields(employee)
    if missing:
        _audit(db, "approval_failed", employee.id, {"reason": "missing_fields", "fields": missing})
        db.commit()
        return RedirectResponse(
            url=f"/review/{employee.id}?approval_error={quote(f'Missing required fields: {', '.join(missing)}')}",
            status_code=303,
        )

    employee.status      = "approved"
    employee.approved_at = datetime.now(timezone.utc)
    employee.approved_by = "system"

    _audit(db, "approve", employee.id, {"status": "approved"})
    db.commit()
    return RedirectResponse(url=f"/review/{employee_id}?approval_success=1", status_code=303)


@app.get("/mark-under-review/{employee_id}")
def mark_under_review(employee_id: int, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)
    if employee.status == "under_review":
        return RedirectResponse(url=f"/review/{employee.id}", status_code=303)
    employee.status = "under_review"
    _audit(db, "mark_under_review", employee.id, {"status": "under_review"})
    db.commit()
    return RedirectResponse(url=f"/review/{employee.id}", status_code=303)


@app.get("/reject-employee/{employee_id}")
def reject_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)
    employee.status = "rejected"
    _audit(db, "reject", employee.id, {"status": "rejected"})
    db.commit()
    return RedirectResponse(url=f"/review/{employee.id}", status_code=303)


@app.get("/download-contract/{employee_id}")
def download_last_contract(employee_id: int, db: Session = Depends(get_db)):
    employee = _get_employee(db, employee_id)
    if not employee.last_contract_path:
        return {"error": "No contract generated for this employee yet"}
    contract_path = Path(employee.last_contract_path)
    if not contract_path.exists():
        return {"error": "Contract file not found on server"}
    return FileResponse(
        path=str(contract_path),
        filename=contract_path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/api/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs_api(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()


@app.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(request: Request, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return templates.TemplateResponse(
        request=request, name="audit-logs.html",
        context={"request": request, "logs": logs},
    )


@app.get("/download-collected/{employee_id}")
def download_collected_docs(employee_id: int, db: Session = Depends(get_db)):
    """Download the auto-generated Word document pack for an employee."""
    employee = _get_employee(db, employee_id)
    if not employee.collected_docs_docx or not Path(employee.collected_docs_docx).exists():
        raise HTTPException(status_code=404, detail="Document pack not generated yet")
    p = Path(employee.collected_docs_docx)
    return FileResponse(
        path=str(p),
        filename=p.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/employee-file/{employee_id}/{session_name}/{filename}")
def download_employee_session_file(
    employee_id: int,
    session_name: str,
    filename: str,
    db: Session = Depends(get_db),
):
    """Download an original uploaded file from a specific upload session."""
    employee = _get_employee(db, employee_id)
    file_path = _resolve_employee_file(employee, session_name, filename)
    return FileResponse(path=str(file_path), filename=filename)


@app.get("/employee-file/{employee_id}/{filename}")
def download_employee_file(employee_id: int, filename: str, db: Session = Depends(get_db)):
    """Download an original uploaded file for a specific employee."""
    employee = _get_employee(db, employee_id)
    for session in _discover_employee_upload_sessions(employee):
        originals_dir = (session["path"] / "originals").resolve()
        file_path = (originals_dir / filename).resolve()
        if originals_dir in file_path.parents and file_path.exists() and file_path.is_file():
            return FileResponse(path=str(file_path), filename=filename)
    if not employee.upload_session_dir:
        raise HTTPException(status_code=404, detail="No upload folder for this employee")
    # Resolve strictly inside originals/ — prevents path traversal
    originals_dir = Path(employee.upload_session_dir) / "originals"
    file_path     = (originals_dir / filename).resolve()
    if not str(file_path).startswith(str(originals_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename)


@app.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    """Show upload performance log and recent server errors."""
    base = Path(__file__).resolve().parent

    # Upload CSV log (date, files count, elapsed minutes)
    upload_rows: List[dict] = []
    csv_path = base / "logs" / "upload_logs.csv"
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            upload_rows = list(reader)
        upload_rows.reverse()  # newest first

    # Last 100 lines of the server error log
    error_lines: List[str] = []
    err_log = base / "logs" / "dev_server.err.log"
    if err_log.exists():
        try:
            error_lines = err_log.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]
        except OSError:
            error_lines = ["(could not read log file)"]

    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={"upload_rows": upload_rows, "error_lines": error_lines},
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "App is running"}
