import re
from typing import Dict, Any, List
from app.services.ai.base import AIProvider, TutorResponse, EvaluationResult


class MockAIProvider(AIProvider):
    """
    High-fidelity deterministic Mock AI Provider for testing and offline development.
    Emulates grounded responses, rubric evaluations, misconception detection, and hint ladder.
    """

    async def generate_explanation(
        self,
        concept_name: str,
        learning_objective: str,
        curriculum_context: str,
        student_name: str = "Krish",
    ) -> TutorResponse:
        message = (
            f"Hello {student_name}! 👋 Today we're exploring **{concept_name}**.\n\n"
            f"**Key Idea:** According to your textbook, pure distilled water does not conduct electricity. "
            f"However, when mineral salts, acids, or bases are dissolved in water, they produce free ions. "
            f"These moving ions carry electric current through the liquid!\n\n"
            f"Think of it like a crowded swimming pool where floating balls carry a message from one side to another.\n\n"
            f"💡 **Check question:** What do you think happens if we test tap water versus pure distilled water in a tester circuit?"
        )
        return TutorResponse(
            message=message,
            pedagogical_intent="explain",
            hint_level=0,
            suggested_quick_replies=[
                "Tap water conducts electricity, distilled water does not.",
                "Both conduct electricity equally.",
                "Neither conducts electricity."
            ]
        )

    async def generate_socratic_check(
        self,
        concept_name: str,
        curriculum_context: str,
        prior_explanation: str,
    ) -> TutorResponse:
        message = (
            f"Before we jump into practice, imagine you connect a battery, a small LED, and two metal pins dipped into lemon juice. "
            f"Do you think the LED will glow? Why or why not?"
        )
        return TutorResponse(
            message=message,
            pedagogical_intent="socratic_check",
            hint_level=0,
            suggested_quick_replies=[
                "Yes, because lemon juice contains acid with free ions.",
                "No, lemon juice is an insulator."
            ]
        )

    async def evaluate_student_answer(
        self,
        question_prompt: str,
        student_answer: str,
        expected_concepts: List[str],
        required_points: List[str],
        misconception_traps: Dict[str, str],
        curriculum_context: str,
    ) -> EvaluationResult:
        normalized_answer = student_answer.lower()

        # Check for known misconception traps
        detected_misconception = None
        for trap_keyword, misconception_desc in misconception_traps.items():
            if trap_keyword.lower() in normalized_answer:
                detected_misconception = misconception_desc
                break

        # Check missing concepts
        missing = []
        found_count = 0
        for concept in expected_concepts:
            # Check if keywords from expected concept appear in answer
            words = [w for w in re.split(r'\W+', concept.lower()) if len(w) > 3]
            matched = any(w in normalized_answer for w in words) if words else False
            if matched:
                found_count += 1
            else:
                missing.append(concept)

        total_expected = max(len(expected_concepts), 1)
        base_score = found_count / total_expected

        if detected_misconception:
            score = max(0.2, base_score * 0.5)
            is_correct = False
            feedback = (
                f"You're thinking along interesting lines, but notice a common misconception: {detected_misconception}. "
                f"In liquids, it is dissolved ions (charged particles), not free electrons or pure water molecules, that carry the current!"
            )
            action = "retry_with_hint"
        elif base_score >= 0.7:
            score = min(1.0, round(base_score, 2))
            is_correct = True
            feedback = (
                f"Spot on! 🎯 You clearly grasped the core mechanism. "
                + (f"To make your school exam answer 100% complete, also mention: {', '.join(missing)}." if missing else "Your explanation is complete and grounded in your textbook!")
            )
            action = "advance"
        else:
            score = max(0.3, round(base_score, 2))
            is_correct = False
            feedback = (
                f"Good start! You mentioned some relevant ideas, but your answer is missing key concepts: {', '.join(missing) if missing else 'the chemical mechanism'}. "
                f"Recall what happens to salt crystals when they dissolve in water."
            )
            action = "retry_with_hint"

        return EvaluationResult(
            score=score,
            is_correct=is_correct,
            missing_concepts=missing,
            misconception_detected=detected_misconception,
            detailed_feedback=feedback,
            recommended_action=action,
        )

    async def generate_hint(
        self,
        question_prompt: str,
        student_previous_attempts: List[str],
        hint_level: int,
        curriculum_context: str,
    ) -> TutorResponse:
        hints = {
            1: "Hint 1 (Clue): Consider whether pure water has any dissolved substances in it.",
            2: "Hint 2 (Concept): Current needs mobile electric charges to flow. In solids it's electrons, but what forms when acids or salts dissolve in water?",
            3: "Hint 3 (First Step): Start by classifying tap water versus distilled water: which one has dissolved minerals?",
            4: "Hint 4 (Guided Walkthrough): When salt ($NaCl$) dissolves in water, it splits into positive sodium ions ($Na^+$) and negative chloride ions ($Cl^-$). Now, what do these ions do when connected to a battery?",
            5: "Hint 5 (Full Solution): Distilled water has no dissolved salts and cannot conduct electricity. Tap water contains small amounts of dissolved mineral salts, providing free ions that conduct electric current. Thus, the circuit is completed and the bulb glows.",
        }
        clamped_level = min(max(hint_level, 1), 5)
        return TutorResponse(
            message=hints.get(clamped_level, hints[1]),
            pedagogical_intent="hint",
            hint_level=clamped_level,
            suggested_quick_replies=["I get it now! Let me answer.", "Could you explain the ions part again?"]
        )
