from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100))
    role = Column(String(20), default="client")
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    car_model = Column(String(100), nullable=True)
    car_number = Column(String(20), nullable=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    subscription_expires = Column(DateTime, nullable=True)
    messages_sent = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")

class Route(Base):
    __tablename__ = "routes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    from_city = Column(String(100))
    to_city = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    chat_room = Column(String(100), default="general")
    content = Column(Text, nullable=True)
    message_type = Column(String(20), default="text")
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    sender = relationship("User", back_populates="messages_sent", foreign_keys=[sender_id])

class VerificationCode(Base):
    __tablename__ = "verification_codes"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False)
    code = Column(String(10), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
