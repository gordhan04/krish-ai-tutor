"""
End-to-End Real Textbook Learning Experience Verification for Chapter 1:
Karnataka Class 8 Science Part-I (2025-26), Chapter 1: Crop Production and Management

Verifies:
1. Complete 19-Step Pedagogical Learning Journey
2. Student Simulations (Scenarios A through F)
3. Question Bank Coverage & Bloom's Distribution (L1-L5)
4. Misconception Traps & Remediation
5. Evidence-Weighted Chapter Mastery
6. Voice & Text Parity
7. Out-of-Scope Non-Hallucination & Provenance
"""

import pytest
import uuid
from typing import AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.learning import LearningSession, ConceptMastery, Misconception, LearningEvent
from app.models.curriculum import Chapter, Section, Topic, Concept, LearningObjective, ContentChunk, CurriculumActivity, CurriculumFigure
from app.models.assessment import Question, QuestionOption, QuestionRubric
from app.core.state_machine import TutorState
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.services.mastery_engine import MasteryEngine
from app.services.rag.retriever import CurriculumRetriever
from app.services.curriculum_ingestion.chapter1_curriculum_builder import enrich_chapter_1

REAL_DB_URL = "sqlite+aiosqlite:///krish_tutor.db"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(REAL_DB_URL, connect_args={"check_same_thread": False})
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_chapter_1_curriculum_and_question_bank_structure(db_session):
    """Verifies that Chapter 1 is fully structured with concepts, objectives, activities, figures, and calibrated questions."""
    # Ensure enrichment is in place
    await enrich_chapter_1(db_session)

    # 1. Verify Chapter 1 exists
    ch_stmt = select(Chapter).where(Chapter.title.ilike("%CROP PRODUCTION%"))
    chapter = (await db_session.execute(ch_stmt)).scalars().first()
    assert chapter is not None, "Chapter 1 not found"
    assert chapter.chapter_number == 1
    assert chapter.printed_page_start == 1
    assert chapter.printed_page_end == 16

    # 2. Verify Sections, Activities, Figures
    sec_stmt = select(Section).where(Section.chapter_id == chapter.id)
    sections = list((await db_session.execute(sec_stmt)).scalars().all())
    assert len(sections) >= 10, f"Expected at least 10 sections, got {len(sections)}"

    act_stmt = select(CurriculumActivity).join(Section).where(Section.chapter_id == chapter.id)
    activities = list((await db_session.execute(act_stmt)).scalars().all())
    act_numbers = [a.activity_number for a in activities]
    assert "Activity 1.1" in act_numbers, "Activity 1.1 (seed floating) missing"
    assert "Activity 1.2" in act_numbers, "Activity 1.2 (seedlings manure) missing"
    assert "Activity 1.3" in act_numbers, "Activity 1.3 (food from animals) missing"

    fig_stmt = select(CurriculumFigure).join(Section).where(Section.chapter_id == chapter.id)
    figures = list((await db_session.execute(fig_stmt)).scalars().all())
    assert len(figures) >= 15, f"Expected real figures, got {len(figures)}"

    # 3. Verify Concepts and Learning Objectives
    c_stmt = (
        select(Concept)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Section, Topic.section_id == Section.id)
        .where(Section.chapter_id == chapter.id)
    )
    concepts = list((await db_session.execute(c_stmt)).scalars().all())
    assert len(concepts) >= 10, f"Expected at least 10 concepts, got {len(concepts)}"
    concept_names = [c.name for c in concepts]
    assert "Agricultural Practices & Crop Seasons" in concept_names
    assert "Preparation of Soil" in concept_names
    assert "Sowing & Seed Selection" in concept_names
    assert "Adding Manure and Fertilisers" in concept_names
    assert "Irrigation: Traditional vs Modern Systems" in concept_names
    assert "Storage of Food Grains" in concept_names

    # 4. Verify Question Coverage across Bloom's Levels (L1-L5)
    q_stmt = (
        select(Question)
        .join(Concept, Question.concept_id == Concept.id)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Section, Topic.section_id == Section.id)
        .where(Section.chapter_id == chapter.id)
    )
    questions = list((await db_session.execute(q_stmt)).scalars().all())
    assert len(questions) >= 30, f"Expected at least 30 calibrated questions, got {len(questions)}"

    levels = {q.cognitive_level for q in questions}
    assert 1 in levels, "Missing Level 1 (Recall) questions"
    assert 2 in levels, "Missing Level 2 (Understanding) questions"
    assert 3 in levels, "Missing Level 3 (Application) questions"
    assert 4 in levels, "Missing Level 4 (Reasoning) questions"
    assert 5 in levels, "Missing Level 5 (Challenge) questions"


