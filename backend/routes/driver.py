from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models import User, Group, driver_groups
from taksi_auth import get_current_user

router = APIRouter(prefix="/driver", tags=["driver"])

class StatusRequest(BaseModel):
    is_online: bool

@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Faqat haydovchilar uchun")
    days_left = None
    if current_user.subscription_expires:
        delta = current_user.subscription_expires - datetime.utcnow()
        days_left = max(0, delta.days)
    groups = []
    for g in current_user.groups:
        row = db.execute(
            driver_groups.select().where(
                and_(driver_groups.c.driver_id == current_user.id,
                     driver_groups.c.group_id == g.id)
            )
        ).fetchone()
        if row:
            groups.append({
                "id": g.id,
                "name": g.name,
                "invite_code": g.invite_code,
                "is_approved": row.is_approved
            })
    return {
        "id": current_user.id,
        "name": current_user.name,
        "phone": current_user.phone,
        "car_model": current_user.car_model or "",
        "car_number": current_user.car_number or "",
        "is_online": current_user.is_online,
        "is_approved": current_user.is_approved,
        "subscription_expires": str(current_user.subscription_expires) if current_user.subscription_expires else None,
        "days_left": days_left,
        "groups": groups
    }

@router.post("/toggle-status")
async def toggle_status(
    request: StatusRequest,
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

@router.get("/groups")
async def get_my_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Faqat haydovchilar uchun")
    result = []
    for g in current_user.groups:
        row = db.execute(
            driver_groups.select().where(
                and_(driver_groups.c.driver_id == current_user.id,
                     driver_groups.c.group_id == g.id)
            )
        ).fetchone()
        if row and row.is_approved:
            result.append({
                "id": g.id,
                "name": g.name,
                "invite_code": g.invite_code
            })
    return result
