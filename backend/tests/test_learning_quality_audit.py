import pytest
from sqlalchemy import select
from app.models.user import Student
from app.models.curriculum import Topic, Concept
from app.models.learning import ConceptMastery, Misconception, LearningSession, LearningEvent
from app.models.assessment import Question
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.services.mastery_engine import MasteryEngine
from app.services.gamification_engine import GamificationEngine
from app.services.ai import get_ai_provider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.mock_provider import MockAIProvider
from app.services.audio_service import VoiceInteractionRequest, VoiceMode


@pytest.mark.asyncio
async def test_scenario_1_strong_student_strategy_selection(db_session):
    """
    Scenario 1: Strong student learns concept quickly.
    Audits whether diagnostic score of 1.0 correctly routes to FIRST_PRINCIPLES.
    Code defect: In evaluate_diagnostic, diagnostic_score >= 0.70 selects STEP_BY_STEP,
    completely ignoring FIRST_PRINCIPLES.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    tutor = TutorEngine(db_session)
    sess_data = await tutor.start_lesson_session(student.id, concept.topic_id, concept.id)
    eval_res = await tutor.evaluate_diagnostic(sess_data["session_id"], diagnostic_score=1.0)

    # In a true pedagogical tutor, a 100% diagnostic score should activate FIRST_PRINCIPLES.
    # The current code sets STEP_BY_STEP:
    assert eval_res["selected_strategy"] == "STEP_BY_STEP"


@pytest.mark.asyncio
async def test_scenario_2_weak_student_strategy_selection(db_session):
    """
    Scenario 2: Weak student.
    Audits whether low diagnostic score (<0.40) routes to WORKED_EXAMPLE.
    Code defect: evaluate_diagnostic sets ANALOGY instead of WORKED_EXAMPLE.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    tutor = TutorEngine(db_session)
    sess_data = await tutor.start_lesson_session(student.id, concept.topic_id, concept.id)
    eval_res = await tutor.evaluate_diagnostic(sess_data["session_id"], diagnostic_score=0.20)

    # Current code assigns ANALOGY instead of WORKED_EXAMPLE
    assert eval_res["selected_strategy"] == "ANALOGY"


@pytest.mark.asyncio
async def test_scenario_3_misconception_negation_trap(db_session):
    """
    Scenario 3: Misconception string-matching trap.
    Audits whether the mock evaluator penalizes a student who explicitly negates a misconception.
    """
    ai = get_ai_provider()
    eval_result = await ai.evaluate_student_answer(
        question_prompt="Why does pure water not conduct electricity?",
        student_answer="In liquids current is carried by dissolved ions, and NOT by free electrons.",
        expected_concepts=["dissolved ions", "free charges"],
        required_points=["pure water has no ions"],
        misconception_traps={"electrons": "Belief that electrons flow freely in water"},
        curriculum_context="Pure water lacks ions.",
    )

    # Substring trap catches 'electrons' even though student explicitly stated NOT free electrons
    assert eval_result.misconception_detected is not None
    assert eval_result.is_correct is False


@pytest.mark.asyncio
async def test_scenario_4_lucky_answer_inflation(db_session):
    """
    Scenario 4: Lucky correct answer.
    Audits whether a single correct answer causes an unrealistic jump in mastery
    despite lack of evidence (evidence_count = 1).
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    m_rec = (await db_session.execute(select(ConceptMastery).where(
        ConceptMastery.student_id == student.id,
        ConceptMastery.concept_id == concept.id,
    ))).scalars().first()
    if m_rec:
        await db_session.delete(m_rec)
        await db_session.commit()

    mastery_engine = MasteryEngine(db_session)
    m1 = await mastery_engine.record_answer_attempt(
        student_id=student.id,
        concept_id=concept.id,
        is_correct=True,
        difficulty_level=3,
    )

    assert m1.evidence_count == 1
    assert m1.confidence == "LOW"
    # Demonstrates mastery inflation: 1 lucky answer gives 100% mastery!
    assert m1.mastery_score >= 0.80


@pytest.mark.asyncio
async def test_scenario_5_high_confidence_incorrect_answer_unhandled(db_session):
    """
    Scenario 5: High confidence but incorrect answer.
    Audits whether the tutor provides deeper remediation for high-confidence misconceptions.
    Current code: evaluate_answer treats all incorrect answers identically, ignoring confidence.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    mastery_engine = MasteryEngine(db_session)
    m = await mastery_engine.get_or_create_concept_mastery(student.id, concept.id)
    m.confidence = "HIGH"
    m.evidence_count = 10
    await db_session.commit()

    assessment = AssessmentEngine(db_session)
    q = (await db_session.execute(select(Question).where(Question.concept_id == concept.id))).scalars().first()

    res = await assessment.evaluate_answer(
        student_id=student.id,
        question_id=q.id,
        student_answer="Wrong answer",
        selected_option_key="B",
    )
    # The evaluation output has no indication of high-confidence calibration:
    assert "remediation_depth" not in res


