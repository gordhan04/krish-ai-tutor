from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_student, verify_session_ownership
from app.models.user import Student
from app.services.tutor_engine import TutorEngine
from app.schemas.tutor import (
    LessonStartRequest,
    LessonStartResponse,
    HintRequest,
    HintResponse,
    SocraticCheckRequest,
    SocraticCheckResponse,
    SocraticEvaluateRequest,
    SocraticEvaluateResponse,
    DiagnosticStartRequest,
    DiagnosticStartResponse,
    DiagnosticEvaluateRequest,
    DiagnosticEvaluateResponse,
    RemediateRequest,
    RemediateResponse,
    MasteryCompleteRequest,
    MasteryCompleteResponse,
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
            strategy=payload.strategy,
        )
        return LessonStartResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/hint", response_model=HintResponse)
async def get_hint(
    payload: HintRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await verify_session_ownership(payload.session_id, student.id, db)
    engine = TutorEngine(db)
    try:
        result = await engine.get_next_hint(
            session_id=payload.session_id,
            question_prompt=payload.question_prompt,
        )
        return HintResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/socratic-check", response_model=SocraticCheckResponse)
async def socratic_check(
    payload: SocraticCheckRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await verify_session_ownership(payload.session_id, student.id, db)
    engine = TutorEngine(db)
    try:
        result = await engine.check_socratic_understanding(session_id=payload.session_id)
        return SocraticCheckResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/socratic-evaluate", response_model=SocraticEvaluateResponse)
async def socratic_evaluate(
    payload: SocraticEvaluateRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await verify_session_ownership(payload.session_id, student.id, db)
    engine = TutorEngine(db)
    try:
        result = await engine.evaluate_socratic_response(
            session_id=payload.session_id,
            student_response=payload.student_response,
        )
        return SocraticEvaluateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/diagnostic", response_model=DiagnosticStartResponse)
async def run_diagnostic(
    payload: DiagnosticStartRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await verify_session_ownership(payload.session_id, student.id, db)
    engine = TutorEngine(db)
    try:
        result = await engine.run_diagnostic(session_id=payload.session_id)
        return DiagnosticStartResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/diagnostic/evaluate", response_model=DiagnosticEvaluateResponse)
async def evaluate_diagnostic(
    payload: DiagnosticEvaluateRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await verify_session_ownership(payload.session_id, student.id, db)
    engine = TutorEngine(db)
    try:
        result = await engine.evaluate_diagnostic(
            session_id=payload.session_id,
            diagnostic_score=payload.diagnostic_score,
        )
        return DiagnosticEvaluateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/remediate", response_model=RemediateResponse)
async def remediate_misconception(
    payload: RemediateRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await verify_session_ownership(payload.session_id, student.id, db)
    engine = TutorEngine(db)
    try:
        result = await engine.remediate_misconception(
            session_id=payload.session_id,
            misconception_id=payload.misconception_id,
        )
        return RemediateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/complete", response_model=MasteryCompleteResponse)
async def complete_session(
    payload: MasteryCompleteRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await verify_session_ownership(payload.session_id, student.id, db)
    engine = TutorEngine(db)
    try:
        result = await engine.check_mastery_completion(session_id=payload.session_id)
        return MasteryCompleteResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/session/resume/{session_id}")
async def resume_session(
    session_id: str,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await verify_session_ownership(session_id, student.id, db)
    engine = TutorEngine(db)
    try:
        result = await engine.resume_session(session_id=session_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
