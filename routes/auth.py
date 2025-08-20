from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth.auth import get_current_user
from schemas.schemas import UserCreate, LoginRequest, VerifyCodeRequest, PurchaseRequest, SubscriptionsResponse
from services.auth_service import seed_plans, register_service, login_service, verify_code_service, purchase_service, add_voucher_service, check_subscription_service

router = APIRouter(tags=["Auth"])

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
