# routes/__init__.py
from fastapi import APIRouter
from .chat import router as chat_router
from .auth import router as auth_router
from .image import router as image_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(chat_router)
router.include_router(image_router)
