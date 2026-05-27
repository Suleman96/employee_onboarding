# FastAPI Application for Employee Management
#started by building the web application skeleton first, so I had a stable runtime, routing layer, 
#     and template rendering before adding any business logic.
# I designed the system around partial employee records because onboarding data often arrives in 
# stages, and the database model supports incomplete records that can be enriched later.
# I expanded the employee schema incrementally based on downstream dependencies, 
# especially contract variables and Ordio field mapping

import http
import subprocess
import webbrowser

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Depends, Form, HTTPException, UploadFile, File
from urllib.parse import quote
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import create_tables, get_db, Employee, AuditLog
from contracts.generator import convert_docx_to_pdf, generate_contract_for_employee
from contracts.resolver import normalize_contract_attributes, resolve_template_path
from pipeline import process_uploaded_files
from config import OCR_ENGINE

from pathlib import Path
from typing import List
from schemas import EmployeeCreate, EmployeeUpdate, EmployeeResponse, AuditLogResponse
import json
import time

# Initialize FastAPI app with lifespan for startup tasks
@asynccontextmanager # This allows us to run code on startup (like creating tables) and optionally on shutdown
async def lifespan(app: FastAPI):
    # Startup code: create database tables
    create_tables()
    print("Database tables created or already exist.")
    
    # Start n8n in the background
    n8n_process = subprocess.Popen("n8n", shell=True)
    print("n8n started on http://localhost:5678")
    webbrowser.open("http://localhost:8000")   # opens your app automatically

    yield
     # Stop n8n when the app shuts down
    n8n_process.terminate()
    print("n8n process terminated.")


# ── Create the FastAPI application ──────────────────────────────

app = FastAPI(lifespan=lifespan, # This tells FastAPI to use the lifespan function for startup/shutdown events 
              title="Employee Onboarding System", 
              version="0.1.0")

templates = Jinja2Templates(directory = "templates")


def normalize_hotel_name(hotel_name_select: str | None, hotel_name_custom: str | None) -> str | None:
    if hotel_name_select == "other":
        custom_value = (hotel_name_custom or "").strip()
        return custom_value or None
    if hotel_name_select in (None, "", "none"):
        return None
    return hotel_name_select



# This helper checks whether the employee is missing important fields.
def get_approval_missing_fields(employee) -> List[str]:
    
    missing = []
    if not employee.first_name:
        missing.append("first_name")
    if not employee.last_name:
        missing.append("last_name")
    if not employee.date_of_birth:
        missing.append("date_of_birth")
    # if not employee.place_of_birth:
    #     missing.append("place_of_birth")
    if not employee.street_and_house_number:
        missing.append("street_and_house_number")
    if not employee.city:
        missing.append("city")
    # if not employee.steuer_id:
    #     missing.append("steuer_id")
    # if not employee.bank_iban:
    #     missing.append("bank_iban")
    if not employee.start_date:
        missing.append("start_date")

    return missing

# Home route 
# This route serves the home page of the application. 
# It uses Jinja2 templates to render an HTML page located in the "templates" directory. 
# When a user accesses the root URL ("/"), this function is called, and it returns the rendered "index.html" 
# template along with the request context.

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db:Session=Depends(get_db)):
    employees = db.query(Employee).order_by(Employee.created_at.desc()).all()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"employees": employees}
        )



