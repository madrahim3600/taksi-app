from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import os
import httpx

from database import get_db
from models import User, VerificationCode
from taksi_auth import create_access_token, generate_code

router = APIRouter(prefix="/auth", tags=["auth"])

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

class SendCodeRequest(BaseModel):
    phone: str
    role: str = "client"
    telegram_id: Optional[str] = None

class VerifyCodeRequest(BaseModel):
    phone: str
    code: str
    name: Optional[str] = None
    car_model: Optional[str] = None
    car_number: Optional[str] = None
    route_id: Optional[int] = None
    telegram_id: Optional[str] = None

class AdminLoginRequest(BaseModel):
    username: str
    password: str

async def send_tg(telegram_id: str, code: str):
    if not TELEGRAM_TOKEN or not telegram_id:
        return False
    try:
        text = f"🚖 TaksiBor tasdiqlash kodi:\n\n{code}\n\nKod 10 daqiqa amal qiladi."
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json={
                "chat_id": telegram_id,
                "text": text
            }, timeout=5)
            return res.status_code == 200
    except:
        return False

@router.post("/send-code")
async def send_code(request: SendCodeRequest, db: Session = Depends(get_db)):
    code = generate_code()
    expires = datetime.utcnow() + timedelta(minutes=10)
    db.query(VerificationCode).filter(
        VerificationCode.phone == request.phone
    ).delete()
    db.add(VerificationCode(phone=request.phone, code=code, expires_at=expires))
    db.commit()
    tg_sent = False
    if request.telegram_id:
        tg_sent = await send_tg(request.telegram_id, code)
    print(f"KOD: {request.phone} -> {code}")
    return {
        "success": True,
        "telegram_sent": tg_sent,
        "demo_code": None if tg_sent else code
    }

@router.post("/verify-code")
async def verify_code(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    v = db.query(VerificationCode).filter(
        VerificationCode.phone == request.phone,
        VerificationCode.code == request.code,
        VerificationCode.is_used == False,
        VerificationCode.expires_at > datetime.utcnow()
    ).first()
    if not v:
        raise HTTPException(status_code=400, detail="Noto'g'ri yoki muddati o'tgan kod")
    v.is_used = True
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
            route_id=request.route_id,
            avatar=request.telegram_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif request.telegram_id:
        user.avatar = request.telegram_id
        db.commit()
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
    if request.username != os.getenv("ADMIN_USERNAME","admin") or \
       request.password != os.getenv("ADMIN_PASSWORD","Admin2024!"):
        raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
    admin = db.query(User).filter(User.role == "admin").first()
    if not admin:
        admin = User(phone="admin", name="Administrator", role="admin", is_approved=True)
        db.add(admin)
        db.commit()
        db.refresh(admin)
    token = create_access_token(data={"sub": str(admin.id)})
    return {"success": True, "token": token}
