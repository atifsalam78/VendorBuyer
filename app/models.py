from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    mobile_code = Column(String, nullable=True)  # Added mobile country code
    mobile = Column(String, unique=True, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_vendor = Column(Boolean, default=False)
    gender = Column(String, nullable=True)  # Moved from Profile to User
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_name = Column(String, nullable=True)
    ntn = Column(String, nullable=True)  # National Tax Number
    address = Column(Text, nullable=True)
    country = Column(String, nullable=True)
    state = Column(String, nullable=True)
    city = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    website = Column(String, nullable=True)
    business_category = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    name = Column(String, nullable=True)
    establishment_year = Column(Integer, nullable=True)
    landline_code = Column(String, nullable=True)
    landline = Column(String, nullable=True)
    designation = Column(String, nullable=True)  # Added designation field
    connections_count = Column(Integer, default=0)  # Number of connections
    followers_count = Column(Integer, default=0)  # Number of followers
    following_count = Column(Integer, default=0)  # Number of accounts following
    tagline = Column(String, nullable=True)  # Company tagline/description
    
    # Social links
    linkedin = Column(String, nullable=True)
    twitter = Column(String, nullable=True)
    facebook = Column(String, nullable=True)
    instagram = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="profile")