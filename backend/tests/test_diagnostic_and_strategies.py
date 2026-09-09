import pytest
from app.services.tutor_engine import TutorEngine
from app.core.state_machine import TutorState, validate_transition
from app.models.user import Student
from app.models.curriculum import Topic
from app.services.ai import get_ai_provider
from sqlalchemy import select


@pytest.mark.asyncio
async def test_diagnostic_run_and_evaluation(db_session):
    engine = TutorEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    assert student is not None

    t_res = await db_session.execute(select(Topic))
    topic = t_res.scalars().first()
    assert topic is not None

    # 1. Start lesson
    lesson = await engine.start_lesson_session(student_id=student.id, topic_id=topic.id)
    session_id = lesson["session_id"]
    assert lesson["state"] == TutorState.TEACHING.value

    # 2. Run diagnostic
    diag = await engine.run_diagnostic(session_id)
    assert diag["state"] == TutorState.DIAGNOSTIC.value
    assert diag["lesson_phase"] == "DIAGNOSTIC"
    assert diag["diagnostic_questions_count"] > 0

    # 3. Evaluate diagnostic with low score (0.30) -> should select ANALOGY
    eval_low = await engine.evaluate_diagnostic(session_id, diagnostic_score=0.30)
    assert eval_low["state"] == TutorState.TEACHING.value
    assert eval_low["selected_strategy"] == "ANALOGY"
    assert eval_low["pre_test_score"] == 0.30

    # 4. Evaluate diagnostic with high score (0.80) -> should select STEP_BY_STEP
    eval_high = await engine.evaluate_diagnostic(session_id, diagnostic_score=0.80)
    assert eval_high["selected_strategy"] == "STEP_BY_STEP"


@pytest.mark.asyncio
async def test_pedagogical_strategy_explanations():
    ai = get_ai_provider()
    strategies = ["ANALOGY", "STEP_BY_STEP", "REAL_WORLD_EXAMPLE", "CORRECT_MISCONCEPTION", "SOCRATIC"]

    for strat in strategies:
        resp = await ai.generate_strategy_explanation(
            concept_name="Electrolytes & Ionic Conduction",
            learning_objective="Understand how dissolved salts conduct electric current",
            curriculum_context="Pure water is poor conductor. Salt dissociates into ions.",
            strategy=strat,
            student_name="Krish",
        )
        assert resp.message is not None
        assert len(resp.message) > 30
        assert resp.strategy == strat


@pytest.mark.asyncio
async def test_phase_c_state_progression():
    # Legal progression chain in Phase C
    assert validate_transition(TutorState.IDLE, TutorState.LESSON_START) is True
    assert validate_transition(TutorState.LESSON_START, TutorState.DIAGNOSTIC) is True
    assert validate_transition(TutorState.DIAGNOSTIC, TutorState.TEACHING) is True
    assert validate_transition(TutorState.TEACHING, TutorState.CHECKING_UNDERSTANDING) is True
    assert validate_transition(TutorState.CHECKING_UNDERSTANDING, TutorState.PRACTICE) is True
    assert validate_transition(TutorState.PRACTICE, TutorState.REMEDIATION) is True
    assert validate_transition(TutorState.REMEDIATION, TutorState.PRACTICE) is True
    assert validate_transition(TutorState.PRACTICE, TutorState.EXPLAIN_IT_BACK) is True
    assert validate_transition(TutorState.EXPLAIN_IT_BACK, TutorState.MASTERY_REVIEW) is True
    assert validate_transition(TutorState.MASTERY_REVIEW, TutorState.CHAPTER_COMPLETE) is True
