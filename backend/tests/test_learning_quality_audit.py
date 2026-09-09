import pytest
from sqlalchemy import select
from app.models.user import Student, User
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
    Verifies that a diagnostic score of 1.0 (100%) routes to FIRST_PRINCIPLES.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    tutor = TutorEngine(db_session)
    sess_data = await tutor.start_lesson_session(student.id, concept.topic_id, concept.id)
    eval_res = await tutor.evaluate_diagnostic(sess_data["session_id"], diagnostic_score=1.0)

    # In a true pedagogical tutor, a 100% diagnostic score activates FIRST_PRINCIPLES
    assert eval_res["selected_strategy"] == "FIRST_PRINCIPLES"


@pytest.mark.asyncio
async def test_scenario_2_weak_student_strategy_selection(db_session):
    """
    Scenario 2: Weak student struggling with basics.
    Verifies that a low diagnostic score (<0.40) routes to WORKED_EXAMPLE.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    tutor = TutorEngine(db_session)
    sess_data = await tutor.start_lesson_session(student.id, concept.topic_id, concept.id)
    eval_res = await tutor.evaluate_diagnostic(sess_data["session_id"], diagnostic_score=0.20)

    # A low diagnostic score activates WORKED_EXAMPLE scaffolding
    assert eval_res["selected_strategy"] == "WORKED_EXAMPLE"


@pytest.mark.asyncio
async def test_scenario_3_misconception_negation_trap(db_session):
    """
    Scenario 3: Misconception string-matching trap.
    Verifies that explicit negation ("NOT by free electrons") is NOT falsely flagged
    as a misconception and scores as correct.
    """
    ai = get_ai_provider()
    eval_result = await ai.evaluate_student_answer(
        question_prompt="Why does pure water not conduct electricity?",
        student_answer="In liquids current is carried by dissolved ions, and NOT by free electrons.",
        expected_concepts=["dissolved ions", "free charges"],
        required_points=["pure water has no ions"],
        misconception_traps={"electrons": "Belief that electrons flow freely in water"},
        curriculum_context="Pure water lacks ions. Dissolved salts create ions.",
    )

    # Negation boundary detection prevents false positive misconception flag
    assert eval_result.misconception_detected is None
    assert eval_result.is_correct is True


@pytest.mark.asyncio
async def test_scenario_4_lucky_answer_inflation(db_session):
    """
    Scenario 4: Lucky correct answer.
    Verifies that a single correct answer does NOT cause an unrealistic jump to 100% mastery.
    Empirical Bayes shrinkage damps the score appropriately (<= 0.40).
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
    # Damped Bayesian shrinkage prevents inflation to 100%:
    assert m1.mastery_score < 0.45
    assert m1.retention_stage == "EXPOSURE"


@pytest.mark.asyncio
async def test_scenario_5_high_confidence_incorrect_answer_unhandled(db_session):
    """
    Scenario 5: High confidence but incorrect answer.
    Verifies that the assessment engine flags DEEP remediation when a student
    with prior HIGH confidence answers incorrectly.
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
    # The evaluation output correctly flags deep remediation for confidently incorrect answers:
    assert res["remediation_depth"] == "DEEP"


@pytest.mark.asyncio
async def test_scenario_6_correct_answer_low_confidence_reinforcement(db_session):
    """
    Scenario 6: Correct answer with low confidence.
    Verifies that a correct answer with low evidence correctly flags reinforcement_needed.
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
    assert res["is_correct"] is True
    assert res["reinforcement_needed"] is True


@pytest.mark.asyncio
async def test_scenario_7_feynman_failure_reduces_mastery(db_session):
    """
    Scenario 7: Feynman failure impact on mastery.
    Verifies that failing the Feynman explanation decreases concept mastery score
    and unconfirms mastery.
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
    m.confirmed_mastery = True
    await db_session.commit()

    sess_data = await tutor_engine.start_lesson_session(student.id, concept.topic_id, concept.id)
    sess_id = sess_data["session_id"]

    res = await assessment_engine.evaluate_explain_it_back(
        session_id=sess_id,
        student_answer="I don't know what ions are at all.",
        concept_id=concept.id,
    )

    assert res["accurate"] is False
    await db_session.refresh(m)
    # Mastery must be penalized downward and unconfirmed
    assert m.mastery_score < 0.85
    assert m.confirmed_mastery is False


@pytest.mark.asyncio
async def test_scenario_8_voice_teach_does_not_force_transition_on_empty(db_session):
    """
    Scenario 8: Voice interaction behavior.
    Triggering VoiceMode.TEACH with an empty transcript does NOT advance session state.
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
    # Empty transcript must retain TEACHING state
    assert db_sess.state == "TEACHING"


@pytest.mark.asyncio
async def test_scenario_9_gemini_provider_real_methods(db_session):
    """
    Scenario 9: AI Provider architecture.
    GeminiProvider implements real Phase C methods and falls back safely on error.
    """
    gemini = GeminiProvider(api_key="fake_key_for_test")
    # Real methods exist and fall back properly to fallback provider
    resp = await gemini.generate_strategy_explanation(
        concept_name="Electrolytes",
        learning_objective="Understand conduction",
        curriculum_context="Context",
        strategy="FIRST_PRINCIPLES",
        student_name="Krish",
    )
    assert resp is not None
    assert len(resp.message) > 0


@pytest.mark.asyncio
async def test_scenario_10_xp_idempotency_farming(db_session):
    """
    Scenario 10: Idempotency hardening in award_xp.
    Repeated award_xp calls with the same item_key award 0 XP for duplicates.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    gamification = GamificationEngine(db_session)
    key = "unique-test-q-farming-99"

    res1 = await gamification.award_xp(student.id, 25, "First attempt", item_key=key)
    assert res1["awarded_xp"] == 25

    res2 = await gamification.award_xp(student.id, 25, "Second duplicate attempt", item_key=key)
    # Duplicate attempt is rejected with 0 XP!
    assert res2["awarded_xp"] == 0


@pytest.mark.asyncio
async def test_question_bank_diversity_and_levels(db_session):
    """
    Verifies that the seeded question bank contains at least 5 calibrated questions
    per concept across Bloom levels 1-5.
    """
    c_res = await db_session.execute(select(Concept))
    concepts = list(c_res.scalars().all())
    assert len(concepts) >= 2

    for concept in concepts:
        q_res = await db_session.execute(select(Question).where(Question.concept_id == concept.id))
        questions = list(q_res.scalars().all())
        assert len(questions) >= 5
        levels = {q.cognitive_level for q in questions}
        assert {1, 2, 3, 4, 5}.issubset(levels)


@pytest.mark.asyncio
async def test_session_resumption_prevents_duplication(db_session):
    """
    Verifies that calling start_lesson_session when an active session exists
    resumes the existing session rather than creating a duplicate row.
    """
    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    tutor = TutorEngine(db_session)
    sess1 = await tutor.start_lesson_session(student.id, concept.topic_id, concept.id)
    sess2 = await tutor.start_lesson_session(student.id, concept.topic_id, concept.id)

    assert sess1["session_id"] == sess2["session_id"]