@app.post("/api/employees/n8n-intake")
def create_employee_from_n8n(payload: EmployeeCreate, db: Session = Depends(get_db)):
    try:
        
        new_employee = Employee(
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            gender=payload.gender,
            date_of_birth=payload.date_of_birth,
            place_of_birth=payload.place_of_birth,
            country_of_birth=payload.country_of_birth,
            nationality=payload.nationality,
            marital_status=payload.marital_status,

            ausweis_number=payload.ausweis_number,
            ausweis_expiry_date=payload.ausweis_expiry_date,
            reise_pass_number=payload.reise_pass_number,
            reise_pass_expiry_date=payload.reise_pass_expiry_date,
            working_permit_number=payload.working_permit_number,
            working_permit_expiry=payload.working_permit_expiry,
            visa_number=payload.visa_number,
            visa_expiry=payload.visa_expiry,

            street_and_house_number=payload.street_and_house_number,
            phone=payload.phone,
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_phone=payload.emergency_contact_phone,
            zip_code=payload.zip_code,
            city=payload.city,
            email=payload.email,
            country=payload.country or "Deutschland",

            krankenkasse=payload.krankenkasse,
            krankenkasse_nummer=payload.krankenkasse_nummer,
            steuer_id=payload.steuer_id,
            steuerklasse=payload.steuerklasse,
            sozialversicherungsnummer=payload.sozialversicherungsnummer,

            bank_name=payload.bank_name,
            bank_iban=payload.bank_iban,
            bank_bic=payload.bank_bic,
            bank_account_holder=payload.bank_account_holder,

            work_city=payload.work_city,
            department=payload.department,
            employment_type=payload.employment_type,
            occupation=payload.occupation,
            position_level=payload.position_level,
            weekly_hours=payload.weekly_hours,
            work_days_per_week=payload.work_days_per_week,
            daily_hours=payload.daily_hours,
            start_date=payload.start_date,
            contract_type=payload.contract_type or "temporary",
            hotel_name=payload.hotel_name,
            end_date=payload.end_date,
            probation_period_months=payload.probation_period_months,
            previous_employer=payload.previous_employer,
            education_level=payload.education_level,

            disabled=payload.disabled if payload.disabled is not None else False,
            status=payload.status or "draft",
            ordio_id=payload.ordio_id,

            last_contract_path=payload.last_contract_path,
            last_contract_generated_at=payload.last_contract_generated_at,
            last_contract_pdf_path=payload.last_contract_pdf_path,
            last_contract_pdf_path_generated_at=payload.last_contract_pdf_path_generated_at,
        )
        
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        
        audit_entry= AuditLog(
            action = "create_from_n8n",
            employee_id= new_employee.id,
            details= f"Created from n8n: {new_employee.first_name or ''} {new_employee.last_name or ''}".strip(),
            performed_by= "n8n"
        )
        db.add(audit_entry)
        db.commit()
        
        return{
            "success": True,
            "employee_id": new_employee.id,
            "message": "Employee saved successfully"
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
        
@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={"form_data": {}, "selected_ocr_engine": OCR_ENGINE}
    )

