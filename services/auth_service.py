from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import hashlib
import json
from database import get_db
from models.models import User, Plan, Voucher, Subscription, ActivationCode, DeviceVerification
from schemas.schemas import (
    UserCreate, LoginRequest, VerifyCodeRequest, PurchaseRequest,
    SubscriptionsResponse, PlanCreate, PlanUpdate, PlanResponse
)
from auth.auth import get_password_hash, verify_password, create_access_token, generate_activation_code, send_activation_email

# Plans management services
def create_plan(plan_data: PlanCreate, db: Session):
    existing_plan = db.query(Plan).filter(Plan.name == plan_data.name).first()
    if existing_plan:
        raise HTTPException(status_code=400, detail="Gói này đã tồn tại")

    new_plan = Plan(**plan_data.dict())
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan

def get_all_plans(db: Session):
    return db.query(Plan).all()

def get_plan_by_id(plan_id: int, db: Session):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói")
    return plan

def update_plan(plan_id: int, plan_data: PlanUpdate, db: Session):
    plan = get_plan_by_id(plan_id, db)

    update_data = plan_data.dict(exclude_unset=True)
    if update_data.get('name'):
        existing_plan = db.query(Plan).filter(
            Plan.name == update_data['name'],
            Plan.id != plan_id
        ).first()
        if existing_plan:
            raise HTTPException(status_code=400, detail="Tên gói này đã tồn tại")

    for key, value in update_data.items():
        setattr(plan, key, value)

    db.commit()
    db.refresh(plan)
    return plan

def delete_plan(plan_id: int, db: Session):
    plan = get_plan_by_id(plan_id, db)

    # Kiểm tra xem có subscription nào đang sử dụng plan này không
    existing_subs = db.query(Subscription).filter(
        Subscription.plan_id == plan_id,
        Subscription.end_date >= datetime.utcnow()
    ).first()

    if existing_subs:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa gói này vì đang có người dùng sử dụng"
        )

    db.delete(plan)
    db.commit()
    return {"message": "Đã xóa gói thành công"}

def register_service(user: UserCreate, db: Session):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Tên người dùng đã được đăng ký")
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email đã được đăng ký")
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        hashed_password=hashed_password,
        is_active=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    code = generate_activation_code()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    activation_code = ActivationCode(
        user_id=new_user.id,
        code=code,
        expires_at=expires_at
    )
    db.add(activation_code)
    db.commit()

    send_activation_email(new_user.email, code)
    return {"msg": "Người dùng đã được tạo, mã kích hoạt đã được gửi đến email.", "username": new_user.username}

def generate_device_id(request: Request) -> str:
    # Lấy thông tin từ user agent
    user_agent = request.headers.get("user-agent", "")
    # Tạo một hash từ user agent (không dùng IP và timestamp vì chúng có thể thay đổi)
    return hashlib.sha256(user_agent.encode()).hexdigest()

def login_service(login: LoginRequest, request: Request, db: Session):
    db_user = db.query(User).filter(User.username == login.username).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Tên người dùng không tồn tại")
    if not db_user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản chưa được kích hoạt. Vui lòng verify code từ email.")
    if not verify_password(login.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Mật khẩu không đúng")

    # Tự động tạo device_id từ thông tin thiết bị
    device_id = generate_device_id(request)

    # Kiểm tra xem thiết bị đã được xác thực chưa
    device_ver = db.query(DeviceVerification).filter(
        DeviceVerification.user_id == db_user.id,
        DeviceVerification.device_id == device_id,
        DeviceVerification.expires_at >= datetime.utcnow()
    ).first()

    if device_ver:
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(data={"sub": db_user.username}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer", "device_id": device_id}

    code = generate_activation_code()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    activation_code = ActivationCode(
        user_id=db_user.id,
        code=code,
        expires_at=expires_at
    )
    db.add(activation_code)
    db.commit()

    send_activation_email(db_user.email, code)
    return {"msg": "Mã kích hoạt đã được gửi đến email", "username": db_user.username}

def verify_code_service(verify: VerifyCodeRequest, request: Request, db: Session):
    db_user = db.query(User).filter(User.username == verify.username).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Không tìm thấy người dùng")

    # Tự động tạo device_id từ thông tin thiết bị
    device_id = generate_device_id(request)

    activation_code = db.query(ActivationCode).filter(
        ActivationCode.user_id == db_user.id,
        ActivationCode.code == verify.code,
        ActivationCode.expires_at >= datetime.utcnow()
    ).first()

    if not activation_code:
        raise HTTPException(status_code=401, detail="Mã kích hoạt không hợp lệ hoặc đã hết hạn")

    db.query(ActivationCode).filter(ActivationCode.user_id == db_user.id).delete()
    db.commit()

    if not db_user.is_active:
        db_user.is_active = True
        db.commit()

    # Tự động tạo device_id từ thông tin thiết bị
    device_id = generate_device_id(request)

    # Kiểm tra và cập nhật thông tin thiết bị
    existing_device = db.query(DeviceVerification).filter(
        DeviceVerification.user_id == db_user.id,
        DeviceVerification.device_id == device_id
    ).first()

    if existing_device:
        existing_device.verified_at = datetime.utcnow()
        existing_device.expires_at = datetime.utcnow() + timedelta(days=30)
    else:
        new_device = DeviceVerification(
            user_id=db_user.id,
            device_id=device_id,
            verified_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(new_device)
    db.commit()

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(data={"sub": db_user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

def purchase_service(purchase: PurchaseRequest, current_user, db: Session):
    plan = db.query(Plan).filter(Plan.id == purchase.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói")

    discount = 0.0
    if purchase.voucher_code:
        voucher = db.query(Voucher).filter(Voucher.code == purchase.voucher_code).first()
        if voucher and voucher.expiry_date >= datetime.utcnow():
            discount = voucher.discount
        else:
            raise HTTPException(status_code=400, detail="Mã giảm giá không hợp lệ hoặc đã hết hạn")

    final_price = plan.price * (1 - discount / 100)
    print(f"Mô phỏng thanh toán {final_price} cho người dùng {current_user.username}")

    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=plan.duration_months * 30)
    api_key = str(uuid.uuid4())

    sub = Subscription(user_id=current_user.id, plan_id=plan.id, start_date=start_date, end_date=end_date, api_key=api_key)
    db.add(sub)
    db.commit()
    return {"api_key": api_key, "end_date": end_date}

def add_voucher_service(code: str, discount_percent: float, valid_days: int, db: Session):
    valid_until = datetime.utcnow() + timedelta(days=valid_days)
    voucher = Voucher(code=code, discount=discount_percent, expiry_date=valid_until, max_usage=100, used_count=0)
    db.add(voucher)
    db.commit()
    return {"msg": "Mã giảm giá đã được thêm"}

def check_subscription_service(current_user, db: Session) -> SubscriptionsResponse:
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date >= datetime.utcnow()
    ).all()

    if not subscriptions:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói đăng ký đang hoạt động")

    return {
        "subscriptions": [
            {
                "plan_name": sub.plan.name,
                "api_key": sub.api_key,
                "start_date": sub.start_date,
                "end_date": sub.end_date
            }
            for sub in subscriptions
        ]
    }
