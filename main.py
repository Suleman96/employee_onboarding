# FastAPI Application for Employee Management
#started by building the web application skeleton first, so I had a stable runtime, routing layer, 
#     and template rendering before adding any business logic.
# I designed the system around partial employee records because onboarding data often arrives in 
# stages, and the database model supports incomplete records that can be enriched later.
# I expanded the employee schema incrementally based on downstream dependencies, 
# especially contract variables and Ordio field mapping


from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import create_tables, get_db, Employee, AuditLog
from contracts.generator import generate_contract_for_employee

from typing import List
from schemas import EmployeeCreate, EmployeeUpdate, EmployeeResponse, AuditLogResponse
import json

# Initialize FastAPI app with lifespan for startup tasks
@asynccontextmanager # This allows us to run code on startup (like creating tables) and optionally on shutdown
async def lifespan(app: FastAPI):
    # Startup code: create database tables
    create_tables()
    print("Database tables created or already exist.")
    yield
    # Shutdown code (if needed) can go here
    
# ── Create the FastAPI application ──────────────────────────────

app = FastAPI(lifespan=lifespan, # This tells FastAPI to use the lifespan function for startup/shutdown events 
              title="Employee Onboarding System", 
              version="0.1.0")

templates = Jinja2Templates(directory = "templates")



# Home route 
# This route serves the home page of the application. 
# It uses Jinja2 templates to render an HTML page located in the "templates" directory. 
# When a user accesses the root URL ("/"), this function is called, and it returns the rendered "index.html" 
# template along with the request context.

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db:Session=Depends(get_db)):
    employees = db.query(Employee).order_by(Employee.created_at.desc()).all()
    
    return templates.TemplateResponse(
        "index.html", {
            "request": request,
            "employees": employees 
            }
        )


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "App is running"}

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/employees/new")
def create_employee(
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
    db.commit()
    db.refresh(new_employee)
    
    audit_entry=AuditLog(
        action="create",
        employee_id= new_employee.id,
        details=f"Created Employee: {new_employee.first_name or ''} {new_employee.last_name or ''}",
        performed_by="system"
    )
    db.add(audit_entry)
    db.commit()
    
    return RedirectResponse(url=f"/review/{new_employee.id}", status_code=303)


@app.get("/review/{employee_id}", response_class=HTMLResponse)
def review_employee(employee_id:int, request: Request, db:Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return HTMLResponse(content="<h1>Employee not found</h1>", status_code=404)
    
    return templates.TemplateResponse(
        "review.html",# This is the name of the template file in the templates/ directory
            {
            "request": request,
            "employee": employee
            }
            
    )

@app.get("/review/{employee_id}/edit", response_class=HTMLResponse)
def edit_employee_page(employee_id:int, request: Request, db:Session= Depends(get_db)):
    employee=db.query(Employee).filter(Employee.id ==employee_id).first()
    if not employee:
        return HTMLResponse(context= "<h1>Employee not found</h1>", status_code=404)
    
    return templates.TemplateResponse(
        "edit_review.html",
        {
            "request": request,
            "employee": employee
        }
    )
@app.post("/review/{employee_id}")
def update_employee(
    employee_id:int,
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
        
        # Do not overwrite existing data with empty strings or None
        if new_value is None or new_value == "":
            continue
        
        if old_value != new_value:
            changed_fields[field_name] = {
                "old": old_value,
                "new": new_value
            }
            setattr(employee, field_name, new_value) #This writes the new value into the employee object dynamically.
            
            
    # This is the old way of updating each field manually, which is more verbose and error-prone.
    # # Update the employee's information
    # employee.first_name = first_name
    # employee.last_name = last_name
    # employee.gender = gender
    # employee.date_of_birth = date_of_birth
    # employee.place_of_birth = place_of_birth
    # employee.country_of_birth = country_of_birth
    # employee.nationality = nationality
    # employee.street_and_house_number = street_and_house_number
    # employee.phone = phone
    # employee.zip_code = zip_code
    # employee.city = city
    # employee.email = email
    # employee.country = country
    # employee.steuer_id = steuer_id
    # employee.steuerklasse = steuerklasse
    # employee.iban = iban
    # employee.start_date = start_date
    # employee.contract_type = contract_type
    # employee.end_date = end_date
    # employee.disabled = disabled
    # employee.status = status
    # employee.ordio_id = ordio_id

    db.commit()
    db.refresh(employee)
    
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
    

@app.get("/employees", response_model= list[EmployeeResponse])
def list_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    return employees




@app.get("/generate-contract/{employee_id}")
def generate_contract(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return {"error": "Employee not found"}
    
    output_path = generate_contract_for_employee(employee)
    audit_entry = AuditLog(
        action = "generate_contract",
        employee_id = employee.id,
        details = json.dumps({"contract_path": str(output_path)}),
        performed_by="system"
    )
    db.add(audit_entry)
    db.commit()
    
    return FileResponse(
        path=str(output_path),
        filename=output_path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.get("/audit-logs", response_model= List[AuditLogResponse])
def list_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    return logs


