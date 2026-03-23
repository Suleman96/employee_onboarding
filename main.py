# FastAPI Application for Employee Management
#started by building the web application skeleton first, so I had a stable runtime, routing layer, 
#     and template rendering before adding any business logic.
# I designed the system around partial employee records because onboarding data often arrives in 
# stages, and the database model supports incomplete records that can be enriched later.
# I expanded the employee schema incrementally based on downstream dependencies, 
# especially contract variables and Ordio field mapping


from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import create_tables, get_db, Employee, AuditLog

import json

# Initialize FastAPI app with lifespan for startup tasks
@asynccontextmanager # This allows us to run code on startup (like creating tables) and optionally on shutdown
async def lifespan(app: FastAPI):
    # Startup code: create database tables
    create_tables()
    print("Database tables created or already exist.")
    yield
    # Shutdown code (if needed) can go here
    
# Create the FastAPI app object
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
    last_name: str = Form(None),
    gender: str = Form(None),
    date_of_birth: str = Form(None),
    place_of_birth: str = Form(None),
    country_of_birth: str = Form(None),
    nationality: str = Form(None),
    street_and_house_number: str = Form(None),
    phone: str = Form(None),
    zip_code: str = Form(None),
    city: str = Form(None),
    email: str = Form(None),
    country: str = Form("Deutschland"),
    steuer_id: str = Form(None),
    steuerklasse: int = Form(None),
    iban: str = Form(None),
    start_date: str = Form(None),
    contract_type: str = Form(None),
    end_date: str = Form(None),
    disabled: str = Form(None),
    status: str = Form("draft"),
    ordio_id: str = Form(None),
    db: Session = Depends(get_db)
):    
    new_employee = Employee(
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=date_of_birth,
        place_of_birth=place_of_birth,
        country_of_birth=country_of_birth,
        nationality=nationality,
        street_and_house_number=street_and_house_number,
        phone=phone,
        zip_code=zip_code,
        city=city,
        email=email,
        country=country,
        steuer_id=steuer_id,
        steuerklasse=steuerklasse,
        iban=iban,
        start_date=start_date,
        contract_type=contract_type,
        end_date=end_date,
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
    last_name: str = Form(None),
    gender: str = Form(None),
    date_of_birth: str = Form(None),
    place_of_birth: str = Form(None),
    country_of_birth: str = Form(None),
    nationality: str = Form(None),
    street_and_house_number: str = Form(None),
    phone: str = Form(None),
    zip_code: str = Form(None),
    city: str = Form(None),
    email: str = Form(None),
    country: str = Form("Deutschland"),
    steuer_id: str = Form(None),
    steuerklasse: int = Form(None),
    iban: str = Form(None),
    start_date: str = Form(None),
    contract_type: str = Form(None),
    end_date: str = Form(None),
    disabled: str = Form(None),
    status: str = Form("draft"),
    ordio_id: str = Form(None),
    db: Session = Depends(get_db)
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return HTMLResponse(content="<h1>Employee not found</h1>", status_code=404)

    # Update the employee's information
    employee.first_name = first_name
    employee.last_name = last_name
    employee.gender = gender
    employee.date_of_birth = date_of_birth
    employee.place_of_birth = place_of_birth
    employee.country_of_birth = country_of_birth
    employee.nationality = nationality
    employee.street_and_house_number = street_and_house_number
    employee.phone = phone
    employee.zip_code = zip_code
    employee.city = city
    employee.email = email
    employee.country = country
    employee.steuer_id = steuer_id
    employee.steuerklasse = steuerklasse
    employee.iban = iban
    employee.start_date = start_date
    employee.contract_type = contract_type
    employee.end_date = end_date
    employee.disabled = disabled
    employee.status = status
    employee.ordio_id = ordio_id

    db.commit()
    db.refresh(employee)
    
    audit_entry =AuditLog(
        action="update",
        employee_id=employee.id,
        details= f"Updated Employee: {employee.first_name or ''} {employee.last_name or ''}",
        performed_by="system"
    )
    db.add(audit_entry)
    db.commit()
    return RedirectResponse(url=f"/review/{employee.id}", status_code=303)
    

@app.get("/employees")
def list_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()

    results = []
    for emp in employees:
        results.append({
            "id": emp.id,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "email": emp.email,
            "status": emp.status
        })

    return results


@app.get("/audit-logs")
def list_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()

    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "action": log.action,
            "employee_id": log.employee_id,
            "details": log.details,
            "performed_by": log.performed_by,
            "timestamp": log.timestamp
        })

    return results