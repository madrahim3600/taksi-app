from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models import User, Route, Message
from taksi_auth import get_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

class AddDaysRequest(BaseModel):
    user_id: int
    days: int

class ApproveRequest(BaseModel):
    user_id: int
    approved: bool

class AddRouteRequest(BaseModel):
    name: str
    from_city: str
    to_city: str

@router.get("/stats")
async def get_stats(admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    total_drivers = db.query(User).filter(User.role == "driver").count()
    active_subs = db.query(User).filter(
        User.role == "driver",
        User.subscription_expires > datetime.utcnow()
    ).count()
    online_users = db.query(User).filter(User.is_online == True).count()
    pending = db.query(User).filter(
        User.role == "driver",
        User.is_approved == False
    ).count()
    return {
        "total_drivers": total_drivers,
        "active_subscriptions": active_subs,
        "online_users": online_users,
        "pending_drivers": pending
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
            "car_model": d.car_model,
            "car_number": d.car_number,
            "is_approved": d.is_approved,
            "is_online": d.is_online,
            "days_left": days_left,
            "route_id": d.route_id,
            "subscription_expires": str(d.subscription_expires) if d.subscription_expires else None
        })
    return result

@router.post("/approve")
async def approve_driver(request: ApproveRequest, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
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
        user.subscription_expires = user.subscription_expires + timedelta(days=request.days)
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

@router.get("/messages")
async def get_messages(admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    messages = db.query(Message).filter(
        Message.is_deleted == False
    ).order_by(Message.created_at.desc()).limit(100).all()
    result = []
    for m in messages:
        result.append({
            "id": m.id,
            "sender_id": m.sender_id,
            "sender_name": m.sender.name if m.sender else "Noma'lum",
            "content": m.content,
            "chat_room": m.chat_room,
            "created_at": str(m.created_at)
        })
    return result

@router.delete("/message/{message_id}")
async def delete_message(message_id: int, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Topilmadi")
    msg.is_deleted = True
    db.commit()
    return {"success": True}

@router.post("/routes")
async def add_route(request: AddRouteRequest, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    route = Route(name=request.name, from_city=request.from_city, to_city=request.to_city)
    db.add(route)
    db.commit()
    return {"success": True, "id": route.id}

@router.delete("/route/{route_id}")
async def delete_route(route_id: int, admin=Depends(get_admin_user), db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Topilmadi")
    route.is_active = False
    db.commit()
    return {"success": True}
