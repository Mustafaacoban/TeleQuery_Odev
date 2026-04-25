from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ---------- Region ----------

class RegionBase(BaseModel):
    region_name: str = Field(..., min_length=2, max_length=100)

class RegionCreate(RegionBase):
    pass

class RegionResponse(RegionBase):
    region_id: int


# ---------- Package ----------

class PackageBase(BaseModel):
    package_name: str = Field(..., min_length=2, max_length=100)
    monthly_fee: float = Field(..., gt=0)

class PackageCreate(PackageBase):
    pass

class PackageUpdate(BaseModel):
    package_name: Optional[str] = Field(None, min_length=2, max_length=100)
    monthly_fee: Optional[float] = Field(None, gt=0)

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

class SubscriptionDetail(BaseModel):
    subscription_id: int
    first_name: str
    last_name: str
    package_name: str
    price_at_purchase: float
    status: str
