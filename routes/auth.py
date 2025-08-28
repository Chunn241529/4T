from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth.auth import get_current_user
from schemas.schemas import (
    UserCreate, LoginRequest, VerifyCodeRequest, PurchaseRequest,
    SubscriptionsResponse, PlanCreate, PlanUpdate, PlanResponse
)
from services.auth_service import (
    register_service, login_service, verify_code_service, purchase_service,
    add_voucher_service, check_subscription_service,
    create_plan, get_all_plans, get_plan_by_id, update_plan, delete_plan
)
from google_auth_oauthlib.flow import Flow
from models.models import User
import logging
import os



# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])



# Plan management routes
@router.post("/plans", response_model=PlanResponse)
def add_plan(plan: PlanCreate, db: Session = Depends(get_db)):
    return create_plan(plan, db)

@router.get("/plans", response_model=list[PlanResponse])
def list_plans(db: Session = Depends(get_db)):
    return get_all_plans(db)

@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    return get_plan_by_id(plan_id, db)

@router.put("/plans/{plan_id}", response_model=PlanResponse)
def edit_plan(plan_id: int, plan: PlanUpdate, db: Session = Depends(get_db)):
    return update_plan(plan_id, plan, db)

@router.delete("/plans/{plan_id}")
def remove_plan(plan_id: int, db: Session = Depends(get_db)):
    return delete_plan(plan_id, db)

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    return register_service(user, db)


@router.post("/login")
def login(login: LoginRequest, request: Request, db: Session = Depends(get_db)):
    return login_service(login, request, db)

@router.post("/verify_code")
def verify_code(verify: VerifyCodeRequest, request: Request, db: Session = Depends(get_db)):
    return verify_code_service(verify, request, db)

@router.post("/purchase")
def purchase(purchase: PurchaseRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return purchase_service(purchase, current_user, db)

@router.post("/add_voucher")
def add_voucher(code: str, discount_percent: float, valid_days: int, db: Session = Depends(get_db)):
    return add_voucher_service(code, discount_percent, valid_days, db)

@router.get("/check_subscription", response_model=SubscriptionsResponse)
def check_subscription(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return check_subscription_service(current_user, db)


