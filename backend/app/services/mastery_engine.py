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
                retention_stage="EXPOSURE",
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
            mastery.consecutive_correct_count = (mastery.consecutive_correct_count or 0) + 1
        else:
            mastery.consecutive_correct_count = 0

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

        # Cognitive difficulty multiplier: Level 1=0.80, Level 2=0.90, Level 3=1.00, Level 4=1.10, Level 5=1.20
        difficulty_factor = 0.70 + (difficulty_level * 0.10)

        # Evidence-Damped Empirical Bayes Shrinkage Formula
        # Prior parameters: K_prior = 1.7, baseline_mastery = 0.10
        # Prevents lucky-answer inflation on low sample sizes
        k_prior = 1.7
        m_baseline = 0.10
        observed_accuracy = 0.60 * mastery.recent_accuracy + 0.40 * mastery.historical_accuracy
        effective_evidence = min(float(mastery.evidence_count), 10.0)

        prior_mastery = mastery.mastery_score or 0.0
        bayesian_mastery = (
            (k_prior * m_baseline) + (effective_evidence * observed_accuracy * difficulty_factor)
        ) / (k_prior + effective_evidence)

        if is_correct and prior_mastery >= 0.70:
            mastery.mastery_score = round(min(1.0, max(bayesian_mastery, prior_mastery)), 2)
        else:
            mastery.mastery_score = round(min(1.0, max(0.0, bayesian_mastery)), 2)

        # Calculate Confidence Tier based on evidence depth
        mastery.confidence = self.calculate_confidence(
            evidence_count=mastery.evidence_count,
            recent_accuracy=mastery.recent_accuracy,
            historical_accuracy=mastery.historical_accuracy,
            max_difficulty=mastery.difficulty_exposure,
        )

        # Retention Stage Updates (Gated by evidence depth and confirmed mastery)
        if mastery.mastery_score >= 0.70:
            if getattr(mastery, "confirmed_mastery", False):
                mastery.retention_stage = "RETAINED_MASTERY"
            else:
                mastery.retention_stage = "INITIAL_MASTERY"
        elif mastery.evidence_count >= 3:
            mastery.retention_stage = "DEVELOPING"
        else:
            mastery.retention_stage = "EXPOSURE"

        now = datetime.now(timezone.utc)
        mastery.last_assessed_at = now
        mastery.last_studied_at = now

        # Calculate Spaced Repetition Revision Interval based on Retention Stage & Mastery
        if mastery.retention_stage == "RETAINED_MASTERY":
            interval_days = 14 if mastery.mastery_score >= 0.65 else 7
        elif mastery.retention_stage == "INITIAL_MASTERY":
            interval_days = 3 if mastery.mastery_score >= 0.60 else 1
        elif mastery.mastery_score >= 0.60:
            interval_days = 2
        elif mastery.mastery_score >= 0.40:
            interval_days = 1
        else:
            interval_days = 0  # Same-day review needed

        mastery.next_revision_at = now + timedelta(days=interval_days)

        await self.db.commit()
        await self.db.refresh(mastery)
        return mastery

    async def recalibrate_on_feynman_failure(self, student_id: str, concept_id: str) -> ConceptMastery:
        """
        Recalibrates mastery downward when a student fails the Feynman explain-it-back test.
        Penalizes mastery score, unconfirms mastery, and downgrades retention stage.
        """
        mastery = await self.get_or_create_concept_mastery(student_id, concept_id)
        mastery.confirmed_mastery = False
        mastery.mastery_score = round(max(0.15, mastery.mastery_score - 0.15), 2)
        mastery.recent_accuracy = round(max(0.20, mastery.recent_accuracy * 0.75), 2)
        if mastery.retention_stage in ["INITIAL_MASTERY", "RETAINED_MASTERY"]:
            mastery.retention_stage = "DEVELOPING"

        now = datetime.now(timezone.utc)
        mastery.last_assessed_at = now
        mastery.next_revision_at = now + timedelta(days=1)
        await self.db.commit()
        await self.db.refresh(mastery)
        return mastery

    async def calculate_next_best_action(self, student_id: str) -> Dict[str, Any]:
        """
        Calculates the single highest-yield next learning action for the student:
        1. Remediate active misconceptions (High priority)
        2. Spaced revision for concepts due (Medium priority)
        3. Strengthen weak concepts (< 50% mastery) (Medium priority)
        4. Resume active unfinished learning session (Normal priority)
        5. Continue curriculum progression / Challenge (Normal priority)
        """
        from app.models.learning import Misconception, LearningSession
        from app.models.curriculum import Concept

        # 1. Active Misconceptions
        misc_stmt = (
            select(Misconception)
            .where(
                Misconception.student_id == student_id,
                Misconception.is_remediated == False,
            )
            .order_by(Misconception.occurrence_count.desc(), Misconception.last_detected_at.desc())
        )
        misc_res = await self.db.execute(misc_stmt)
        active_misc = misc_res.scalars().first()
        if active_misc:
            c_res = await self.db.execute(select(Concept).where(Concept.id == active_misc.concept_id))
            concept = c_res.scalars().first()
            c_name = concept.name if concept else "Science Concept"
            return {
                "action_type": "REMEDIATE_MISCONCEPTION",
                "priority": "HIGH",
                "title": f"Clear Up Misconception in {c_name}",
                "description": f"Targeted review: {active_misc.misconception_text}",
                "concept_id": active_misc.concept_id,
                "misconception_id": active_misc.id,
                "reason": f"Detected {active_misc.occurrence_count} time(s) during practice.",
            }

        # 2. Spaced Revision Due
        now = datetime.now(timezone.utc)
        rev_stmt = (
            select(ConceptMastery)
            .where(
                ConceptMastery.student_id == student_id,
                ConceptMastery.next_revision_at <= now,
                ConceptMastery.mastery_score >= 0.40,
            )
            .order_by(ConceptMastery.next_revision_at.asc())
        )
        rev_res = await self.db.execute(rev_stmt)
        rev_due = rev_res.scalars().first()
        if rev_due:
            c_res = await self.db.execute(select(Concept).where(Concept.id == rev_due.concept_id))
            concept = c_res.scalars().first()
            c_name = concept.name if concept else "Learned Concept"
            return {
                "action_type": "SPACED_REVISION",
                "priority": "MEDIUM",
                "title": f"Spaced Revision: {c_name}",
                "description": "Quick 5-minute review to retain concept before memory decays.",
                "concept_id": rev_due.concept_id,
                "reason": f"Last studied on {rev_due.last_studied_at.strftime('%b %d') if rev_due.last_studied_at else 'recently'}.",
            }

        # 3. Weak Concept (< 0.50 with attempts)
        weak_stmt = (
            select(ConceptMastery)
            .where(
                ConceptMastery.student_id == student_id,
                ConceptMastery.mastery_score < 0.50,
                ConceptMastery.evidence_count > 0,
            )
            .order_by(ConceptMastery.mastery_score.asc())
        )
        weak_res = await self.db.execute(weak_stmt)
        weak = weak_res.scalars().first()
        if weak:
            c_res = await self.db.execute(select(Concept).where(Concept.id == weak.concept_id))
            concept = c_res.scalars().first()
            c_name = concept.name if concept else "Challenging Concept"
            return {
                "action_type": "PRACTICE_WEAK_CONCEPT",
                "priority": "MEDIUM",
                "title": f"Strengthen Weak Concept: {c_name}",
                "description": "Targeted practice questions to build understanding.",
                "concept_id": weak.concept_id,
                "reason": f"Current mastery is {int(weak.mastery_score * 100)}%.",
            }

        # 4. Active In-Progress Session
        sess_stmt = (
            select(LearningSession)
            .where(
                LearningSession.student_id == student_id,
                LearningSession.ended_at.is_(None),
                LearningSession.state.notin_(["COMPLETED", "CHAPTER_COMPLETE"]),
            )
            .order_by(LearningSession.started_at.desc())
        )
        sess_res = await self.db.execute(sess_stmt)
        active_sess = sess_res.scalars().first()
        if active_sess:
            return {
                "action_type": "CONTINUE_LEARNING",
                "priority": "NORMAL",
                "title": f"Resume Active Lesson: {active_sess.session_goal or 'Lesson'}",
                "description": f"Currently in {active_sess.state} phase.",
                "session_id": active_sess.id,
                "topic_id": active_sess.topic_id,
                "concept_id": active_sess.current_concept_id,
                "reason": "Complete the current active learning session.",
            }

        # 5. Default Next Action
        return {
            "action_type": "CONTINUE_LEARNING",
            "priority": "NORMAL",
            "title": "Start Today's Mission: Chemical Effects of Electric Current",
            "description": "Learn new concepts in Class 8 Science.",
            "concept_id": None,
            "reason": "Daily curriculum milestone.",
        }

    async def calculate_chapter_mastery(
        self, student_id: str, chapter_id: str
    ) -> Dict[str, Any]:
        """
        Calculates evidence-weighted chapter mastery derived from all concept masteries in the chapter:
        ChapterMastery = sum(w_i * M_i) / sum(w_i), where w_i = min(evidence_count_i, 5) * tier_i
        """
        from app.models.curriculum import Section, Topic, Concept

        stmt = (
            select(Concept)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Section, Topic.section_id == Section.id)
            .where(Section.chapter_id == chapter_id)
        )
        res = await self.db.execute(stmt)
        concepts = list(res.scalars().all())

        if not concepts:
            return {
                "chapter_id": chapter_id,
                "overall_mastery": 0.0,
                "confidence": "LOW",
                "concepts_count": 0,
                "mastered_concepts_count": 0,
                "is_chapter_mastered": False,
                "concept_breakdowns": [],
            }

        concept_ids = [c.id for c in concepts]
        m_stmt = select(ConceptMastery).where(
            ConceptMastery.student_id == student_id,
            ConceptMastery.concept_id.in_(concept_ids),
        )
        m_res = await self.db.execute(m_stmt)
        mastery_by_concept = {m.concept_id: m for m in m_res.scalars().all()}

        total_weight = 0.0
        weighted_mastery_sum = 0.0
        mastered_count = 0
        total_evidence = 0
        concept_breakdowns = []

        for concept in concepts:
            m = mastery_by_concept.get(concept.id)
            score = m.mastery_score if m else 0.0
            evidence = m.evidence_count if m else 0
            conf = m.confidence if m else "LOW"
            retention = m.retention_stage if m else "EXPOSURE"
            tier = concept.difficulty_tier or 2

            w_i = max(1.0, float(min(evidence, 5) * tier)) if evidence > 0 else 1.0
            total_weight += w_i
            weighted_mastery_sum += w_i * score
            total_evidence += evidence

            if score >= 0.70:
                mastered_count += 1

            concept_breakdowns.append({
                "concept_id": concept.id,
                "concept_name": concept.name,
                "difficulty_tier": tier,
                "mastery_score": score,
                "evidence_count": evidence,
                "confidence": conf,
                "retention_stage": retention,
            })

        overall_mastery = round(weighted_mastery_sum / total_weight, 2) if total_weight > 0 else 0.0

        avg_evidence = total_evidence / len(concepts) if concepts else 0
        if avg_evidence < 2.0:
            overall_confidence = "LOW"
        elif avg_evidence <= 4.0:
            overall_confidence = "MEDIUM"
        else:
            overall_confidence = "HIGH"

        is_chapter_mastered = (
            overall_mastery >= 0.75
            and mastered_count >= int(0.70 * len(concepts))
            and overall_confidence in ["MEDIUM", "HIGH"]
        )

        return {
            "chapter_id": chapter_id,
            "overall_mastery": overall_mastery,
            "confidence": overall_confidence,
            "concepts_count": len(concepts),
            "mastered_concepts_count": mastered_count,
            "is_chapter_mastered": is_chapter_mastered,
            "concept_breakdowns": concept_breakdowns,
        }

