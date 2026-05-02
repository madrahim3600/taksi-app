import os
import sys
from dotenv import load_dotenv

load_dotenv('/home/taksi/taksi-app/backend/.env')
sys.path.insert(0, '/home/taksi/taksi-app/backend')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from models import User, Route, Message, VerificationCode

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from database import SessionLocal
    from models import Route
    db = SessionLocal()
    try:
        if db.query(Route).count() == 0:
            routes = [
                Route(name="Toshkent - Samarqand", from_city="Toshkent", to_city="Samarqand"),
                Route(name="Toshkent - Buxoro", from_city="Toshkent", to_city="Buxoro"),
                Route(name="Toshkent - Namangan", from_city="Toshkent", to_city="Namangan"),
                Route(name="Toshkent - Fargona", from_city="Toshkent", to_city="Fargona"),
                Route(name="Samarqand - Buxoro", from_city="Samarqand", to_city="Buxoro"),
            ]
            db.add_all(routes)
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(title="Taksi API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes.auth_routes import router as auth_router
from routes.driver import router as driver_router
from routes.client import router as client_router
from routes.admin import router as admin_router
from routes.chat import router as chat_router

app.include_router(auth_router)
app.include_router(driver_router)
app.include_router(client_router)
app.include_router(admin_router)
app.include_router(chat_router)

@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "Server ishlayapti!"}
