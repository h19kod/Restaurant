from typing import Optional

from pydantic import BaseModel, Field

from app.models import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=128)
    role: UserRole
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    tenant_id: int
    username: str
    full_name: str
    role: UserRole
    phone: Optional[str]
    is_active: bool
