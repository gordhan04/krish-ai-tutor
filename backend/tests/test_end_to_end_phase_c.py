import pytest
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.services.mastery_engine import MasteryEngine
from app.models.user import Student
from app.models.curriculum import Topic, Concept
from app.models.assessment import Question
from app.models.learning import LearningSession, Misconception, ConceptMastery
from app.core.state_machine import TutorState
from sqlalchemy import select


@pytest.mark.asyncio
async def test_complete_14_step_adaptive_learning_loop(db_session):
    """
    Validates the complete 14-step Phase C Adaptive Learning & Retention Loop:
    Diagnostic -> Strategy Selection -> Explanation -> Socratic Check -> Reflection Evaluation
    -> Adaptive Practice -> Deduplication -> Misconception Trap -> Targeted Remediation
    -> Retest Success & Resolution -> Explain-It-Back (Feynman) -> Mastery Confirmation
    -> Observed Learning Gain & Stopping Condition -> Spaced Revision & Next Best Action
    """
    tutor_engine = TutorEngine(db_session)
    assessment_engine = AssessmentEngine(db_session)
    mastery_engine = MasteryEngine(db_session)

    s_res = await db_session.execute(select(Student))
    student = s_res.scalars().first()
    assert student is not None

    t_res = await db_session.execute(select(Topic))
    topic = t_res.scalars().first()
    assert topic is not None

    # Step 1: Start Lesson
    lesson = await tutor_engine.start_lesson_session(student_id=student.id, topic_id=topic.id)
    session_id = lesson["session_id"]
    concept_id = lesson["concept_id"]
    assert lesson["state"] == TutorState.TEACHING.value

    # Step 2: Diagnostic Pre-Test
    diag = await tutor_engine.run_diagnostic(session_id)
    assert diag["state"] == TutorState.DIAGNOSTIC.value
    assert diag["diagnostic_questions_count"] > 0

    # Step 3: Evaluate Diagnostic and Select Strategy
    diag_eval = await tutor_engine.evaluate_diagnostic(session_id, diagnostic_score=0.45)
    assert diag_eval["state"] == TutorState.TEACHING.value
    assert diag_eval["selected_strategy"] == "REAL_WORLD_EXAMPLE"

    # Step 4: Strategy-Calibrated Explanation
    assert len(lesson["message"]) > 50

    # Step 5: Socratic Check Posed
    socratic_res = await tutor_engine.check_socratic_understanding(session_id)
    assert socratic_res["state"] == TutorState.CHECKING_UNDERSTANDING.value
    assert len(socratic_res["socratic_question"]) > 10

    # Step 6: Student Socratic Reflection Evaluated
    soc_eval = await tutor_engine.evaluate_socratic_response(
        session_id=session_id,
        student_response="Because water has dissolved minerals that split into mobile charged particles.",
    )
    assert soc_eval["understanding_confirmed"] is True
    assert soc_eval["state"] == TutorState.PRACTICE.value

    # Step 7: Adaptive Practice Question (Calibrated)
    q1 = await assessment_engine.get_adaptive_question(
        topic_id=topic.id,
        concept_id=concept_id,
        mastery_score=0.40,
        session_id=session_id,
    )
    assert q1 is not None
    q1_id = q1.id

    # Step 8: Student answers correctly on Level 2 MCQ
    ans1 = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=q1_id,
        student_answer="",
        selected_option_key="A",
        session_id=session_id,
    )
    assert ans1["is_correct"] is True

    # Step 8b: Deduplication Check — Second adaptive question must be DIFFERENT
    q2 = await assessment_engine.get_adaptive_question(
        topic_id=topic.id,
        concept_id=concept_id,
        mastery_score=ans1["mastery_score"],
        session_id=session_id,
    )
    assert q2 is not None
    assert q2.id != q1_id

    # Step 9: Misconception Trap Triggered
    # Find subjective rubric question
    q_sub_stmt = select(Question).where(
        Question.concept_id == concept_id,
        Question.question_type == "rubric_explanation",
    )
    q_sub = (await db_session.execute(q_sub_stmt)).scalars().first()
    assert q_sub is not None

    trap_answer = "Electrons flow freely from the battery across the salt solution."
    ans2 = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=q_sub.id,
        student_answer=trap_answer,
        session_id=session_id,
    )
    assert ans2["misconception_detected"] is not None

    # Verify session entered REMEDIATION state
    sess_stmt = select(LearningSession).where(LearningSession.id == session_id)
    session = (await db_session.execute(sess_stmt)).scalars().first()
    assert session.state == TutorState.REMEDIATION.value

    # Step 10: Contrast Remediation Explanation
    misc_stmt = select(Misconception).where(
        Misconception.student_id == student.id,
        Misconception.concept_id == concept_id,
        Misconception.is_remediated == False,
    )
    misc = (await db_session.execute(misc_stmt)).scalars().first()
    assert misc is not None

    remedy = await tutor_engine.remediate_misconception(
        session_id=session_id,
        misconception_id=misc.id,
    )
    assert "remediation_message" in remedy
    assert len(remedy["remediation_message"]) > 40

    # Step 11: Retest Question -> Success & Misconception Resolved
    correct_retest = "Dissolved salts dissociate into ions which move through the liquid to conduct current."
    retest_ans = await assessment_engine.evaluate_answer(
        student_id=student.id,
        question_id=q_sub.id,
        student_answer=correct_retest,
        session_id=session_id,
    )
    assert retest_ans["is_correct"] is True
    assert retest_ans["retest_remediated"] is True

    await db_session.refresh(misc)
    assert misc.is_remediated is True
    assert misc.resolved_at is not None

    # Step 12: Explain-It-Back Synthesis (Feynman Technique)
    feynman_answer = (
        "Pure water cannot conduct electricity because it lacks charge carriers. "
        "When salt dissolves in water, it splits into positive sodium ions and negative chloride ions. "
        "These ions carry charge through the solution between the electrodes, completing the electrical circuit."
    )
    feynman_res = await assessment_engine.evaluate_explain_it_back(
        session_id=session_id,
        student_answer=feynman_answer,
        concept_id=concept_id,
    )
    assert feynman_res["accurate"] is True
    assert feynman_res["confirmed_mastery"] is True
    assert feynman_res["retention_stage"] == "INITIAL_MASTERY"
    assert feynman_res["xp_awarded"] > 0

    # Step 13: Check Mastery Completion & Stopping Condition
    # Ensure mastery score >= 0.75 for terminal completion
    m_record = await mastery_engine.get_or_create_concept_mastery(student.id, concept_id)
    m_record.mastery_score = 0.85
    m_record.confidence = "HIGH"
    await db_session.commit()

    completion = await tutor_engine.check_mastery_completion(session_id)
    assert completion["is_terminal"] is True
    assert completion["state"] == TutorState.CHAPTER_COMPLETE.value
    assert completion["learning_gain"] > 0
    assert "break" in completion["message"].lower() or "rest" in completion["message"].lower()

    # Step 14: Spaced Revision Scheduling & Next Best Action
    m_updated = await mastery_engine.get_or_create_concept_mastery(student.id, concept_id)
    assert m_updated.next_revision_at is not None

    next_action = await mastery_engine.calculate_next_best_action(student.id)
    assert next_action is not None
    assert "action_type" in next_action
    assert next_action["priority"] in ["HIGH", "MEDIUM", "NORMAL", "LOW"]
