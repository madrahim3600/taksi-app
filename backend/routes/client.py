from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import User, Route
from taksi_auth import get_current_user

router = APIRouter(prefix="/client", tags=["client"])

@router.get("/routes")
async def get_routes(db: Session = Depends(get_db)):
    routes = db.query(Route).filter(Route.is_active == True).all()
    result = []
    for route in routes:
        driver_count = db.query(User).filter(
            User.route_id == route.id,
            User.role == "driver",
            User.is_approved == True
        ).count()
        online_count = db.query(User).filter(
            User.route_id == route.id,
            User.role == "driver",
            User.is_approved == True,
            User.is_online == True
        ).count()
        result.append({
            "id": route.id,
            "name": route.name,
            "from_city": route.from_city,
            "to_city": route.to_city,
            "total_drivers": driver_count,
            "online_drivers": online_count
        })
    return result

@router.get("/drivers/{route_id}")
async def get_drivers(route_id: int, db: Session = Depends(get_db)):
    drivers = db.query(User).filter(
        User.route_id == route_id,
        User.role == "driver",
        User.is_approved == True
    ).all()
    result = []
    for d in drivers:
        result.append({
            "id": d.id,
            "name": d.name,
            "phone": d.phone,
            "car_model": d.car_model,
            "car_number": d.car_number,
            "is_online": d.is_online,
            "last_seen": str(d.last_seen) if d.last_seen else None
        })
    return result

@router.get("/search")
async def search_drivers(q: str, db: Session = Depends(get_db)):
    drivers = db.query(User).filter(
        User.role == "driver",
        User.is_approved == True,
        User.name.ilike(f"%{q}%")
    ).all()
    result = []
    for d in drivers:
        result.append({
            "id": d.id,
            "name": d.name,
            "phone": d.phone,
            "car_model": d.car_model,
            "car_number": d.car_number,
            "is_online": d.is_online
        })
    return result
