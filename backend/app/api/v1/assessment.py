from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_student
from app.models.user import Student
from app.services.assessment_engine import AssessmentEngine
from app.services.mastery_engine import MasteryEngine
from app.schemas.assessment import (
    QuestionOut,
    AnswerSubmitRequest,
    AnswerSubmitResponse,
)

router = APIRouter(prefix="/assessment", tags=["Assessment"])


@router.get("/question", response_model=QuestionOut)
async def get_practice_question(
    topic_id: str,
    concept_id: str,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    mastery_engine = MasteryEngine(db)
    mastery = await mastery_engine.get_or_create_concept_mastery(student.id, concept_id)

    assessment_engine = AssessmentEngine(db)
    question = await assessment_engine.get_adaptive_question(
        topic_id=topic_id,
        concept_id=concept_id,
        mastery_score=mastery.mastery_score,
    )
    if not question:
        raise HTTPException(status_code=404, detail="No question available for this concept")
    return question


@router.post("/answer", response_model=AnswerSubmitResponse)
async def submit_answer(
    payload: AnswerSubmitRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    engine = AssessmentEngine(db)
    try:
        result = await engine.evaluate_answer(
            student_id=student.id,
            question_id=payload.question_id,
            student_answer=payload.student_answer,
            selected_option_key=payload.selected_option_key,
            session_id=payload.session_id,
        )
        return AnswerSubmitResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
