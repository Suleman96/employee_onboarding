# His is how data is validated ad passed around

from pydantic import BaseModel, EmailStr
from typing import Optional

#This is for incoming data when a user submits a new employee.
#Optional[str] = None This means the field can be empty.


class EmployeeCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    street_and_number: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Deutschland"
    
#This is for sending employee data back out safely without exposing sensitive information.
class EmployeeResponse(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    place_of_birth: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    street_and_number: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    status: str
    
    class Config:
        from_attribute = True
        
