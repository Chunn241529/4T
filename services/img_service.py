from fastapi import HTTPException, status
from pydantic import BaseModel
from typing import Optional
import httpx
from auth.auth import validate_api_key
from models.models import Subscription, ImageGenerationHistory, User
from config.settings import API_TIMEOUT, COMFYUI_API_URL, COMFYUI_HISTORY_URL, COMFYUI_VIEW_URL
from config.payload import payload_genimage_realistic
from sqlalchemy.orm import Session
from datetime import datetime
from schemas.schemas import ImageGenRequest, ImageGenerationResponse
import asyncio
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from google.auth.transport.requests import Request

async def refresh_google_token(user, db: Session):
    if user.google_token_expiry and user.google_token_expiry < datetime.utcnow():
        credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id="your-client-id.apps.googleusercontent.com",
            client_secret="your-client-secret"
        )
        credentials.refresh(Request())
        db.query(User).filter(User.id == user.id).update({
            "google_access_token": credentials.token,
            "google_token_expiry": credentials.expiry
        })
        db.commit()
        return credentials
    return Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="your-client-id.apps.googleusercontent.com",
        client_secret="your-client-secret"
    )

async def save_image_to_drive(image_data: bytes, filename: str, positive_prompt: str, size: str, subscription_id: int, current_user, db: Session):
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date >= datetime.utcnow()
    ).all()
    if not any(sub.plan.name in ["Semi-Annual", "Annual"] for sub in subscriptions):
        raise HTTPException(status_code=403, detail="Yêu cầu gói Semi-Annual hoặc Annual để lưu ảnh vào Google Drive")

    if not current_user.google_access_token:
        raise HTTPException(status_code=403, detail="Vui lòng cấp quyền Google Drive trước. Truy cập /auth/google.")

    credentials = await refresh_google_token(current_user, db)
    drive_service = build('drive', 'v3', credentials=credentials)

    file_metadata = {'name': filename}
    media = MediaIoBaseUpload(io.BytesIO(image_data), mimetype='image/png', resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    # Lưu vào ImageGenerationHistory
    image_history = ImageGenerationHistory(
        user_id=current_user.id,
        subscription_id=subscription_id,
        positive_prompt=positive_prompt,
        size=size,
        drive_file_id=file.get('id')
    )
    db.add(image_history)
    db.commit()

    return file.get('id')

async def generate_image_service(request: ImageGenRequest, user, db: Session) -> ImageGenerationResponse:
    # Kiểm tra định dạng size
    try:
        width, height = map(int, request.size.split("x"))
        if width <= 0 or height <= 0:
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="Định dạng size không hợp lệ. Vui lòng cung cấp theo dạng 'widthxheight'.")

    # Tìm API key hợp lệ
    api_key = None
    subscription_id = None
    subscription = db.query(Subscription).filter(
        Subscription.api_key == request.api_key if request.api_key else Subscription.user_id == user.id,
        Subscription.user_id == user.id,
        Subscription.end_date >= datetime.utcnow()
    ).order_by(Subscription.end_date.desc()).first()

    if not subscription:
        raise HTTPException(status_code=401 if request.api_key else 404,
                            detail="API key không hợp lệ hoặc đã hết hạn" if request.api_key else "Không tìm thấy gói đăng ký đang hoạt động")

    api_key = request.api_key or subscription.api_key
    subscription_id = subscription.id

    # Xác thực API key
    try:
        validated_user = await validate_api_key(api_key=api_key, db=db)
        if not validated_user:
            raise HTTPException(status_code=401, detail="API key không hợp lệ")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Lỗi xác thực: {str(e)}")

    # Tạo payload ComfyUI từ config.payload, sử dụng user.id làm client_id
    comfyui_payload = payload_genimage_realistic(
        client_id=user.id,
        positive_prompt=request.positive_prompt,
        width=width,
        height=height
    )

    # Gọi API ComfyUI /api/prompt
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        try:
            response = await client.post(COMFYUI_API_URL, json=comfyui_payload)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi gọi API ComfyUI /api/prompt: {str(e)}")

        # Lấy prompt_id từ response
        if "prompt_id" not in result:
            raise HTTPException(status_code=500, detail="Không tìm thấy prompt_id từ ComfyUI")

        prompt_id = result["prompt_id"]

        # Gọi API /api/history để lấy thông tin filename
        filename = None
        max_retries = 20
        retry_delay = 3
        for attempt in range(max_retries):
            try:
                history_response = await client.get(f"{COMFYUI_HISTORY_URL}?max_items=64")
                history_response.raise_for_status()
                history_data = history_response.json()

                # Tìm filename từ node 30 trong history
                if str(prompt_id) in history_data:
                    outputs = history_data[str(prompt_id)].get("outputs", {})
                    if "30" in outputs:
                        output_files = outputs["30"].get("images", [])
                        if output_files and isinstance(output_files, list):
                            filename = output_files[0].get("filename")
                            if filename and outputs["30"]["images"][0].get("type") == "output":
                                break
                await asyncio.sleep(retry_delay)
            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail=f"Lỗi khi gọi API ComfyUI /api/history: {str(e)}")

        if not filename:
            raise HTTPException(status_code=500, detail="Không thể lấy filename từ ComfyUI history sau nhiều lần thử")

        # Gọi API /api/view để lấy ảnh
        image_data = None
        try:
            view_params = {
                "filename": filename,
                "subfolder": "",
                "type": "output",
                "rand": str(datetime.now().timestamp())
            }
            image_response = await client.get(COMFYUI_VIEW_URL, params=view_params)
            image_response.raise_for_status()
            image_data = image_response.content
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi lấy ảnh từ ComfyUI /api/view: {str(e)}")

    if not image_data:
        raise HTTPException(status_code=500, detail="Không thể lấy dữ liệu ảnh từ ComfyUI")

    # Lưu ảnh vào Google Drive
    drive_filename = f"generated_image_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    file_id = await save_image_to_drive(image_data, drive_filename, request.positive_prompt, request.size, subscription_id, user, db)

    # Trả về response
    return ImageGenerationResponse(
        id=db.query(ImageGenerationHistory).filter(
            ImageGenerationHistory.user_id == user.id,
            ImageGenerationHistory.drive_file_id == file_id
        ).first().id,
        positive_prompt=request.positive_prompt,
        size=request.size,
        drive_file_id=file_id,
        timestamp=datetime.utcnow()
    )