@app.post("/upload/documents")
def upload_documents(
    request: Request,
    files: list[UploadFile] = File(default=[]),
    text_input: str = Form(default=""),
    employee_id: int | None = Form(default=None),
    ocr_engine: str = Form(default=OCR_ENGINE),
    db: Session = Depends(get_db),
):
    start_time = time.perf_counter()
    try:
        result = process_uploaded_files(
            db=db,
            files=files,
            text_input=text_input,
            employee_id=employee_id,
            ocr_engine_name=ocr_engine,
        )
        
        elapsed_seconds = time.perf_counter() - start_time
        elapsed_minutes = elapsed_seconds / 60
        print(f"Extraction completed in {elapsed_seconds:.2f} seconds ({elapsed_minutes:.2f} minutes)")     
                
        # Log to file
        log_file = "logs/upload_logs.csv"
        if not Path(log_file).exists():
            with open(log_file, "w") as f:
                f.write("Date,Files,Time\n")
        with open(log_file, "a") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{len(files)},{elapsed_minutes:.2f}\n")

        employee_id = result["employee_id"]
        return RedirectResponse(url=f"/review/{employee_id}", status_code=303)

    except Exception as e:
        import traceback
        print("=== UPLOAD PIPELINE ERROR START ===")
        traceback.print_exc()
        print("=== UPLOAD PIPELINE ERROR END ===")

        return templates.TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "form_data": {},
                "selected_ocr_engine": ocr_engine,
                "error_message": f"Upload processing failed: {str(e)}",
                "error": f"Upload processing failed: {str(e)}",
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
    db: Session = Depends(get_db)
):
    
    form_data = {
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "gender": gender,
        "date_of_birth": date_of_birth,
        "place_of_birth": place_of_birth,
        "country_of_birth": country_of_birth,
        "nationality": nationality,
        "marital_status": marital_status,

        "ausweis_number": ausweis_number,
        "ausweis_expiry_date": ausweis_expiry_date,
        "reise_pass_number": reise_pass_number,
        "reise_pass_expiry_date": reise_pass_expiry_date,
        "working_permit_number": working_permit_number,
        "working_permit_expiry": working_permit_expiry,
        "visa_number": visa_number,
        "visa_expiry": visa_expiry,

        "street_and_house_number": street_and_house_number,
        "phone": phone,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_phone": emergency_contact_phone,
        "zip_code": zip_code,
        "city": city,
        "email": email,
        "country": country,

        "krankenkasse": krankenkasse,
        "krankenkasse_nummer": krankenkasse_nummer,
        "steuer_id": steuer_id,
        "steuerklasse": steuerklasse,
        "sozialversicherungsnummer": sozialversicherungsnummer,

        "bank_name": bank_name,
        "bank_iban": bank_iban,
        "bank_bic": bank_bic,
        "bank_account_holder": bank_account_holder,

        "hotel_name_select": hotel_name_select,
        "hotel_name_custom": hotel_name_custom,
        "work_city": work_city,
        "department": department,
        "employment_type": employment_type,
        "occupation": occupation,
        "position_level": position_level,
        "weekly_hours": weekly_hours,
        "work_days_per_week": work_days_per_week,
        "daily_hours": daily_hours,
        "start_date": start_date,
        "contract_type": contract_type,
        "end_date": end_date,
        "probation_period_months": probation_period_months,
        "previous_employer": previous_employer,
        "education_level": education_level,

        "disabled": disabled,
        "status": status,
        "ordio_id": ordio_id,
    }
    
    email = email.strip().lower() if email else ""
    form_data["email"] = email

    existing_employee = None

    if email:
        existing_employee = db.query(Employee).filter(Employee.email == email).first()

    if existing_employee:
        return templates.TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "error_message": f"This email already exists for employee ID {existing_employee.id}. Please open that record and edit it instead.",
                "form_data": form_data,
            },
            status_code=200,
        )
    new_employee = Employee(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=date_of_birth,
        place_of_birth=place_of_birth,
        country_of_birth=country_of_birth,
        nationality=nationality,
        marital_status=marital_status,

        ausweis_number=ausweis_number,
        ausweis_expiry_date=ausweis_expiry_date,
        reise_pass_number=reise_pass_number,
        reise_pass_expiry_date=reise_pass_expiry_date,
        working_permit_number=working_permit_number,
        working_permit_expiry=working_permit_expiry,
        visa_number=visa_number,
        visa_expiry=visa_expiry,

        street_and_house_number=street_and_house_number,
        phone=phone,
        emergency_contact_name=emergency_contact_name,
        emergency_contact_phone=emergency_contact_phone,
        zip_code=zip_code,
        city=city,
        email=email,
        country=country,

        krankenkasse=krankenkasse,
        krankenkasse_nummer=krankenkasse_nummer,
        steuer_id=steuer_id,
        steuerklasse=steuerklasse,
        sozialversicherungsnummer=sozialversicherungsnummer,

        bank_name=bank_name,
        bank_iban=bank_iban,
        bank_bic=bank_bic,
        bank_account_holder=bank_account_holder,

        work_city=work_city,
        department=department,
        employment_type=employment_type,
        occupation=occupation,
        position_level=position_level,
        hotel_name=normalize_hotel_name(hotel_name_select, hotel_name_custom),
        weekly_hours=weekly_hours,
        work_days_per_week=work_days_per_week,
        daily_hours=daily_hours,
        start_date=start_date,
        contract_type=contract_type,
        end_date=end_date,
        probation_period_months=probation_period_months,
        previous_employer=previous_employer,
        education_level=education_level,

        disabled=disabled,
        status=status,
        ordio_id=ordio_id,
    )

    db.add(new_employee)
    try:
        db.commit()
        db.refresh(new_employee)

        audit_entry = AuditLog(
            action="create",
            employee_id=new_employee.id,
            details=f"Created Employee: {new_employee.first_name or ''} {new_employee.last_name or ''}".strip(),
            performed_by="system"
        )
        db.add(audit_entry)
        db.commit()

        return RedirectResponse(url=f"/review/{new_employee.id}", status_code=303)

    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="upload.html",
            context={
                "error_message": "This email already exists. Please use a different email or edit the existing employee.",
                "form_data": form_data,
            },
            status_code=200,
        )
        
@app.get("/review/{employee_id}", response_class=HTMLResponse)
def review_employee(employee_id:int, request: Request, db:Session = Depends(get_db)):
    
    
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return HTMLResponse(content="<h1>Employee not found</h1>", status_code=404)
    
    approval_error = request.query_params.get("approval_error")
    approval_success = request.query_params.get("approval_success")
    
    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "employee": employee,
            "approval_error": approval_error,
            "approval_success": approval_success,
        }
    )

@app.get("/review/{employee_id}/edit", response_class=HTMLResponse)
def edit_employee_page(employee_id:int, request: Request, db:Session= Depends(get_db)):
    employee=db.query(Employee).filter(Employee.id ==employee_id).first()
    if not employee:
        return HTMLResponse(content="<h1>Employee not found</h1>", status_code=404)
    
    return templates.TemplateResponse(
        request=request,
        name="edit_review.html",
        context={"employee": employee}
    )
