# His is how data is validated ad passed around

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


#This is for incoming data when a user submits a new employee.
#Optional[str] = None This means the field can be empty.


class EmployeeBase(BaseModel):
    # Personal Information
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    country_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None

    # Identification Documents
    ausweis_number: Optional[str] = None
    ausweis_expiry_date: Optional[str] = None
    reise_pass_number: Optional[str] = None
    reise_pass_expiry_date: Optional[str] = None
    working_permit_number: Optional[str] = None
    working_permit_expiry: Optional[str] = None
    visa_number: Optional[str] = None
    visa_expiry: Optional[str] = None

    # Contact Information
    street_and_house_number: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    email: Optional[EmailStr] = None
    country: Optional[str] = None

    # Insurance and Tax Information
    krankenkasse: Optional[str] = None
    krankenkasse_nummer: Optional[str] = None
    steuer_id: Optional[str] = None
    steuerklasse: Optional[int] = None
    sozialversicherungsnummer: Optional[str] = None

    # Banking Information
    bank_name: Optional[str] = None
    bank_iban: Optional[str] = None
    bank_bic: Optional[str] = None
    bank_account_holder: Optional[str] = None

    # Employment Information
    work_city: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None
    occupation: Optional[str] = None
    position_level: Optional[str] = None
    weekly_hours: Optional[float] = None
    work_days_per_week: Optional[float] = None
    daily_hours: Optional[float] = None
    start_date: Optional[str] = None
    contract_type: Optional[str] = "temporary"
    end_date: Optional[str] = None
    probation_period_months: Optional[int] = None
    previous_employer: Optional[str] = None
    education_level: Optional[str] = None

    # Health and Accessibility
    disabled: Optional[bool] = None

    # System Fields
    status: Optional[str] = "draft"
    ordio_id: Optional[str] = None
    
    
    
class EmployeeCreate(EmployeeBase):
    pass
class EmployeeUpdate(EmployeeBase):
    pass    
    
#This is for sending employee data back out safely without exposing sensitive information.
class EmployeeResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime 
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    is_deleted: bool = False
    deleted_reason: Optional[str] = None
    # this is for converting the SQLAlchemy model to a Pydantic model. 
    # It allows us to return SQLAlchemy objects directly from our API endpoints 
    # and have them automatically converted to the appropriate Pydantic response model.
    model_config= ConfigDict(from_attributes=True)
    
class AuditLogResponse(BaseModel):
    id: int
    action: str
    employee_id: int
    details: str
    performed_by: str
    timestamp: datetime
    
    model_config= ConfigDict(from_attributes=True)
    
    