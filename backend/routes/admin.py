from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import datetime, timedelta
import random, string

from database import get_db
from models import User, Group, Message, driver_groups
from taksi_auth import get_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

class AddDaysRequest(BaseModel):
    user_id: int
    days: int

class ApproveRequest(BaseModel):
    user_id: int
    approved: bool

class GroupRequest(BaseModel):
    name: str
    description: str = ""

class DriverGroupRequest(BaseModel):
    driver_id: int
    group_id: int
    approved: bool = True

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@router.get("/stats")
async def stats(admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    return {
        "total_drivers": db.query(User).filter(User.role == "driver").count(),
        "active_subscriptions": db.query(User).filter(
            User.role == "driver",
            User.subscription_expires > datetime.utcnow()
        ).count(),
        "online_users": db.query(User).filter(User.is_online == True).count(),
        "pending_drivers": db.query(User).filter(
            User.role == "driver",
            User.is_approved == False
        ).count(),
        "total_groups": db.query(Group).filter(Group.is_active == True).count()
    }

@router.get("/drivers")
async def get_drivers(admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    drivers = db.query(User).filter(User.role == "driver").all()
    result = []
    for d in drivers:
        days_left = None
        if d.subscription_expires:
            delta = d.subscription_expires - datetime.utcnow()
            days_left = max(0, delta.days)
        result.append({
            "id": d.id,
            "name": d.name,
            "phone": d.phone,
            "car_model": d.car_model or "",
            "car_number": d.car_number or "",
            "is_approved": d.is_approved,
            "is_online": d.is_online,
            "days_left": days_left,
            "subscription_expires": str(d.subscription_expires) if d.subscription_expires else None
        })
    return result

@router.post("/approve")
async def approve(request: ApproveRequest, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Topilmadi")
    user.is_approved = request.approved
    db.commit()
    return {"success": True}

@router.post("/add-days")
async def add_days(request: AddDaysRequest, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Topilmadi")
    now = datetime.utcnow()
    if user.subscription_expires and user.subscription_expires > now:
        user.subscription_expires += timedelta(days=request.days)
    else:
        user.subscription_expires = now + timedelta(days=request.days)
    db.commit()
    return {"success": True, "expires": str(user.subscription_expires)}

@router.post("/reset-sub/{user_id}")
async def reset_sub(user_id: int, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Topilmadi")
    user.subscription_expires = None
    user.is_online = False
    db.commit()
    return {"success": True}

@router.delete("/driver/{user_id}")
async def delete_driver(user_id: int, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Topilmadi")
    db.delete(user)
    db.commit()
    return {"success": True}

@router.get("/groups")
async def get_groups(admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    groups = db.query(Group).filter(Group.is_active == True).all()
    return [{
        "id": g.id,
        "name": g.name,
        "description": g.description or "",
        "invite_code": g.invite_code,
        "driver_count": len(g.drivers),
        "created_at": str(g.created_at)
    } for g in groups]

@router.post("/groups")
async def create_group(request: GroupRequest, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    group = Group(
        name=request.name,
        description=request.description,
        invite_code=gen_code()
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"success": True, "id": group.id, "invite_code": group.invite_code}

@router.put("/groups/{group_id}")
async def update_group(group_id: int, request: GroupRequest, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Topilmadi")
    group.name = request.name
    group.description = request.description
    db.commit()
    return {"success": True}

@router.delete("/groups/{group_id}")
async def delete_group(group_id: int, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Topilmadi")
    group.is_active = False
    db.commit()
    return {"success": True}

@router.post("/driver-group")
async def manage_driver_group(request: DriverGroupRequest, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    driver = db.query(User).filter(User.id == request.driver_id).first()
    group = db.query(Group).filter(Group.id == request.group_id).first()
    if not driver or not group:
        raise HTTPException(status_code=404, detail="Topilmadi")
    existing = db.execute(
        driver_groups.select().where(
            and_(driver_groups.c.driver_id == request.driver_id,
                 driver_groups.c.group_id == request.group_id)
        )
    ).fetchone()
    if existing:
        db.execute(
            driver_groups.update().where(
                and_(driver_groups.c.driver_id == request.driver_id,
                     driver_groups.c.group_id == request.group_id)
            ).values(is_approved=request.approved)
        )
    else:
        db.execute(driver_groups.insert().values(
            driver_id=request.driver_id,
            group_id=request.group_id,
            is_approved=request.approved
        ))
    db.commit()
    return {"success": True}

@router.get("/group/{group_id}/drivers")
async def group_drivers(group_id: int, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Topilmadi")
    result = []
    for d in group.drivers:
        row = db.execute(
            driver_groups.select().where(
                and_(driver_groups.c.driver_id == d.id,
                     driver_groups.c.group_id == group_id)
            )
        ).fetchone()
        result.append({
            "id": d.id,
            "name": d.name,
            "phone": d.phone,
            "car_model": d.car_model or "",
            "is_approved": row.is_approved if row else False,
            "is_online": d.is_online
        })
    return result

@router.get("/messages")
async def get_messages(admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(
        Message.is_deleted == False
    ).order_by(Message.created_at.desc()).limit(100).all()
    return [{
        "id": m.id,
        "sender_id": m.sender_id,
        "sender_name": m.sender.name if m.sender else "Noma'lum",
        "content": m.content or "",
        "group_id": m.group_id,
        "created_at": str(m.created_at)
    } for m in msgs]

@router.delete("/message/{message_id}")
async def delete_message(message_id: int, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Topilmadi")
    msg.is_deleted = True
    db.commit()
    return {"success": True}
