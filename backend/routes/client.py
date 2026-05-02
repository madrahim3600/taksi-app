from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database import get_db
from models import User, Group, Message, driver_groups
from taksi_auth import get_current_user

router = APIRouter(prefix="/client", tags=["client"])

@router.get("/search")
async def search_groups(q: str = "", db: Session = Depends(get_db)):
    if not q.strip():
        return []
    groups = db.query(Group).filter(
        Group.is_active == True
    ).filter(
        Group.name.ilike(f"%{q}%") | Group.invite_code.ilike(f"%{q}%")
    ).all()
    result = []
    for g in groups:
        rows = db.execute(
            driver_groups.select().where(
                and_(driver_groups.c.group_id == g.id,
                     driver_groups.c.is_approved == True)
            )
        ).fetchall()
        approved_ids = [r.driver_id for r in rows]
        approved_drivers = db.query(User).filter(User.id.in_(approved_ids)).all()
        online = [d for d in approved_drivers if d.is_online]
        result.append({
            "id": g.id,
            "name": g.name,
            "description": g.description or "",
            "invite_code": g.invite_code,
            "total_drivers": len(approved_drivers),
            "online_drivers": len(online)
        })
    return result

@router.get("/group/{group_id}")
async def get_group(group_id: int, db: Session = Depends(get_db)):
    g = db.query(Group).filter(
        Group.id == group_id,
        Group.is_active == True
    ).first()
    if not g:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")
    rows = db.execute(
        driver_groups.select().where(
            and_(driver_groups.c.group_id == g.id,
                 driver_groups.c.is_approved == True)
        )
    ).fetchall()
    approved_ids = [r.driver_id for r in rows]
    drivers = db.query(User).filter(User.id.in_(approved_ids)).all()
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description or "",
        "invite_code": g.invite_code,
        "drivers": [{
            "id": d.id,
            "name": d.name,
            "phone": d.phone,
            "car_model": d.car_model or "",
            "car_number": d.car_number or "",
            "is_online": d.is_online,
            "last_seen": str(d.last_seen) if d.last_seen else None
        } for d in drivers]
    }

@router.get("/group/{group_id}/messages")
async def get_messages(group_id: int, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(
        Message.group_id == group_id,
        Message.is_deleted == False
    ).order_by(Message.created_at.asc()).limit(100).all()
    return [{
        "id": m.id,
        "sender_id": m.sender_id,
        "sender_name": m.sender.name if m.sender else "Noma'lum",
        "content": m.content or "",
        "message_type": m.message_type,
        "created_at": str(m.created_at)
    } for m in msgs]
