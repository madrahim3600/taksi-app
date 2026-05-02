from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import os

from database import get_db
from models import User, VerificationCode
from auth import create_access_token, generate_code

router = APIRouter(prefix="/auth", tags=["auth"])

class SendCodeRequest(BaseModel):
    phone: str
    role: str = "client"

class VerifyCodeRequest(BaseModel):
    phone: str
    code: str
    name: Optional[str] = None
    car_model: Optional[str] = None
    car_number: Optional[str] = None
    route_id: Optional[int] = None

class AdminLoginRequest(BaseModel):
    username: str
    password: str

@router.post("/send-code")
async def send_code(request: SendCodeRequest, db: Session = Depends(get_db)):
    code = generate_code()
    expires = datetime.utcnow() + timedelta(minutes=10)
    db.query(VerificationCode).filter(
        VerificationCode.phone == request.phone
    ).delete()
    verification = VerificationCode(
        phone=request.phone,
        code=code,
        expires_at=expires
    )
    db.add(verification)
    db.commit()
    print(f"KOD: {request.phone} -> {code}")
    return {
        "success": True,
        "message": "Kod yuborildi",
        "demo_code": code
    }

@router.post("/verify-code")
async def verify_code(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    verification = db.query(VerificationCode).filter(
        VerificationCode.phone == request.phone,
        VerificationCode.code == request.code,
        VerificationCode.is_used == False,
        VerificationCode.expires_at > datetime.utcnow()
    ).first()
    if not verification:
        raise HTTPException(status_code=400, detail="Noto'g'ri yoki muddati o'tgan kod")
    verification.is_used = True
    db.commit()
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        is_driver = bool(request.car_model)
        user = User(
            phone=request.phone,
            name=request.name or f"Foydalanuvchi_{request.phone[-4:]}",
            role="driver" if is_driver else "client",
            is_approved=not is_driver,
            car_model=request.car_model,
            car_number=request.car_number,
            route_id=request.route_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "is_approved": user.is_approved,
            "car_model": user.car_model,
            "car_number": user.car_number
        }
    }

@router.post("/admin-login")
async def admin_login(request: AdminLoginRequest, db: Session = Depends(get_db)):
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin2024!")
    if request.username != admin_username or request.password != admin_password:
        raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
    admin = db.query(User).filter(User.role == "admin").first()
    if not admin:
        admin = User(
            phone="admin",
            name="Administrator",
            role="admin",
            is_approved=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    token = create_access_token(data={"sub": str(admin.id)})
    return {"success": True, "token": token}
