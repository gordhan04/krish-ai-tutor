import pytest
import os
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.user import User, Student
from app.models.curriculum import CurriculumDocument, Chapter, Topic, Concept, ContentChunk
from app.models.learning import ConceptMastery
from app.services.curriculum_ingestion.pipeline import IngestionPipeline
from app.services.curriculum_ingestion.publisher import CurriculumPublisher
from app.services.tutor_engine import TutorEngine
from app.services.assessment_engine import AssessmentEngine
from app.services.ai.mock_provider import MockAIProvider
from tests.fixtures.ncert_pdf_generator import generate_class_8_combustion_textbook_pdf
from app.core.config import settings


@pytest.mark.asyncio
async def test_real_class_8_textbook_end_to_end_learning_cycle(db_session: AsyncSession):
    """
    Acceptance Test (Requirement 36):
    Upload NCERT Class 8 Science Chapter 4 (Combustion and Flame) ->
    Process -> Review -> Publish ->
    Krish starts lesson on new topic ->
    RAG retrieves grounded excerpts citing Page 1 / 2 ->
    Tutor provides explanation ->
    Adaptive practice question evaluated ->
    Mastery and evidence recorded in database.
    """
    db = db_session
    if True:
        # 1. Setup Student (Krish) and Admin
        u_stmt = select(User).where(User.role == "student")
        u_res = await db.execute(u_stmt)
        student_user = u_res.scalars().first()
        if not student_user:
            student_user = User(
                id=str(uuid.uuid4()),
                email="krish_e2e@test.com",
                hashed_password="hash",
                role="student",
            )
            db.add(student_user)
            await db.flush()

        s_stmt = select(Student).where(Student.user_id == student_user.id)
        s_res = await db.execute(s_stmt)
        student = s_res.scalars().first()
        if not student:
            student = Student(user_id=student_user.id, display_name="Krish", grade_level=8)
            db.add(student)
            await db.flush()

        # 2. Ingest NCERT Class 8 Chapter 4 PDF
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        pdf_bytes = generate_class_8_combustion_textbook_pdf()
        file_path = os.path.join(settings.UPLOAD_DIR, f"ncert_ch4_{uuid.uuid4().hex}.pdf")
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        doc = CurriculumDocument(
            id=str(uuid.uuid4()),
            original_filename="ncert_science_class8_chapter4.pdf",
            storage_path=file_path,
            file_size=len(pdf_bytes),
            content_hash=uuid.uuid4().hex,
            mime_type="application/pdf",
            status="UPLOADED",
            uploader_id=student_user.id,
        )
        db.add(doc)
        await db.commit()

        # 3. Process through Ingestion Pipeline
        ai_provider = MockAIProvider()
        pipeline = IngestionPipeline(db, ai_provider)
        ingested_doc = await pipeline.process_document(doc.id)
        assert ingested_doc.status == "READY_FOR_REVIEW"
        assert ingested_doc.page_count == 4

        # 4. Review & Publish
        await CurriculumPublisher.approve_document(db, doc.id)
        published_doc = await CurriculumPublisher.publish_document(db, doc.id)
        assert published_doc.status == "PUBLISHED"

        # 5. Verify Ingested Chapter and Topics are live
        ch_stmt = select(Chapter).where(Chapter.title.ilike("%Combustion%"))
        ch_res = await db.execute(ch_stmt)
        chapter = ch_res.scalars().first()
        assert chapter is not None
        assert chapter.chapter_number == 4
        assert chapter.status == "PUBLISHED"

        # Find Topic "WHAT IS COMBUSTION?"
        t_stmt = select(Topic).where(Topic.title.ilike("%COMBUSTION%"))
        t_res = await db.execute(t_stmt)
        topic = t_res.scalars().first()
        assert topic is not None
        assert topic.status == "PUBLISHED"

        # Find Concept
        c_stmt = select(Concept).where(Concept.topic_id == topic.id)
        c_res = await db.execute(c_stmt)
        concept = c_res.scalars().first()
        assert concept is not None

        # 6. Krish starts lesson via TutorEngine
        tutor = TutorEngine(db)
        lesson_data = await tutor.start_lesson_session(
            student_id=student.id,
            topic_id=topic.id,
            concept_id=concept.id,
        )

        assert lesson_data["state"] == "TEACHING"
        assert "combustion" in lesson_data["concept_name"].lower()
        assert len(lesson_data["curriculum_sources"]) > 0

        # Verify citation grounding
        first_source = lesson_data["curriculum_sources"][0]
        assert first_source["page"] >= 1

        # 7. Adaptive assessment on new concept
        assessment = AssessmentEngine(db)
        question = await assessment.get_adaptive_question(topic.id, concept.id)
        assert question is not None

        # 8. Student submits answer and gets evaluated
        if question.question_type in ("mcq", "true_false"):
            eval_result = await assessment.evaluate_answer(
                student_id=student.id,
                question_id=question.id,
                student_answer="",
                selected_option_key="A",
            )
        else:
            eval_result = await assessment.evaluate_answer(
                student_id=student.id,
                question_id=question.id,
                student_answer=f"{concept.name} is a chemical reaction involving oxygen and fuel that produces heat.",
            )

        assert eval_result["is_correct"] is True
        assert eval_result["score"] >= 0.7

        # 9. Verify ConceptMastery is updated with evidence depth
        m_stmt = select(ConceptMastery).where(
            ConceptMastery.student_id == student.id,
            ConceptMastery.concept_id == concept.id,
        )
        m_res = await db.execute(m_stmt)
        mastery = m_res.scalars().first()
        assert mastery is not None
        assert mastery.evidence_count >= 1
        assert mastery.mastery_score > 0.0
