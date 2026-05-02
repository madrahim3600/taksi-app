import os
import sys
import random
import string
from dotenv import load_dotenv

load_dotenv('/home/taksi/taksi-app/backend/.env')
sys.path.insert(0, '/home/taksi/taksi-app/backend')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from models import User, Group, Message, VerificationCode, driver_groups

Base.metadata.create_all(bind=engine)

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@asynccontextmanager
async def lifespan(app: FastAPI):
    from database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(Group).count() == 0:
            groups = [
                Group(name="Toshkent - Samarqand", description="Toshkent Samarqand yo'nalishi", invite_code=gen_code()),
                Group(name="Toshkent - Buxoro", description="Toshkent Buxoro yo'nalishi", invite_code=gen_code()),
                Group(name="Toshkent - Namangan", description="Toshkent Namangan yo'nalishi", invite_code=gen_code()),
                Group(name="Toshkent - Fargona", description="Toshkent Fargona yo'nalishi", invite_code=gen_code()),
                Group(name="Samarqand - Buxoro", description="Samarqand Buxoro yo'nalishi", invite_code=gen_code()),
            ]
            db.add_all(groups)
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(title="TaksiBor API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes.login_routes import router as auth_router
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
    return {"status": "ok", "message": "TaksiBor API v2 ishlayapti!"}
