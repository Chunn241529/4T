from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: str
    phone_number: Optional[str] = None
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: Optional[str] = None

class VerifyCodeRequest(BaseModel):
    username: str
    code: str
    device_id: Optional[str] = None

class PurchaseRequest(BaseModel):
    plan_id: int
    voucher_code: Optional[str] = None

class ChatRequest(BaseModel):
    model: str = "4T-N"
    prompt: str = "Chào bạn"
    api_key: Optional[str] = None

class SubscriptionResponse(BaseModel):
    plan_name: str
    api_key: str
    start_date: datetime
    end_date: datetime

    class Config:
        from_attributes = True

class SubscriptionsResponse(BaseModel):
    subscriptions: List[SubscriptionResponse]

class ConversationCreate(BaseModel):
    title: Optional[str] = None  # Optional, nếu không có thì tự generate

class ConversationResponse(BaseModel):
    id: int
    title: Optional[str]
    created_at: Optional[datetime] = None  # Cho phép None
    updated_at: Optional[datetime] = None  # Cho phép None

    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True

# Cập nhật ChatRequest để hỗ trợ conversation_id
class ChatRequest(BaseModel):
    model: str = "4T-N"
    prompt: str = "Chào bạn"
    api_key: Optional[str] = None
    conversation_id: Optional[int] = None  # Optional, nếu không có thì tạo mới

class ImageGenRequest(BaseModel):
    positive_prompt: str
    size: str  # Format: "widthxheight", ví dụ: "960x1024"
    api_key: Optional[str] = None

class ImageGenerationResponse(BaseModel):
    id: int
    positive_prompt: str
    size: str
    image_base64: str
    timestamp: datetime

    class Config:
        from_attributes = True  # Hỗ trợ ánh xạ từ model SQLAlchemy
