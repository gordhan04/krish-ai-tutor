from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError
import hashlib
import os
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Hash plain_password with sha256 + salt and compare with stored hash."""
    try:
        salt, hash_val = hashed_password.split("$")
        check = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
        return check == hash_val
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate salted sha256 hash for secure password storage."""
    salt = os.urandom(16).hex()
    hash_val = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${hash_val}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
