import pytest
from app.services.tutor_engine import TutorEngine
from app.core.state_machine import TutorState, validate_transition, StateTransitionError
from app.models.user import Student
from app.models.curriculum import Topic
from sqlalchemy import select


@pytest.mark.asyncio
async def test_state_machine_legal_and_illegal_transitions():
    # Legal transitions
    assert validate_transition(TutorState.IDLE, TutorState.LESSON_START) is True
    assert validate_transition(TutorState.LESSON_START, TutorState.TEACHING) is True
    assert validate_transition(TutorState.TEACHING, TutorState.CHECKING_UNDERSTANDING) is True
    assert validate_transition(TutorState.PRACTICE, TutorState.EVALUATING) is True
    assert validate_transition(TutorState.REMEDIATION, TutorState.CHECKING_UNDERSTANDING) is True
    assert validate_transition(TutorState.PRACTICE, TutorState.CHECKING_UNDERSTANDING) is True
    assert validate_transition(TutorState.CHECKING_UNDERSTANDING, TutorState.CHECKING_UNDERSTANDING) is True
    assert validate_transition(TutorState.REMEDIATION, TutorState.REMEDIATION) is True

    # Illegal transition: IDLE cannot jump directly to EVALUATING
    with pytest.raises(StateTransitionError):
        validate_transition(TutorState.IDLE, TutorState.EVALUATING)


@pytest.mark.asyncio
async def test_tutor_lesson_start_and_hint_ladder(db_session):
    engine = TutorEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    assert student is not None

    t_res = await db_session.execute(select(Topic))
    topic = t_res.scalars().first()
    assert topic is not None

    # Start Lesson
    lesson = await engine.start_lesson_session(student_id=student.id, topic_id=topic.id)
    assert lesson["state"] == TutorState.TEACHING.value
    assert "Electrolytes" in lesson["concept_name"]
    assert len(lesson["message"]) > 0
    assert len(lesson["curriculum_sources"]) > 0

    session_id = lesson["session_id"]

    # Check 5-tier Hint Ladder progression
    hint1 = await engine.get_next_hint(session_id, "Why does salt water conduct electricity?")
    assert hint1["hint_level"] == 1
    assert "Hint 1" in hint1["hint_message"]

    hint2 = await engine.get_next_hint(session_id, "Why does salt water conduct electricity?")
    assert hint2["hint_level"] == 2
    assert "Hint 2" in hint2["hint_message"]
