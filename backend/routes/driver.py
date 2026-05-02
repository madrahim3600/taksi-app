from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import User, Route
from auth import get_current_user

router = APIRouter(prefix="/driver", tags=["driver"])

class UpdateStatusRequest(BaseModel):
    is_online: bool

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Faqat haydovchilar uchun")
    days_left = None
    if current_user.subscription_expires:
        delta = current_user.subscription_expires - datetime.utcnow()
        days_left = max(0, delta.days)
    return {
        "id": current_user.id,
        "name": current_user.name,
        "phone": current_user.phone,
        "car_model": current_user.car_model,
        "car_number": current_user.car_number,
        "is_online": current_user.is_online,
        "is_approved": current_user.is_approved,
        "subscription_expires": str(current_user.subscription_expires) if current_user.subscription_expires else None,
        "days_left": days_left
    }

@router.post("/toggle-status")
async def toggle_status(
    request: UpdateStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Faqat haydovchilar uchun")
    if not current_user.is_approved:
        raise HTTPException(status_code=403, detail="Admin hali tasdiqlamagan")
    if current_user.subscription_expires and current_user.subscription_expires < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Obuna muddati tugagan")
    current_user.is_online = request.is_online
    current_user.last_seen = datetime.utcnow()
    db.commit()
    return {"success": True, "is_online": current_user.is_online}

@router.get("/routes")
async def get_routes(db: Session = Depends(get_db)):
    routes = db.query(Route).filter(Route.is_active == True).all()
    return [{"id": r.id, "name": r.name, "from_city": r.from_city, "to_city": r.to_city} for r in routes]
