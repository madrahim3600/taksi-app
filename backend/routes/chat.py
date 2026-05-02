from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
from datetime import datetime

from database import SessionLocal
from models import Message, User

router = APIRouter(prefix="/chat", tags=["chat"])

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, ws: WebSocket, room: str):
        await ws.accept()
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(ws)

    def disconnect(self, ws: WebSocket, room: str):
        if room in self.rooms and ws in self.rooms[room]:
            self.rooms[room].remove(ws)

    async def broadcast(self, data: dict, room: str):
        if room in self.rooms:
            for ws in self.rooms[room][:]:
                try:
                    await ws.send_text(json.dumps(data))
                except:
                    self.rooms[room].remove(ws)

manager = ConnectionManager()

@router.websocket("/ws/group/{group_id}/{user_id}")
async def group_chat(ws: WebSocket, group_id: int, user_id: int):
    room = f"group_{group_id}"
    await manager.connect(ws, room)
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
            data = await ws.receive_text()
            msg_data = json.loads(data)
            new_msg = Message(
                sender_id=user_id,
                group_id=group_id,
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
                "content": msg_data.get("content", ""),
                "message_type": msg_data.get("type", "text"),
                "created_at": str(new_msg.created_at)
            }, room)
    except WebSocketDisconnect:
        manager.disconnect(ws, room)
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
