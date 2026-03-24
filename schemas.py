# His is how data is validated ad passed around

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


#This is for incoming data when a user submits a new employee.
#Optional[str] = None This means the field can be empty.


class EmployeeBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    
    date_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    country_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    
    street_and_house_number: Optional[str] = None
    phone: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    email: Optional[EmailStr] = None
    country: Optional[str] = None
    
    ausweis_number: Optional[str] = None
    reise_pass_number: Optional[str] = None
    krankenkasse: Optional[str] = None
    krankenkasse_nummer: Optional[str] = None
    steuer_id: Optional[str] = None
    steuerklasse: Optional[int] = None
    sozialversicherungsnummer: Optional[str] = None
    bank_name: Optional[str] = None
    bank_iban: Optional[str] = None
    bank_bic: Optional[str] = None
    bank_account_holder: Optional[str] = None
    
    start_date: Optional[str] = None
    contract_type: Optional[str] = None
    end_date: Optional[str] = None
    disabled: Optional[str] = None

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
    
    