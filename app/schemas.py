from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    mobile: Optional[str] = None

class UserCreate(UserBase):
    password: str
    is_vendor: bool = False

class UserLogin(BaseModel):
    email_or_mobile: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_vendor: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Profile schemas
class ProfileBase(BaseModel):
    company_name: Optional[str] = None
    ntn: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

# Post schemas
class PostBase(BaseModel):
    content: str
    image_url: Optional[str] = None
    visibility: str = "public"

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    content: Optional[str] = None
    image_url: Optional[str] = None
    visibility: Optional[str] = None

class PostResponse(PostBase):
    id: int
    user_id: int
    likes_count: int
    comments_count: int
    shares_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True