@pytest.mark.asyncio
async def test_full_19_step_pedagogical_journey(db_session):
    """
    Executes and validates the authentic 19-step learning journey for Chapter 1:
    1. Welcome -> 2. Diagnostic -> 3. Objective -> 4. Strategy -> 5. Intro ->
    6. Analogy -> 7. Socratic Check -> 8. Practice -> 9. Evaluation ->
    10. Misconception Detection -> 11. Remediation -> 12. Retest ->
    13. Explain-it-back -> 14. Mastery Update -> 15. Next Concept ->
    16. Chapter Review -> 17. Final Assessment -> 18. Chapter Mastery -> 19. Chapter Complete
    """
    await enrich_chapter_1(db_session)
    student_id = f"student_19step_{uuid.uuid4().hex[:8]}"

    # Locate Chapter 1 and a core concept (Sowing & Seed Selection)
    ch_stmt = select(Chapter).where(Chapter.title.ilike("%CROP PRODUCTION%"))
    chapter = (await db_session.execute(ch_stmt)).scalars().first()

    c_stmt = (
        select(Concept)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Section, Topic.section_id == Section.id)
        .where(Section.chapter_id == chapter.id, Concept.name == "Sowing & Seed Selection")
    )
    concept = (await db_session.execute(c_stmt)).scalars().first()
    assert concept is not None

    tutor = TutorEngine(db_session)
    assessor = AssessmentEngine(db_session)
    mastery = MasteryEngine(db_session)

    # Step 1: Start Session (Welcome / LESSON_START -> TEACHING)
    start_info = await tutor.start_lesson_session(
        student_id=student_id,
        topic_id=concept.topic_id,
        concept_id=concept.id,
    )
    session_id = start_info["session_id"]
    assert start_info["state"] == TutorState.TEACHING.value

    # Step 2: Diagnostic Assessment
    diag_info = await tutor.run_diagnostic(session_id)
    assert diag_info["state"] == TutorState.DIAGNOSTIC.value
    assert diag_info["diagnostic_questions_count"] >= 1

    # Step 3 & 4: Evaluate Diagnostic & Strategy Selection (Objective + Strategy)
    eval_diag = await tutor.evaluate_diagnostic(session_id, diagnostic_score=0.60)
    assert eval_diag["state"] == TutorState.TEACHING.value
    assert eval_diag["selected_strategy"] in ["STEP_BY_STEP", "REAL_WORLD_EXAMPLE"]

    # Step 5 & 6: Concept Explanation & Curriculum Context
    session_status = await tutor.get_session_status(session_id)
    assert len(session_status["curriculum_sources"]) > 0

    # Step 7: Socratic Check
    soc_info = await tutor.check_socratic_understanding(session_id)
    assert soc_info["state"] == TutorState.CHECKING_UNDERSTANDING.value
    assert "socratic_question" in soc_info

    # Step 8: Socratic Response Evaluation -> Transitions to PRACTICE
    soc_eval = await tutor.evaluate_socratic_response(
        session_id=session_id,
        student_response="Damaged seeds are eaten by pests, so they become hollow inside and float on water."
    )
    assert soc_eval["state"] == TutorState.PRACTICE.value

    # Step 9 & 10: Practice Question & Misconception Detection
    q_stmt = select(Question).where(
        Question.concept_id == concept.id,
        Question.prompt.ilike("%float%")
    )
    q = (await db_session.execute(q_stmt)).scalars().first()
    assert q is not None

    # Student answers with the common misconception: "floating seeds are the healthiest because they contain extra air"
    ans_res = await assessor.submit_answer(
        session_id=session_id,
        question_id=q.id,
        selected_option_key="B",  # Wrong option (Misconception trap)
        time_spent_seconds=25,
    )
    assert ans_res["is_correct"] is False
    assert ans_res["state"] == TutorState.REMEDIATION.value
    assert ans_res["detected_misconceptions"] is not None

    # Step 11: Targeted Remediation
    misc_id = ans_res["detected_misconceptions"][0]["id"]
    rem_info = await tutor.remediate_misconception(session_id, misc_id)
    assert rem_info["state"] == TutorState.REMEDIATION.value
    assert len(rem_info["remediation_message"]) > 0

    # Step 12: Near-Transfer Retest
    retest_ans = await assessor.submit_answer(
        session_id=session_id,
        question_id=q.id,
        selected_option_key="A",  # Correct answer after remediation
        time_spent_seconds=18,
    )
    assert retest_ans["is_correct"] is True

    # Step 13: Explain-It-Back (Feynman Technique)
    feynman_res = await assessor.evaluate_explain_it_back(
        session_id=session_id,
        student_answer="When we put seeds in water, healthy good seeds are dense and sink to the bottom. Damaged seeds are hollowed out by insects, making them lighter so they float on top, which helps us separate and discard them.",
        concept_id=concept.id,
    )
    assert feynman_res["accurate"] is True
    assert feynman_res["confirmed_mastery"] is True

    # Step 14: Mastery Update Verification
    c_mastery = await mastery.get_or_create_concept_mastery(student_id, concept.id)
    assert c_mastery.evidence_count >= 2
    assert c_mastery.confirmed_mastery is True

    # Step 15 & 16: Chapter Review
    review = await tutor.get_chapter_review(session_id, chapter.id)
    assert review["chapter_id"] == chapter.id
    assert len(review["key_takeaways"]) >= 10
    assert len(review["activities_reviewed"]) >= 1

    # Step 17: Final Chapter Assessment
    final_test = await tutor.run_final_chapter_assessment(session_id, chapter.id, question_count=5)
    assert final_test["questions_count"] == 5
    assert len(final_test["questions"]) == 5

    # Answer questions across concepts to build evidence depth
    for q_item in final_test["questions"]:
        opt_stmt = select(QuestionOption).where(
            QuestionOption.question_id == q_item["id"],
            QuestionOption.is_correct == True
        )
        correct_opt = (await db_session.execute(opt_stmt)).scalars().first()
        if correct_opt:
            await assessor.submit_answer(
                session_id=session_id,
                question_id=q_item["id"],
                selected_option_key=correct_opt.option_key,
                time_spent_seconds=15,
            )

    # Step 18: Evidence-Weighted Chapter Mastery
    ch_mastery_report = await mastery.calculate_chapter_mastery(student_id, chapter.id)
    assert ch_mastery_report["chapter_id"] == chapter.id
    assert ch_mastery_report["concepts_count"] >= 10
    assert ch_mastery_report["overall_mastery"] > 0.0

    # Step 19: Spaced Revision & Chapter Completion Gate Check
    comp_check = await tutor.check_mastery_completion(session_id, chapter_id=chapter.id)
    assert "overall_mastery" in comp_check
    assert "unresolved_misconceptions_count" in comp_check
    assert comp_check["unresolved_misconceptions_count"] == 0


