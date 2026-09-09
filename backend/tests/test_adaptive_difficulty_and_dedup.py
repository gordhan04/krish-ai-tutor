import pytest
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.models.user import Student
from app.models.curriculum import Topic, Concept
from app.models.learning import LearningSession, ConceptMastery
from sqlalchemy import select


@pytest.mark.asyncio
async def test_adaptive_question_deduplication(db_session):
    tutor_engine = TutorEngine(db_session)
    assessment_engine = AssessmentEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    t_res = await db_session.execute(select(Topic))
    topic = t_res.scalars().first()

    # Start session
    lesson = await tutor_engine.start_lesson_session(student_id=student.id, topic_id=topic.id)
    session_id = lesson["session_id"]
    concept_id = lesson["concept_id"]

    # 1. Fetch first adaptive question
    q1 = await assessment_engine.get_adaptive_question(
        topic_id=topic.id,
        concept_id=concept_id,
        mastery_score=0.20,
        session_id=session_id,
    )
    assert q1 is not None
    q1_id = q1.id

    # 2. Student attempts and answers first question
    eval1 = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=q1_id,
        student_answer="A",
        selected_option_key="A",
        session_id=session_id,
    )

    # Verify session recorded the attempted question
    s_stmt = select(LearningSession).where(LearningSession.id == session_id)
    session = (await db_session.execute(s_stmt)).scalars().first()
    assert q1_id in session.attempted_question_ids

    # 3. Fetch second adaptive question with same session_id
    q2 = await assessment_engine.get_adaptive_question(
        topic_id=topic.id,
        concept_id=concept_id,
        mastery_score=eval1["mastery_score"],
        session_id=session_id,
    )
    assert q2 is not None
    # Crucial deduplication invariant: q2 must not be the same question!
    assert q2.id != q1_id


@pytest.mark.asyncio
async def test_consecutive_correct_difficulty_stepup(db_session):
    assessment_engine = AssessmentEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()

    c_res = await db_session.execute(select(Concept))
    concept = c_res.scalars().first()

    # Create mastery with 0 consecutive correct
    m = await assessment_engine.mastery_engine.get_or_create_concept_mastery(student.id, concept.id)
    m.consecutive_correct_count = 0
    await db_session.commit()

    # Create dummy session to check step-up
    session = LearningSession(
        student_id=student.id,
        topic_id=concept.topic_id,
        state="PRACTICE",
        current_concept_id=concept.id,
        attempted_question_ids=[],
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Initial adaptive query (mastery 0.30 -> target levels [1, 2])
    q_initial = await assessment_engine.get_adaptive_question(
        topic_id=concept.topic_id,
        concept_id=concept.id,
        mastery_score=0.30,
        session_id=session.id,
    )
    assert q_initial is not None
    assert q_initial.cognitive_level in [1, 2]

    # Student scores 2 consecutive correct
    m.consecutive_correct_count = 2
    await db_session.commit()

    # With 2 consecutive correct, target levels step up to [2, 3]
    q_stepped = await assessment_engine.get_adaptive_question(
        topic_id=concept.topic_id,
        concept_id=concept.id,
        mastery_score=0.30,
        session_id=session.id,
    )
    assert q_stepped is not None
    assert q_stepped.cognitive_level in [2, 3]
