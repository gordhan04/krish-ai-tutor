from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.learning import ConceptMastery, LearningEvent


class MasteryEngine:
    """
    Deterministic Knowledge & Mastery Engine.
    Tracks mastery score alongside statistical confidence and evidence count.
    Prevents premature declarations of mastery on small sample sizes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_concept_mastery(
        self, student_id: str, concept_id: str
    ) -> ConceptMastery:
        stmt = select(ConceptMastery).where(
            ConceptMastery.student_id == student_id,
            ConceptMastery.concept_id == concept_id,
        )
        result = await self.db.execute(stmt)
        record = result.scalars().first()

        if not record:
            record = ConceptMastery(
                student_id=student_id,
                concept_id=concept_id,
                mastery_score=0.0,
                evidence_count=0,
                confidence="LOW",
                difficulty_exposure=1,
                total_attempts=0,
                correct_attempts=0,
                recent_accuracy=0.0,
                historical_accuracy=0.0,
                last_studied_at=datetime.now(timezone.utc),
            )
            self.db.add(record)
            await self.db.flush()

        return record

    def calculate_confidence(
        self, evidence_count: int, recent_accuracy: float, historical_accuracy: float, max_difficulty: int
    ) -> str:
        """
        Determines statistical confidence tier:
        - evidence_count < 3: Always LOW (cannot scientifically claim mastery)
        - 3 <= evidence_count <= 6: MEDIUM if variance between recent and historical is small
        - evidence_count > 6: HIGH if tested on application or challenge difficulty
        """
        if evidence_count < 3:
            return "LOW"
        elif evidence_count <= 6:
            variance = abs(recent_accuracy - historical_accuracy)
            return "MEDIUM" if variance <= 0.30 else "LOW"
        else:
            return "HIGH" if max_difficulty >= 3 else "MEDIUM"

    async def record_answer_attempt(
        self,
        student_id: str,
        concept_id: str,
        is_correct: bool,
        difficulty_level: int = 2,
    ) -> ConceptMastery:
        mastery = await self.get_or_create_concept_mastery(student_id, concept_id)

        mastery.total_attempts += 1
        mastery.evidence_count += 1
        if is_correct:
            mastery.correct_attempts += 1

        # Track difficulty exposure
        if difficulty_level > mastery.difficulty_exposure:
            mastery.difficulty_exposure = difficulty_level

        # Historical accuracy
        mastery.historical_accuracy = round(
            mastery.correct_attempts / mastery.total_attempts, 2
        )

        # Recent accuracy: exponential smoothing with alpha = 0.35
        attempt_val = 1.0 if is_correct else 0.0
        if mastery.total_attempts == 1:
            mastery.recent_accuracy = attempt_val
        else:
            mastery.recent_accuracy = round(
                0.35 * attempt_val + 0.65 * mastery.recent_accuracy, 2
            )

        # Cognitive difficulty multiplier
        difficulty_multiplier = 0.7 + (difficulty_level * 0.1)

        # Combined raw mastery score
        raw_score = (
            0.60 * mastery.recent_accuracy + 0.40 * mastery.historical_accuracy
        ) * difficulty_multiplier

        mastery.mastery_score = round(min(1.0, max(0.0, raw_score)), 2)

        # Calculate Confidence Tier based on evidence depth
        mastery.confidence = self.calculate_confidence(
            evidence_count=mastery.evidence_count,
            recent_accuracy=mastery.recent_accuracy,
            historical_accuracy=mastery.historical_accuracy,
            max_difficulty=mastery.difficulty_exposure,
        )

        now = datetime.now(timezone.utc)
        mastery.last_assessed_at = now
        mastery.last_studied_at = now

        # Calculate Spaced Repetition Revision Interval
        if mastery.mastery_score >= 0.85 and mastery.confidence in ["MEDIUM", "HIGH"]:
            interval_days = 7
        elif mastery.mastery_score >= 0.60:
            interval_days = 3
        elif mastery.mastery_score >= 0.40:
            interval_days = 1
        else:
            interval_days = 0  # Same-day review needed

        mastery.next_revision_at = now + timedelta(days=interval_days)

        await self.db.commit()
        await self.db.refresh(mastery)
        return mastery