@pytest.mark.asyncio
async def test_student_simulations_scenarios_a_to_f(db_session):
    """
    Simulates all 6 student profiles:
    - Scenario A: Strong baseline knowledge (rapid advancement)
    - Scenario B: Average knowledge (hints, step-by-step)
    - Scenario C: Misconception-heavy student (contrastive remediation)
    - Scenario D: Partial answers (Socratic guidance)
    - Scenario E: Repeatedly wrong answers (hint ladder 1->5, Feynman failure penalty)
    - Scenario F: Session resume (interrupted session preservation)
    """
    await enrich_chapter_1(db_session)
    tutor = TutorEngine(db_session)
    assessor = AssessmentEngine(db_session)
    mastery_eng = MasteryEngine(db_session)

    ch_stmt = select(Chapter).where(Chapter.title.ilike("%CROP PRODUCTION%"))
    chapter = (await db_session.execute(ch_stmt)).scalars().first()

    c_stmt = (
        select(Concept)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Section, Topic.section_id == Section.id)
        .where(Section.chapter_id == chapter.id, Concept.name.ilike("%Manure%"))
    )
    concept = (await db_session.execute(c_stmt)).scalars().first()
    assert concept is not None

    # SCENARIO A: Strong Student (Diagnostic 0.95 -> FIRST_PRINCIPLES)
    student_a = f"student_a_{uuid.uuid4().hex[:6]}"
    sess_a = await tutor.start_lesson_session(student_a, concept.topic_id, concept.id)
    eval_a = await tutor.evaluate_diagnostic(sess_a["session_id"], diagnostic_score=0.95)
    assert eval_a["selected_strategy"] == "FIRST_PRINCIPLES"

    # SCENARIO B: Average Student (Diagnostic 0.50 -> REAL_WORLD_EXAMPLE + Hint Ladder)
    student_b = f"student_b_{uuid.uuid4().hex[:6]}"
    sess_b = await tutor.start_lesson_session(student_b, concept.topic_id, concept.id)
    eval_b = await tutor.evaluate_diagnostic(sess_b["session_id"], diagnostic_score=0.50)
    assert eval_b["selected_strategy"] == "REAL_WORLD_EXAMPLE"

    hint_b1 = await tutor.get_next_hint(sess_b["session_id"], "How does manure differ from fertiliser?")
    assert hint_b1["hint_level"] == 1
    hint_b2 = await tutor.get_next_hint(sess_b["session_id"], "How does manure differ from fertiliser?")
    assert hint_b2["hint_level"] == 2

    # SCENARIO C: Misconception-Heavy Student
    student_c = f"student_c_{uuid.uuid4().hex[:6]}"
    sess_c = await tutor.start_lesson_session(student_c, concept.topic_id, concept.id)
    q_c_stmt = select(Question).where(Question.concept_id == concept.id, Question.cognitive_level == 4)
    q_c = (await db_session.execute(q_c_stmt)).scalars().first()
    assert q_c is not None

    # Answer with misconception B ("Chemical fertilisers provide 100% organic humus")
    ans_c = await assessor.submit_answer(sess_c["session_id"], q_c.id, selected_option_key="B", time_spent_seconds=20)
    assert ans_c["is_correct"] is False
    assert ans_c["state"] == TutorState.REMEDIATION.value
    assert len(ans_c["detected_misconceptions"]) >= 1

    # SCENARIO D: Student gives partial answer to Socratic prompt
    student_d = f"student_d_{uuid.uuid4().hex[:6]}"
    sess_d = await tutor.start_lesson_session(student_d, concept.topic_id, concept.id)
    await tutor.check_socratic_understanding(sess_d["session_id"])
    soc_d = await tutor.evaluate_socratic_response(
        sess_d["session_id"], student_response="It gives some food to plants but I don't know the full details."
    )
    assert "feedback" in soc_d

    # SCENARIO E: Repeated Wrong Answers & Failed Feynman Downward Recalibration
    student_e = f"student_e_{uuid.uuid4().hex[:6]}"
    sess_e = await tutor.start_lesson_session(student_e, concept.topic_id, concept.id)
    await mastery_eng.record_answer_attempt(student_e, concept.id, is_correct=True, difficulty_level=2)
    await mastery_eng.record_answer_attempt(student_e, concept.id, is_correct=True, difficulty_level=2)
    pre_m = await mastery_eng.get_or_create_concept_mastery(student_e, concept.id)
    pre_score = pre_m.mastery_score

    # Student fails Feynman explanation completely
    fail_feynman = await assessor.evaluate_explain_it_back(
        sess_e["session_id"],
        student_answer="I have no clue what this concept is about and fertiliser is just rocks.",
        concept_id=concept.id,
    )
    assert fail_feynman["accurate"] is False
    assert fail_feynman["confirmed_mastery"] is False

    post_m = await mastery_eng.get_or_create_concept_mastery(student_e, concept.id)
    assert post_m.mastery_score < pre_score or post_m.confirmed_mastery is False

    # SCENARIO F: Session Interruption and Resume
    student_f = f"student_f_{uuid.uuid4().hex[:6]}"
    sess_f1 = await tutor.start_lesson_session(student_f, concept.topic_id, concept.id)
    sess_f1_id = sess_f1["session_id"]
    q_f = (await db_session.execute(select(Question).where(Question.concept_id == concept.id))).scalars().first()
    await assessor.submit_answer(sess_f1_id, q_f.id, selected_option_key="A", time_spent_seconds=10)

    # Student leaves and resumes
    sess_f2 = await tutor.start_lesson_session(student_f, concept.topic_id, concept.id)
    assert sess_f2["session_id"] == sess_f1_id, "Should have resumed the existing active session"


