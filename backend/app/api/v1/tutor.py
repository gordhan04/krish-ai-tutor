from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_student
from app.models.user import Student
from app.services.tutor_engine import TutorEngine
from app.schemas.tutor import (
    LessonStartRequest,
    LessonStartResponse,
    HintRequest,
    HintResponse,
    SocraticCheckRequest,
    SocraticCheckResponse,
)

router = APIRouter(prefix="/tutor", tags=["Tutor Engine"])


@router.post("/lesson/start", response_model=LessonStartResponse)
async def start_lesson(
    payload: LessonStartRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    engine = TutorEngine(db)
    try:
        result = await engine.start_lesson_session(
            student_id=student.id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
        )
        return LessonStartResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/hint", response_model=HintResponse)
async def get_hint(
    payload: HintRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    engine = TutorEngine(db)
    try:
        result = await engine.get_next_hint(
            session_id=payload.session_id,
            question_prompt=payload.question_prompt,
        )
        return HintResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/socratic-check", response_model=SocraticCheckResponse)
async def socratic_check(
    payload: SocraticCheckRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    engine = TutorEngine(db)
    try:
        result = await engine.check_socratic_understanding(session_id=payload.session_id)
        return SocraticCheckResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
