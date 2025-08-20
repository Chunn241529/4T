from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth.auth import get_current_user
from schemas.schemas import ImageGenRequest, ImageGenerationResponse
from services.img_service import generate_image_service

router = APIRouter(
    prefix="/genimg",
    tags=["Image Generation"]
)

@router.post("", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return await generate_image_service(request, user, db)
