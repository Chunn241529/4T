from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, JSON, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=False)
    oauth_state = Column(String, nullable=True)
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    google_token_expiry = Column(DateTime, nullable=True)

    chat_history = relationship("ChatHistory", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    device_verifications = relationship("DeviceVerification", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    image_generation_history = relationship("ImageGenerationHistory", back_populates="user")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_id = Column(Integer, ForeignKey("plans.id"))
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    api_key = Column(String, unique=True, index=True)

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    chat_history = relationship("ChatHistory", back_populates="subscription")
    image_generation_history = relationship("ImageGenerationHistory", back_populates="subscription")

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    duration_months = Column(Integer)
    price = Column(Float)

    subscriptions = relationship("Subscription", back_populates="plan")

class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    discount = Column(Float)
    expiry_date = Column(DateTime)
    max_usage = Column(Integer)
    used_count = Column(Integer, default=0)

class ActivationCode(Base):
    __tablename__ = "activation_codes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    code = Column(String, index=True)
    expires_at = Column(DateTime)

    user = relationship("User")

class DeviceVerification(Base):
    __tablename__ = "device_verifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(String, index=True)
    verified_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="device_verifications")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    chat_history = relationship("ChatHistory", back_populates="conversation")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    role = Column(String)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    embedding = Column(JSON, nullable=True)

    user = relationship("User", back_populates="chat_history")
    conversation = relationship("Conversation", back_populates="chat_history")
    subscription = relationship("Subscription", back_populates="chat_history")

class ImageGenerationHistory(Base):
    __tablename__ = "image_generation_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    positive_prompt = Column(Text, nullable=False)
    size = Column(String, nullable=False)  # Format: "widthxheight"
    drive_file_id = Column(String, nullable=True)  # ID tệp trên Google Drive
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="image_generation_history")
    subscription = relationship("Subscription", back_populates="image_generation_history")
