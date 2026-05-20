from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ---------- Region ----------

class RegionBase(BaseModel):
    region_name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=10)

class RegionCreate(RegionBase):
    pass

class RegionResponse(RegionBase):
    region_id: int


# ---------- Package ----------

class PackageBase(BaseModel):
    package_name: str = Field(..., min_length=2, max_length=100)
    monthly_fee: float = Field(..., gt=0)
    speed_mbps: int = Field(..., ge=0)
    quota_gb: Optional[int] = Field(None, ge=0)  # None = sınırsız

class PackageCreate(PackageBase):
    pass

class PackageUpdate(BaseModel):
    package_name: Optional[str] = Field(None, min_length=2, max_length=100)
    monthly_fee: Optional[float] = Field(None, gt=0)
    speed_mbps: Optional[int] = Field(None, ge=0)
    quota_gb: Optional[int] = Field(None, ge=0)

class PackageResponse(PackageBase):
    package_id: int


# ---------- Customer ----------

class CustomerBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    phone_number: str
    email: EmailStr
    region_id: Optional[int] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^\+?\d{10,13}$", cleaned):
            raise ValueError("Geçersiz telefon numarası formatı.")
        return cleaned

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    region_id: Optional[int] = None

class CustomerResponse(CustomerBase):
    customer_id: int
    created_at: Optional[str] = None


# ---------- Subscription ----------

class SubscriptionCreate(BaseModel):
    customer_id: int
    package_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class SubscriptionUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|cancelled|suspended)$")

class SubscriptionResponse(BaseModel):
    subscription_id: int
    customer_id: int
    package_id: int
    package_name: str
    price_at_purchase: float
    status: str
    started_at: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class SubscriptionDetail(BaseModel):
    subscription_id: int
    first_name: str
    last_name: str
    package_name: str
    price_at_purchase: float
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ---------- Employee ----------

class EmployeeCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=50)

class EmployeeResponse(EmployeeCreate):
    employee_id: int


# ---------- Invoice ----------

class InvoiceCreate(BaseModel):
    subscription_id: int
    amount: float = Field(..., gt=0)
    due_date: date
    status: Optional[str] = Field(default="Unpaid", pattern="^(Unpaid|Paid|Overdue)$")

class InvoiceUpdate(BaseModel):
    status: str = Field(..., pattern="^(Unpaid|Paid|Overdue)$")

class InvoiceResponse(BaseModel):
    invoice_id: int
    subscription_id: int
    amount: float
    due_date: str
    status: str


# ---------- Payment ----------

class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1, max_length=50)

class PaymentResponse(BaseModel):
    payment_id: int
    invoice_id: int
    payment_date: Optional[str] = None
    amount: float
    payment_method: str


# ---------- SupportTicket ----------

class SupportTicketCreate(BaseModel):
    customer_id: int
    employee_id: Optional[int] = None
    subject: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(default="Open", pattern="^(Open|In Progress|Resolved|Closed)$")

class SupportTicketUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(Open|In Progress|Resolved|Closed)$")
    employee_id: Optional[int] = None

class SupportTicketResponse(BaseModel):
    ticket_id: int
    customer_id: int
    employee_id: Optional[int] = None
    subject: str
    description: Optional[str] = None
    status: str
    created_at: Optional[str] = None


# ---------- ProcessPayment (sp_process_payment için) ----------

class ProcessPaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1, max_length=50)
