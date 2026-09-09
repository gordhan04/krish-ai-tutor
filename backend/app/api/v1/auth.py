from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User, Student
from app.schemas.auth import UserLogin, Token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Get student profile if student
    s_stmt = select(Student).where(Student.user_id == user.id)
    s_res = await db.execute(s_stmt)
    student = s_res.scalars().first()

    access_token = create_access_token(
        data={"sub": user.id, "role": user.role, "student_id": student.id if student else None}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role,
        student_id=student.id if student else None,
        display_name=student.display_name if student else user.email.split("@")[0],
    )
