from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth.auth import get_current_user
from schemas.schemas import ChatRequest, ChatHistoryResponse, ConversationResponse, ConversationCreate
from services.chat_service import create_conversation_service, stream_chat_service, get_conversations_service, get_history_service, delete_conversation_service, delete_history_service, edit_history_service

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(request: ConversationCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await create_conversation_service(request, user, db)

@router.post("")
async def stream_chat(request: ChatRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await stream_chat_service(request, user, db)

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await get_conversations_service(user, db)

@router.get("/history/{conversation_id}", response_model=List[ChatHistoryResponse])
async def get_history(conversation_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await get_history_service(conversation_id, user, db)

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await delete_conversation_service(conversation_id, user, db)

@router.delete("/history/{history_id}")
async def delete_history(history_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await delete_history_service(history_id, user, db)

@router.patch("/history/{history_id}")
async def edit_history(history_id: int, content: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await edit_history_service(history_id, content, user, db)
