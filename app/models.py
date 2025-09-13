from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class ProfileImage(Base):
    __tablename__ = "profile_images"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    profile_pic = Column(String, nullable=True)
    banner_pic = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="profile_image")

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
    profile_image = relationship("ProfileImage", back_populates="user", uselist=False)

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

class Like(Base):
    __tablename__ = "likes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), index=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User")
    post = relationship("Post", back_populates="likes")
    
    # Unique constraint to prevent duplicate likes
    __table_args__ = (
        Index('ix_likes_user_post', 'user_id', 'post_id', unique=True),
    )

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)  # Indexed for high traffic
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    visibility = Column(String, default="public")  # public, connections, private
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    
    # Add indexes for high traffic optimization
    __table_args__ = (
        Index('ix_posts_created_at', 'created_at'),  # For sorting by recent posts
        Index('ix_posts_user_created', 'user_id', 'created_at'),  # For user-specific feeds
        Index('ix_posts_visibility', 'visibility'),  # For visibility filtering
    )