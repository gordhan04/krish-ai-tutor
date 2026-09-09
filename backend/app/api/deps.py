from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, Student

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            if user:
                return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Optional dev bypass strictly only when explicitly enabled in configuration
    if settings.ALLOW_DEV_ANONYMOUS_AUTH:
        stmt = select(User).where(User.role == "student")
        result = await db.execute(stmt)
        dev_user = result.scalars().first()
        if dev_user:
            return dev_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(allowed_roles: List[str]):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles {allowed_roles}, but user has role '{current_user.role}'",
            )
        return current_user
    return role_checker


async def get_current_student(
    current_user: User = Depends(require_role(["student"])),
    db: AsyncSession = Depends(get_db),
) -> Student:
    stmt = select(Student).where(Student.user_id == current_user.id)
    result = await db.execute(stmt)
    student = result.scalars().first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not associated with this account",
        )
    return student


async def get_current_parent(
    current_user: User = Depends(require_role(["parent", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> User:
    return current_user


async def verify_session_ownership(
    session_id: str,
    student_id: str,
    db: AsyncSession,
):
    from app.models.learning import LearningSession
    stmt = select(LearningSession).where(LearningSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning session {session_id} not found",
        )
    if session.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to access or modify this learning session",
        )
    return session

