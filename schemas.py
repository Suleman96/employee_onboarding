from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class EmployeeBase(BaseModel):
    # Personal
    first_name:       Optional[str] = None
    middle_name:      Optional[str] = None
    last_name:        Optional[str] = None
    gender:           Optional[str] = None
    date_of_birth:    Optional[str] = None
    place_of_birth:   Optional[str] = None
    country_of_birth: Optional[str] = None
    nationality:      Optional[str] = None
    marital_status:   Optional[str] = None

    # Identity documents
    ausweis_number:         Optional[str] = None
    ausweis_expiry_date:    Optional[str] = None
    reise_pass_number:      Optional[str] = None
    reise_pass_expiry_date: Optional[str] = None
    working_permit_number:  Optional[str] = None
    working_permit_expiry:  Optional[str] = None
    visa_number:            Optional[str] = None
    visa_expiry:            Optional[str] = None

    # Contact
    street_and_house_number: Optional[str] = None
    phone:                   Optional[str] = None
    emergency_contact_name:  Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    zip_code: Optional[str]      = None
    city:     Optional[str]      = None
    email:    Optional[EmailStr] = None
    country:  Optional[str]      = None

    # Insurance & tax
    krankenkasse:             Optional[str] = None
    krankenkasse_nummer:      Optional[str] = None
    steuer_id:                Optional[str] = None
    steuerklasse:             Optional[int] = None
    sozialversicherungsnummer: Optional[str] = None

    # Banking
    bank_name:           Optional[str] = None
    bank_iban:           Optional[str] = None
    bank_bic:            Optional[str] = None
    bank_account_holder: Optional[str] = None

    # Employment
    work_city:               Optional[str]   = None
    department:              Optional[str]   = None
    employment_type:         Optional[str]   = None
    occupation:              Optional[str]   = None
    position_level:          Optional[str]   = None
    weekly_hours:            Optional[float] = None
    work_days_per_week:      Optional[float] = None
    daily_hours:             Optional[float] = None
    start_date:              Optional[str]   = None
    contract_type:           Optional[str]   = "temporary"
    hotel_name:              Optional[str]   = None
    end_date:                Optional[str]   = None
    probation_period_months: Optional[int]   = None
    previous_employer:       Optional[str]   = None
    education_level:         Optional[str]   = None

    # Accessibility
    disabled: Optional[bool] = None

    # System
    status:   Optional[str] = "draft"
    ordio_id: Optional[str] = None

    # Contract generation
    last_contract_path:                    Optional[str]      = None
    last_contract_generated_at:            Optional[datetime] = None
    last_contract_pdf_path:                Optional[str]      = None
    last_contract_pdf_path_generated_at:   Optional[datetime] = None
    upload_session_dir:                    Optional[str]      = None
    latest_upload_session_dir:             Optional[str]      = None
    collected_docs_docx:                   Optional[str]      = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeResponse(BaseModel):
    id:             int
    created_at:     datetime
    updated_at:     datetime
    approved_at:    Optional[datetime] = None
    approved_by:    Optional[str]      = None
    is_deleted:     bool               = False
    deleted_reason: Optional[str]      = None
    hotel_name:     Optional[str]      = None

    last_contract_path:         Optional[str]      = None
    last_contract_generated_at: Optional[datetime] = None
    upload_session_dir:         Optional[str]      = None
    latest_upload_session_dir:  Optional[str]      = None
    collected_docs_docx:        Optional[str]      = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id:           int
    action:       str
    employee_id:  int
    details:      str
    performed_by: str
    timestamp:    datetime

    model_config = ConfigDict(from_attributes=True)
