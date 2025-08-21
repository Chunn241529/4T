from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth.auth import get_current_user
from schemas.schemas import UserCreate, LoginRequest, VerifyCodeRequest, PurchaseRequest, SubscriptionsResponse
from services.auth_service import seed_plans, register_service, login_service, verify_code_service, purchase_service, add_voucher_service, check_subscription_service
from google_auth_oauthlib.flow import Flow
from models.models import User
import logging
import os

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth", "Google Drive"])

# Đường dẫn đến file client_secrets.json
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "..", "client_secret_399293753103-9e2hhelbc2j6rc24hmuhfpl7gfeepbeb.apps.googleusercontent.com.json")
SCOPES = ['https://www.googleapis.com/auth/drive.file']
REDIRECT_URI = "http://localhost:8000/oauth/callback"

# Kiểm tra file client_secrets.json
if not os.path.exists(CLIENT_SECRETS_FILE):
    logger.error("client_secrets.json not found at %s", CLIENT_SECRETS_FILE)
    raise ValueError("client_secrets.json not found. Please place it in the project root directory.")

@router.on_event("startup")
async def startup_event():
    db = next(get_db())
    try:
        seed_plans(db)
    finally:
        db.close()

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    return register_service(user, db)


@router.post("/login")
def login(login: LoginRequest, db: Session = Depends(get_db)):
    return login_service(login, db)

@router.post("/verify_code")
def verify_code(verify: VerifyCodeRequest, db: Session = Depends(get_db)):
    return verify_code_service(verify, db)

@router.post("/purchase")
def purchase(purchase: PurchaseRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return purchase_service(purchase, current_user, db)

@router.post("/add_voucher")
def add_voucher(code: str, discount_percent: float, valid_days: int, db: Session = Depends(get_db)):
    return add_voucher_service(code, discount_percent, valid_days, db)

@router.get("/check_subscription", response_model=SubscriptionsResponse)
def check_subscription(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return check_subscription_service(current_user, db)

@router.get("/auth/google")
async def auth_google(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    logger.info("Generated authorization URL for /auth/google: %s, state: %s", authorization_url, state)
    db.query(User).filter(User.id == current_user.id).update({"oauth_state": state})
    db.commit()
    return {
        "google_auth_url": authorization_url,
        "state": state
    }

# @router.get("/oauth/callback")
# async def oauth_callback(state: str, code: str, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.oauth_state == state).first()
#     if not user:
#         logger.error("Invalid state: %s", state)
#         raise HTTPException(status_code=401, detail="Invalid state")

#     flow = Flow.from_client_secrets_file(
#         CLIENT_SECRETS_FILE,
#         scopes=SCOPES,
#         state=state,
#         redirect_uri=REDIRECT_URI
#     )
#     try:
#         flow.fetch_token(code=code)
#     except Exception as e:
#         logger.error("Failed to fetch token: %s", str(e))
#         raise HTTPException(status_code=400, detail=f"Failed to fetch token: {str(e)}")

#     credentials = flow.credentials
#     logger.info("Fetched credentials: token=%s, refresh_token=%s, expiry=%s",
#                 credentials.token, credentials.refresh_token, credentials.expiry)

#     db.query(User).filter(User.id == user.id).update({
#         "google_access_token": credentials.token,
#         "google_refresh_token": credentials.refresh_token,
#         "google_token_expiry": credentials.expiry,
#         "oauth_state": None
#     })
#     db.commit()

#     return {"msg": "Google Drive authenticated successfully"}

@router.get("/google-auth")
def google_auth(username: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    logger.info("Generated authorization URL: %s, state: %s", authorization_url, state)

    db_user.oauth_state = state
    db.commit()

    return {
        "google_auth_url": authorization_url,
        "state": state
    }

@router.get("/oauth/callback")
def oauth_callback(code: str, state: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    db_user = db.query(User).filter(User.oauth_state == state).first()
    if not db_user:
        logger.error("Invalid state: %s", state)
        raise HTTPException(status_code=401, detail="Invalid state")

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.error("Failed to fetch token: %s", str(e))
        raise HTTPException(status_code=400, detail=f"Failed to fetch token: {str(e)}")

    credentials = flow.credentials
    logger.info("Received credentials: %s", credentials.to_json())

    # Lưu token vào cơ sở dữ liệu
    db_user.access_token = credentials.token
    db_user.refresh_token = credentials.refresh_token
    db_user.token_expiry = credentials.expiry
    db_user.oauth_state = None  # Xóa state sau khi sử dụng
    db.commit()

    return {
        "msg": "OAuth flow completed",
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "expires_in": str(credentials.expiry)
    }
