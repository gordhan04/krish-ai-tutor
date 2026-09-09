from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import Concept, ContentChunk
from app.models.assessment import Question, QuestionOption, QuestionRubric
from app.services.ai.base import AIProvider


class CurriculumQuestionGenerator:
    """
    Generates grounded candidate questions (MCQ & Rubric-based) from concepts.
    Keeps questions in draft mode until published.
    """

    def __init__(self, db: AsyncSession, ai_provider: AIProvider):
        self.db = db
        self.ai_provider = ai_provider

    async def generate_questions_for_concepts(
        self,
        concepts: List[Concept],
        chunks: List[ContentChunk],
    ) -> int:
        """
        Generates candidate questions based on concepts and supporting chunks.
        Returns the count of generated questions.
        """
        generated_count = 0
        chunk_map = {c.concept_id: c for c in chunks if c.concept_id}

        for concept in concepts:
            chunk = chunk_map.get(concept.id)
            source_text = chunk.chunk_text if chunk else concept.summary
            source_page = chunk.page_number if chunk else 1

            try:
                candidates = await self.ai_provider.generate_candidate_questions(
                    concept_name=concept.name,
                    concept_summary=concept.summary,
                    source_text=source_text,
                )

                for q_data in candidates:
                    q_obj = Question(
                        topic_id=concept.topic_id or "",
                        concept_id=concept.id,
                        question_type=q_data.get("question_type", "mcq"),
                        cognitive_level=q_data.get("cognitive_level", 2),
                        prompt=q_data.get("prompt", ""),
                        explanation=q_data.get("explanation", ""),
                        source_page=source_page,
                        source_type="generated_practice",
                        is_published=False,  # Kept in draft until reviewed
                    )
                    self.db.add(q_obj)
                    await self.db.flush()

                    if q_data.get("question_type") == "mcq" and "options" in q_data:
                        for opt in q_data["options"]:
                            option = QuestionOption(
                                question_id=q_obj.id,
                                option_key=opt.get("option_key", "A"),
                                option_text=opt.get("option_text", ""),
                                is_correct=opt.get("is_correct", False),
                                feedback=opt.get("feedback", ""),
                            )
                            self.db.add(option)

                    elif q_data.get("question_type") == "rubric_explanation" and "rubric" in q_data:
                        r_data = q_data["rubric"]
                        rubric = QuestionRubric(
                            question_id=q_obj.id,
                            expected_concepts=r_data.get("expected_concepts", []),
                            required_points=r_data.get("required_points", []),
                            misconception_traps=r_data.get("misconception_traps", {}),
                            max_score=r_data.get("max_score", 1.0),
                        )
                        self.db.add(rubric)

                    generated_count += 1
            except Exception:
                # Failure isolation: generated question errors never destroy the extracted curriculum
                continue

        await self.db.flush()
        return generated_count
