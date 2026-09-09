from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_student
from app.models.user import Student
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.services.audio_service import (
    VoiceInteractionRequest,
    VoiceInteractionResponse,
    VoiceMode,
    VoiceTurnState,
    StandardWebSpeechTTS,
)

router = APIRouter(prefix="/voice", tags=["Voice Tutoring"])


@router.post("/interact", response_model=VoiceInteractionResponse)
async def voice_interact(
    payload: VoiceInteractionRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified voice tutoring endpoint.
    Routes student verbal responses through the central Tutor and Assessment engines.
    """
    tts_provider = StandardWebSpeechTTS()
    tutor_engine = TutorEngine(db)
    assessment_engine = AssessmentEngine(db)

    try:
        tutor_message = ""
        next_mode = payload.mode

        if payload.mode == VoiceMode.TEACH:
            # Student asks for teaching or explanation verbally
            socratic_res = await tutor_engine.check_socratic_understanding(payload.session_id)
            tutor_message = socratic_res["socratic_question"]
            next_mode = VoiceMode.SOCRATIC

        elif payload.mode == VoiceMode.SOCRATIC:
            # Student verbally answered Socratic check
            eval_res = await tutor_engine.evaluate_socratic_response(
                session_id=payload.session_id,
                student_response=payload.transcript,
            )
            tutor_message = eval_res["feedback"]
            next_mode = VoiceMode.QUIZ if eval_res.get("understanding_confirmed") else VoiceMode.TEACH

        elif payload.mode == VoiceMode.EXPLAIN_IT_BACK:
            # Student explains concept in own words verbally (Feynman Technique)
            eval_res = await assessment_engine.evaluate_explain_it_back(
                session_id=payload.session_id,
                student_answer=payload.transcript,
                concept_id=payload.concept_id,
            )
            tutor_message = eval_res["feedback"]
            next_mode = VoiceMode.TEACH

        elif payload.mode == VoiceMode.QUIZ and payload.question_id:
            # Student verbally answered quiz question
            eval_res = await assessment_engine.evaluate_answer(
                student_id=student.id,
                question_id=payload.question_id,
                student_answer=payload.transcript,
                session_id=payload.session_id,
            )
            tutor_message = eval_res["feedback"]
            next_mode = VoiceMode.TEACH
        else:
            tutor_message = "I heard you! Let's continue with our lesson."

        synth_instructions = await tts_provider.synthesize(tutor_message)

        return VoiceInteractionResponse(
            session_id=payload.session_id,
            mode=payload.mode,
            turn_state=VoiceTurnState.SPEAKING,
            tutor_text_response=tutor_message,
            audio_synthesis_instructions=synth_instructions,
            fallback_to_text=False,
            next_mode=next_mode,
        )

    except Exception as e:
        # Graceful fallback: return safe text response without crashing
        fallback_msg = "I had a moment of trouble processing the voice audio, but don't worry! You can type your answer or try speaking again."
        synth_instructions = await tts_provider.synthesize(fallback_msg)
        return VoiceInteractionResponse(
            session_id=payload.session_id,
            mode=payload.mode,
            turn_state=VoiceTurnState.ERROR,
            tutor_text_response=fallback_msg,
            audio_synthesis_instructions=synth_instructions,
            fallback_to_text=True,
            next_mode=payload.mode,
        )
