from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict
import json
from datetime import datetime

from database import get_db, SessionLocal
from models import Message, User
from auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            if websocket in self.active_connections[room]:
                self.active_connections[room].remove(websocket)

    async def broadcast(self, message: dict, room: str):
        if room in self.active_connections:
            for connection in self.active_connections[room][:]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    self.active_connections[room].remove(connection)

manager = ConnectionManager()

@router.websocket("/ws/{room}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room: str, user_id: int):
    await manager.connect(websocket, room)
    db = SessionLocal()
    user = None
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_online = True
            db.commit()
        await manager.broadcast({
            "type": "user_online",
            "user_id": user_id,
            "name": user.name if user else "Noma'lum"
        }, room)
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            new_msg = Message(
                sender_id=user_id,
                receiver_id=msg_data.get("receiver_id"),
                chat_room=room,
                content=msg_data.get("content"),
                message_type=msg_data.get("type", "text")
            )
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)
            await manager.broadcast({
                "type": "message",
                "id": new_msg.id,
                "sender_id": user_id,
                "sender_name": user.name if user else "Noma'lum",
                "content": msg_data.get("content"),
                "message_type": msg_data.get("type", "text"),
                "created_at": str(new_msg.created_at)
            }, room)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        if user:
            user.is_online = False
            user.last_seen = datetime.utcnow()
            db.commit()
        await manager.broadcast({
            "type": "user_offline",
            "user_id": user_id
        }, room)
    finally:
        db.close()

@router.get("/history/{room}")
async def get_history(room: str, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(
        Message.chat_room == room,
        Message.is_deleted == False
    ).order_by(Message.created_at.asc()).limit(100).all()
    result = []
    for m in messages:
        result.append({
            "id": m.id,
            "sender_id": m.sender_id,
            "sender_name": m.sender.name if m.sender else "Noma'lum",
            "content": m.content,
            "message_type": m.message_type,
            "created_at": str(m.created_at)
        })
    return result