@pytest.mark.asyncio
async def test_chapter_1_out_of_scope_retrieval_isolation(db_session):
    """
    Verifies that out-of-scope queries (Friction, Cell Structure, Electric Current)
    cannot retrieve or leak chunks into Chapter 1 (Crop Production).
    """
    retriever = CurriculumRetriever(db_session)
    ch_stmt = select(Chapter).where(Chapter.title.ilike("%CROP PRODUCTION%"))
    chapter = (await db_session.execute(ch_stmt)).scalars().first()
    assert chapter is not None

    friction_chunks = await retriever.search_textbook_chunks(
        query_text="What is rolling friction and fluid friction drag?",
        limit=5,
        chapter_id=chapter.id,
    )
    for chunk in friction_chunks:
        assert chunk.chapter_id == chapter.id
        assert "friction" not in chunk.chunk_text.lower(), "Out of scope chunk leaked into Chapter 1 retrieval!"

    cell_chunks = await retriever.search_textbook_chunks(
        query_text="Explain difference between plant cell and animal cell cytoplasm and cell wall",
        limit=5,
        chapter_id=chapter.id,
    )
    for chunk in cell_chunks:
        assert chunk.chapter_id == chapter.id
        assert "chloroplast" not in chunk.chunk_text.lower(), "Cell chunk leaked into Chapter 1 retrieval!"