@app.post("/review/{employee_id}")
def update_employee(
    employee_id:int,
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
    sozialversicherungsnummer : str = Form(None),

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
    

    db: Session = Depends(get_db)
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return HTMLResponse(content="<h1>Employee not found</h1>", status_code=404)

    if email:
        email_conflict = db.query(Employee).filter(Employee.email == email, Employee.id != employee_id).first()
        if email_conflict:
            return templates.TemplateResponse(
                request=request,
                name="edit_review.html",
                context={
                    "employee": employee,
                    "error_message": "That email address is already assigned to another employee. Please use a unique email.",
                },
            )

    incoming_data = {
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "gender": gender,
        "date_of_birth": date_of_birth,
        "place_of_birth": place_of_birth,
        "country_of_birth": country_of_birth,
        "nationality": nationality,
        "marital_status": marital_status,
        
        "ausweis_number": ausweis_number,
        "ausweis_expiry_date": ausweis_expiry_date,
        "reise_pass_number": reise_pass_number,
        "reise_pass_expiry_date": reise_pass_expiry_date,
        "working_permit_number": working_permit_number,
        "working_permit_expiry": working_permit_expiry,
        "visa_number": visa_number,
        "visa_expiry": visa_expiry,
        
        "phone": phone,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_phone": emergency_contact_phone,
        "email": email,
        "street_and_house_number": street_and_house_number,
        "zip_code": zip_code,
        "city": city,
        "country": country,
        
        "krankenkasse": krankenkasse,
        "krankenkasse_nummer": krankenkasse_nummer,
        "steuer_id": steuer_id,
        "steuerklasse": steuerklasse,
        "sozialversicherungsnummer": sozialversicherungsnummer,
        
        "bank_name": bank_name,
        "bank_iban": bank_iban,
        "bank_bic": bank_bic,
        "bank_account_holder": bank_account_holder,
        
        "work_city": work_city,
        "department": department,
        "employment_type": employment_type,
        "occupation": occupation,
        "position_level": position_level,
        "hotel_name": normalize_hotel_name(hotel_name_select, hotel_name_custom),
        "weekly_hours": weekly_hours,
        "work_days_per_week": work_days_per_week,
        "daily_hours": daily_hours,
        "start_date": start_date,
        "contract_type": contract_type,
        "end_date": end_date,
        "probation_period_months": probation_period_months,
        "previous_employer": previous_employer,
        "education_level": education_level,
        
        "disabled": disabled,
        "status": status,
        "ordio_id": ordio_id,
    }
    
    changed_fields = {}
    
    #This loops through every submitted field. 
    # It compares the new value with the existing value in the database. 
    # If they differ, it records the change in the changed_fields dictionary.
    for field_name, new_value in incoming_data.items():
        #This reads the current value from the employee object and stores it in old_value for comparison.
        
        old_value = getattr(employee, field_name)
        
        # Allow clearing hotel_name when explicit empty value is provided
        if field_name == "hotel_name" and (new_value is None or new_value == ""):
            if old_value is not None and old_value != "":
                changed_fields[field_name] = {
                    "old": old_value,
                    "new": None
                }
                setattr(employee, field_name, None)
            continue

        # Do not overwrite existing data with empty strings or None for all other fields
        #if new_value is None or new_value == "":
        #    continue

        if old_value != new_value:
            changed_fields[field_name] = {
                "old": old_value,
                "new": new_value
            }
            setattr(employee, field_name, new_value) #This writes the new value into the employee object dynamically.
            
    if changed_fields and "status" not in changed_fields and employee.status != "under_review":
        old_status = employee.status
        employee.status = "under_review"
        changed_fields["status"] = {"old": old_status, "new": "under_review"}

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
                "error_message": "An error occurred while saving the employee. Please verify the email and try again.",
            },
        )
    
    audit_entry =AuditLog(
        action="update",
        employee_id=employee.id,
        # details= f"Updated Employee: {employee.first_name or ''} {employee.last_name or ''}",
        details = json.dumps(changed_fields, ensure_ascii=False),
        performed_by="system"
    )
    db.add(audit_entry)
    db.commit()
    return RedirectResponse(url=f"/review/{employee.id}", status_code=303)
    

