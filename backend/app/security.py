from datetime import datetime, timedelta, timezone
import jwt
import hashlib
import secrets
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import JWT_SECRET, SESSION_COOKIE, SESSION_SECONDS, SESSION_IDLE_SECONDS, COOKIE_SECURE
from .db import get_db
from .models import User, RevokedToken, TokenVersion, LoginSession

password_hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def check_password(password: str, stored: str) -> bool:
    try:
        return password_hasher.verify(stored, password)
    except (VerifyMismatchError, VerificationError):
        return False

def make_token(user_id: int) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS)
    from .db import SessionLocal
    with SessionLocal() as db:
        version = db.get(TokenVersion, user_id)
        number = version.version if version else 0
        token = jwt.encode({'sub': str(user_id), 'exp': expiry, 'jti': secrets.token_hex(16), 'ver': number}, JWT_SECRET, algorithm='HS256')
        now = time.time()
        db.add(LoginSession(digest=hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
                            created_at=now, last_seen_at=now, expires_at=expiry.timestamp()))
        db.commit()
    return token


def session_cookie(response: Response, token: str):
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=COOKIE_SECURE, samesite='strict', path='/')

def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> User:
    token = credentials.credentials if credentials else request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail='Please log in first.')
    return user_from_token(token, db)


def user_from_token(token: str, db: Session, touch: bool = True) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'], options={'require': ['sub','exp','jti','ver']})
        user_id = int(payload['sub'])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail='Invalid or expired login.')
    if db.get(RevokedToken, hashlib.sha256(token.encode()).hexdigest()):
        raise HTTPException(401, 'Login has been revoked.')
    session = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
    now = time.time()
    if not session or session.expires_at <= now or session.last_seen_at + SESSION_IDLE_SECONDS <= now:
        raise HTTPException(401, 'Session expired. Please log in again.')
    if touch and now - session.last_seen_at >= 60:
        session.last_seen_at = now
        db.commit()
    version = db.get(TokenVersion, user_id)
    if payload.get('ver', 0) != (version.version if version else 0):
        raise HTTPException(401, 'Please log in after your password reset.')
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail='Account not found.')
    return user