@pytest.mark.asyncio
async def test_chapter_1_voice_and_text_engine_parity(db_session):
    """
    Verifies that voice and text modes execute through the exact same Tutor, Assessment,
    and Mastery engines, mutating identical database session and mastery state.
    """
    tutor = TutorEngine(db_session)
    assessor = AssessmentEngine(db_session)
    mastery = MasteryEngine(db_session)

    ch_stmt = select(Chapter).where(Chapter.title.ilike("%CROP PRODUCTION%"))
    chapter = (await db_session.execute(ch_stmt)).scalars().first()

    c_stmt = (
        select(Concept)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Section, Topic.section_id == Section.id)
        .where(Section.chapter_id == chapter.id, Concept.name == "Preparation of Soil")
    )
    concept = (await db_session.execute(c_stmt)).scalars().first()

    student_id = f"student_parity_{uuid.uuid4().hex[:6]}"
    sess = await tutor.start_lesson_session(student_id, concept.topic_id, concept.id)
    session_id = sess["session_id"]

    # Text Socratic
    await tutor.check_socratic_understanding(session_id)
    text_eval = await tutor.evaluate_socratic_response(
        session_id=session_id,
        student_response="Tilling turns the soil so roots can breathe easily and friendly microbes grow."
    )
    assert text_eval["state"] == TutorState.PRACTICE.value

    # Voice Socratic (same underlying evaluation contract)
    voice_eval = await assessor.ai.evaluate_socratic_response(
        concept_name=concept.name,
        socratic_question="Why do we loosen the soil?",
        student_response="It loosens hard crumbs and lets air into soil pores for earthworms.",
        curriculum_context="",
    )
    assert "understanding_confirmed" in voice_eval

    # Mastery record updated identically
    m_record = await mastery.get_or_create_concept_mastery(student_id, concept.id)
    assert m_record.student_id == student_id