@app.post("/delete-employee/{employee_id}")
def delete_employee(employee_id: int, db:Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return HTMLResponse(content= "<h1>Employee not found </h1>", status_code= 404)
    
    employee_name = f"{employee.first_name or ''} {employee.last_name or ''}".strip()
    
    audit_entry = AuditLog(
        action = "delete",
        employee_id = employee.id,
        details= f"Deleted Employee: {employee_name}",
        performed_by ="system"
    )    
    
    db.add(audit_entry)
    db.commit()
    db.delete(employee)
    db.commit()

    return RedirectResponse(url="/", status_code=303)
    


@app.get("/employees", response_model= list[EmployeeResponse])
def list_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    return employees

@app.get("/debug-template/{employee_id}")
def debug_template(employee_id:int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    
    if not employee:
        return{"error": "Employee not found"}
    
    attrs = normalize_contract_attributes(employee)
    template_path= resolve_template_path(employee)
    
    if not template_path or not template_path.exists():
        return {"error": "No suitable template found for this employee"}
    return {
        "attrs": attrs,
        "template_path": str(template_path),
    }


@app.get("/generate-contract/{employee_id}")
def generate_contract(employee_id: int, db: Session = Depends(get_db)):
    
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return {"error": "Employee not found"}
    
    # Step 1: Generate the DOCX contract
    try:
        output_path = generate_contract_for_employee(employee)
        
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}
    
    # Step:  Convert DOCX to PDF
    pdf_path = convert_docx_to_pdf(output_path)
    
    
    # Step 3: Save contract path and generation time to employee record
    employee.last_contract_path = str(output_path)  
    employee.last_contract_generated_at = datetime.now(timezone.utc) 
     
    # Step 4: Save contract path and generation time to employee record
    employee.last_contract_pdf_path = str(pdf_path)  
    employee.last_contract_pdf_path_generated_at= datetime.now(timezone.utc)  
    
    
    # Step 5: Audit Log
    audit_entry = AuditLog(
        action = "generate_contract",
        employee_id = employee.id,
        details = json.dumps({"contract_path": str(output_path)}),
        performed_by="system"
    )
    db.add(audit_entry)
    db.commit()
    
    #     return FileResponse(
    #     path=str(output_path),
    #     filename=output_path.name,
    #     media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    # )
    
    return RedirectResponse(url=f"/review/{employee_id}", status_code=303)

@app.get("/approve-employee/{employee_id}")
def approve_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return {"error": "Employee not found"}
    
    if employee.status == "approved":
        return RedirectResponse(url=f"/review/{employee.id}", status_code=303)
    
    missing_fields = get_approval_missing_fields(employee)
    
    if missing_fields:
        audit_entry = AuditLog(
            action="approval_failed",
            employee_id=employee.id,
            details=json.dumps({"reason": "missing_fields", "fields": missing_fields}),
            performed_by="system"
        )
        db.add(audit_entry)
        db.commit()
        missing_text = ", ".join(missing_fields)
        return RedirectResponse(
            url=f"/review/{employee.id}?approval_error={quote(f'Missing required fields: {missing_text}')}",
            status_code=303,
        )

    employee.status = "approved"
    employee.approved_at = datetime.now(timezone.utc)
    employee.approved_by = "system"

    audit_entry = AuditLog(
        action="approve",
        employee_id=employee.id,
        details=json.dumps({"status": "approved"}),
        performed_by="system"
    )
    db.add(audit_entry)
    db.commit()

    return RedirectResponse(url=f"/review/{employee_id}?approval_success=1", status_code=303)

@app.get("/mark-under-review/{employee_id}")
def mark_under_review(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()

    if not employee:
        return {"error": "Employee not found"}
    
    if employee.status == "under_review":
        return RedirectResponse(url=f"/review/{employee.id}", status_code=303)

    employee.status = "under_review"

    audit_entry = AuditLog(
        action="mark_under_review",
        employee_id=employee.id,
        details=json.dumps({"status": "under_review"}),
        performed_by="system"
    )

    db.add(audit_entry)
    db.commit()
    db.refresh(employee)

    return RedirectResponse(url=f"/review/{employee.id}", status_code=303)

@app.get("/reject-employee/{employee_id}")
def reject_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()

    if not employee:
        return {"error": "Employee not found"}

    employee.status = "rejected"

    audit_entry = AuditLog(
        action="reject",
        employee_id=employee.id,
        details=json.dumps({"status": "rejected"}),
        performed_by="system"
    )

    db.add(audit_entry)
    db.commit()
    db.refresh(employee)

    return RedirectResponse(url=f"/review/{employee.id}", status_code=303)

@app.get("/download-contract/{employee_id}")
def download_last_contract(employee_id: int, db: Session = Depends(get_db)):
    
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    
    if not employee:
        return {"error": "Employee not found"}
    
    if not employee.last_contract_path:
        return {"error": "No contract generated for this employee yet"}
    
    contract_path = Path(employee.last_contract_path)
    
    if not contract_path.exists():
        return {"error": "Contract file not found on server"}
    
    return FileResponse(
        path=str(contract_path),
        filename=contract_path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )



@app.get("/api/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs_api(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return logs


@app.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(request: Request, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="audit-logs.html",
        context={"request": request, "logs": logs},
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "App is running"}