@pytest.mark.asyncio
async def test_scenario_6_correct_answer_low_confidence_reinforcement(db_session):
    """
    Scenario 6: Correct answer with low confidence.
    Audits whether correct answer with low evidence provides reinforcement rather than immediate escalation.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    mastery_engine = MasteryEngine(db_session)
    m = await mastery_engine.get_or_create_concept_mastery(student.id, concept.id)
    m.confidence = "LOW"
    m.evidence_count = 1
    await db_session.commit()

    assessment = AssessmentEngine(db_session)
    q = (await db_session.execute(select(Question).where(Question.concept_id == concept.id))).scalars().first()

    res = await assessment.evaluate_answer(
        student_id=student.id,
        question_id=q.id,
        student_answer="A",
        selected_option_key="A",
    )
    # System reports is_correct=True, but doesn't flag reinforcement recommendation
    assert res["is_correct"] is True
    assert res["confidence"] == "LOW"


@pytest.mark.asyncio
async def test_scenario_7_feynman_failure_does_not_reduce_mastery(db_session):
    """
    Scenario 7: Feynman failure impact on mastery.
    Failing the Feynman explanation does not decrease concept mastery score.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    mastery_engine = MasteryEngine(db_session)
    tutor_engine = TutorEngine(db_session)
    assessment_engine = AssessmentEngine(db_session)

    m = await mastery_engine.get_or_create_concept_mastery(student.id, concept.id)
    m.mastery_score = 0.85
    await db_session.commit()

    sess_data = await tutor_engine.start_lesson_session(student.id, concept.topic_id, concept.id)
    sess_id = sess_data["session_id"]

    res = await assessment_engine.evaluate_explain_it_back(
        session_id=sess_id,
        student_answer="blah blah blah",
        concept_id=concept.id,
    )

    assert res["accurate"] is False
    await db_session.refresh(m)
    assert m.mastery_score == 0.85


@pytest.mark.asyncio
async def test_scenario_8_voice_teach_forces_state_transition(db_session):
    """
    Scenario 8: Voice interaction behavior.
    Triggering VoiceMode.TEACH forcibly advances the session to CHECKING_UNDERSTANDING.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    tutor = TutorEngine(db_session)
    sess = await tutor.start_lesson_session(student.id, concept.topic_id, concept.id)
    assert sess["state"] == "TEACHING"

    from app.api.v1.voice import voice_interact
    from app.services.audio_service import VoiceInteractionRequest, VoiceMode

    req = VoiceInteractionRequest(
        session_id=sess["session_id"],
        transcript="",
        mode=VoiceMode.TEACH,
    )
    voice_res = await voice_interact(payload=req, student=student, db=db_session)

    db_sess = (await db_session.execute(select(LearningSession).where(LearningSession.id == sess["session_id"]))).scalars().first()
    assert db_sess.state == "CHECKING_UNDERSTANDING"


@pytest.mark.asyncio
async def test_scenario_9_gemini_provider_phase_c_delegation(db_session):
    """
    Scenario 9: AI Provider architecture audit.
    GeminiProvider unconditionally delegates Phase C methods to MockAIProvider,
    bypassing actual Gemini API integration.
    """
    gemini = GeminiProvider(api_key="fake_key_for_test")
    # All 4 Phase C methods delegate to self.fallback:
    assert isinstance(gemini.fallback, MockAIProvider)


@pytest.mark.asyncio
async def test_scenario_10_xp_idempotency_farming(db_session):
    """
    Scenario 10: Repeated API request / Idempotency defect in award_xp.
    award_xp checks for a LearningEvent with item_key, but never creates it,
    allowing infinite duplicate XP farming.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    gamification = GamificationEngine(db_session)
    key = "unique-test-q-farming-99"

    res1 = await gamification.award_xp(student.id, 25, "First attempt", item_key=key)
    assert res1["awarded_xp"] == 25

    res2 = await gamification.award_xp(student.id, 25, "Second duplicate attempt", item_key=key)
    assert res2["awarded_xp"] == 25
