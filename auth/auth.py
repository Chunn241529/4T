from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from config.settings import SECRET_KEY, ALGORITHM
from database import get_db
from models.models import Subscription, User, ActivationCode
import random
import string

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def validate_api_key(api_key: str = Header(None), db: Session = Depends(get_db)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    sub = db.query(Subscription).filter(Subscription.api_key == api_key).first()
    if not sub or sub.end_date < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    return sub.user

def generate_activation_code():
    return ''.join(random.choices(string.digits, k=6))

def send_activation_email(email: str, code: str):
    print(f"Sending activation code {code} to {email}")
    # Example with smtplib (uncomment and configure for production):
    """
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(f"Your activation code is: {code}")
    msg['Subject'] = 'Activation Code'
    msg['From'] = 'your-email@example.com'
    msg['To'] = email
    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login('your-email@example.com', 'your-password')
        server.sendmail('your-email@example.com', email, msg.as_string())
    """
