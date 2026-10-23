from datetime import datetime, timezone
from sqlalchemy import DateTime, Double, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

# Integer keys work in both MySQL and SQLite for this teaching project.
def now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(50), default='')
    last_name: Mapped[str] = mapped_column(String(50), default='')
    contact_number: Mapped[str] = mapped_column(String(16), default='')
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Resume(Base):
    __tablename__ = 'resumes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(600))
    extracted_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Interview(Base):
    __tablename__ = 'interviews'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True)
    role: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    custom_kind: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20))
    question_limit: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(20), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Question(Base):
    __tablename__ = 'questions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey('interviews.id', ondelete='CASCADE'), index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(20))

class Answer(Base):
    __tablename__ = 'answers'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id', ondelete='CASCADE'), unique=True)
    text: Mapped[str] = mapped_column(Text)
    correctness: Mapped[float] = mapped_column(Float)
    relevance: Mapped[float] = mapped_column(Float)
    clarity: Mapped[float] = mapped_column(Float)
    examples: Mapped[float] = mapped_column(Float)
    overall: Mapped[float] = mapped_column(Float)
    feedback: Mapped[str] = mapped_column(Text)
    improved_answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class PeerRoom(Base):
    __tablename__ = 'peer_rooms'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    interviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    topic: Mapped[str] = mapped_column(String(100))
    duration_seconds: Mapped[int] = mapped_column(Integer, default=900)
    status: Mapped[str] = mapped_column(String(20), default='waiting')
    started_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    ended_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    code: Mapped[str] = mapped_column(Text, default='')
    problem: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class RoomEvent(Base):
    __tablename__ = 'room_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey('peer_rooms.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    kind: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey('peer_rooms.id', ondelete='CASCADE'), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(600))
    kind: Mapped[str] = mapped_column(String(20))
    pages: Mapped[list] = mapped_column(JSON)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

class RecoveryCode(Base):
    __tablename__ = 'recovery_codes'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(255))

class RevokedToken(Base):
    __tablename__ = 'revoked_tokens'
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[float] = mapped_column(Double)

class TokenVersion(Base):
    __tablename__ = 'token_versions'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)

class LoginSession(Base):
    __tablename__ = 'login_sessions'
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    created_at: Mapped[float] = mapped_column(Double)
    last_seen_at: Mapped[float] = mapped_column(Double)
    expires_at: Mapped[float] = mapped_column(Double, index=True)
