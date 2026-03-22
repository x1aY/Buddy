import jwt
from datetime import datetime, timedelta
from typing import Optional
from config import settings
from models.schemas import JwtPayload, UserInfo


def create_jwt_token(user: UserInfo, expires_days: int = 30) -> str:
    """Create JWT token for user"""
    now = int(datetime.now().timestamp())
    payload = {
        "userId": user.id,
        "userName": user.name,
        "provider": user.provider,
        "iat": now,
        "exp": now + expires_days * 24 * 60 * 60
    }
    encoded = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded


def verify_jwt_token(token: str) -> Optional[JwtPayload]:
    """Verify JWT token and return payload"""
    try:
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return JwtPayload(**decoded)
    except jwt.PyJWTError:
        return None