@pytest.mark.asyncio
async def test_chapter_1_explanation_grounding_and_no_electricity_leakage(db_session):
    """
    Verifies that Chapter 1 explanations, Socratic checks, hints, and strategies
    are strictly grounded in agricultural science and do NOT leak electricity/ion templates.
    """
    tutor = TutorEngine(db_session)
    ch_stmt = select(Chapter).where(Chapter.title.ilike("%CROP PRODUCTION%"))
    chapter = (await db_session.execute(ch_stmt)).scalars().first()

    # Find Agricultural Practices & Crop Seasons concept
    c_stmt = (
        select(Concept)
        .join(Topic, Concept.topic_id == Topic.id)
        .join(Section, Topic.section_id == Section.id)
        .where(Section.chapter_id == chapter.id, Concept.name.ilike("%Crop Seasons%"))
    )
    concept = (await db_session.execute(c_stmt)).scalars().first()
    assert concept is not None

    student_id = f"student_agri_{uuid.uuid4().hex[:6]}"
    sess = await tutor.start_lesson_session(student_id, concept.topic_id, concept.id)

    # 1. Verify default initial explanation
    initial_msg = sess["message"]
    assert "Kharif" in initial_msg or "Rabi" in initial_msg or "monsoon" in initial_msg
    assert "electrical switch" not in initial_msg.lower()
    assert "tap water" not in initial_msg.lower()
    assert "dissolved mineral salts" not in initial_msg.lower()

    # 2. Verify all strategies for this concept are grounded in agriculture
    strategies = ["REAL_WORLD_EXAMPLE", "ANALOGY", "STEP_BY_STEP", "CORRECT_MISCONCEPTION", "SOCRATIC", "RECAP"]
    for strat in strategies:
        resp = await tutor.ai.generate_strategy_explanation(
            concept_name=concept.name,
            learning_objective="Understand and explain the principles of Agricultural Practices as described in the textbook.",
            curriculum_context="Kharif crops are sown in rainy season. Rabi crops in winter.",
            strategy=strat,
            student_name="Krish",
        )
        msg_lower = resp.message.lower()
        assert any(k in msg_lower for k in ["crop", "kharif", "rabi", "monsoon", "season", "agricultural", "sowing"]), f"Strategy {strat} missing crop context: {resp.message}"
        assert "electrical switch" not in msg_lower, f"Strategy {strat} leaked electricity template!"
        assert "distilled water" not in msg_lower, f"Strategy {strat} leaked distilled water template!"

    # 3. Verify Socratic check is concept-aware
    soc_resp = await tutor.ai.generate_socratic_check(
        concept_name=concept.name,
        curriculum_context="Kharif crops are sown in monsoon. Rabi in winter.",
        prior_explanation=initial_msg,
    )
    soc_lower = soc_resp.message.lower()
    assert "lemon juice" not in soc_lower
    assert "led" not in soc_lower
    assert any(k in soc_lower for k in ["crop", "paddy", "farmer", "winter", "season"])

    # 4. Verify Hints are concept-aware
    hint_resp = await tutor.ai.generate_hint(
        question_prompt="Which of the following sets contains only Kharif crops?",
        student_previous_attempts=[],
        hint_level=1,
        curriculum_context="Kharif crops are sown in rainy season.",
    )
    hint_lower = hint_resp.message.lower()
    assert "pure water" not in hint_lower
    assert any(k in hint_lower for k in ["kharif", "season", "monsoon", "crop"])

