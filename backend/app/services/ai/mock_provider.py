import re
from typing import Dict, Any, List, Optional
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
            strategy="DIRECT_EXPLANATION",
            hint_level=0,
            suggested_quick_replies=[
                "Tap water conducts electricity, distilled water does not.",
                "Both conduct electricity equally.",
                "Neither conducts electricity."
            ]
        )

    async def generate_strategy_explanation(
        self,
        concept_name: str,
        learning_objective: str,
        curriculum_context: str,
        strategy: str,
        student_name: str = "Krish",
        prior_misconception: str = None,
    ) -> TutorResponse:
        strategy_upper = strategy.upper()

        if strategy_upper == "ANALOGY":
            message = (
                f"Hey {student_name}! To understand **{concept_name}**, let's use an analogy:\n\n"
                f"Imagine a busy highway. In solid metal wires, electrons are like fast sports cars zooming in their lanes. "
                f"In liquids, however, there are no loose sports cars! Instead, dissolved mineral salts split into charged 'ferry boats' called **ions**. "
                f"These ferry boats carry the electric charge across the liquid pool.\n\n"
                f"No ferry boats (distilled water)? No traffic flows!"
            )
            replies = ["The ions act like boats carrying charge.", "So pure water has no boats?"]
        elif strategy_upper == "REAL_WORLD_EXAMPLE":
            message = (
                f"Let's look at an everyday example, {student_name}:\n\n"
                f"If you ever touch electrical switches with wet hands, it is dangerous. Why? "
                f"Pure water doesn't conduct, but our tap water and the moisture on our skin has dissolved mineral salts. "
                f"Those tiny dissolved salts turn regular water into a conductor!"
            )
            replies = ["Dissolved salts make tap water conductive.", "That's why distilled water is safe?"]
        elif strategy_upper == "STEP_BY_STEP":
            message = (
                f"Let's break down **{concept_name}** step by step:\n\n"
                f"1. **Dissolution**: Solid salts (like sodium chloride) enter the liquid.\n"
                f"2. **Ionization**: The molecules break apart into positively and negatively charged ions.\n"
                f"3. **Conduction**: When a battery voltage is applied, positive ions move toward the negative terminal and negative ions toward the positive terminal.\n"
                f"4. **Current Flow**: This movement of ions constitutes the electric current in liquids!"
            )
            replies = ["Step 1: Dissolve, Step 2: Ions, Step 3: Flow.", "What if the salt doesn't dissolve?"]
        elif strategy_upper == "CORRECT_MISCONCEPTION":
            misc = prior_misconception or "electrons flow through pure water"
            message = (
                f"Let's pause and clear up a common trap, {student_name}!\n\n"
                f"You might have thought: *'{misc}'*. It is very natural to think that! "
                f"In metal wires, electrons do all the moving. But in liquids, individual electrons cannot survive freely. "
                f"Textbook Activity 11.2 proves that electric current only flows when dissolved salts produce **ions**.\n\n"
                f"Let's remember: **Metals = Free electrons; Liquids = Dissolved ions**."
            )
            replies = ["Got it: Liquids use ions, not electrons.", "Can we retest this?"]
        elif strategy_upper == "SOCRATIC":
            message = (
                f"Krish, let's think about **{concept_name}** together.\n\n"
                f"When you dissolve table salt into water, what happens at the microscopic level? "
                f"How might that allow electrical charge to move between submerged electrodes?"
            )
            replies = ["Salt splits into charged particles.", "I'd like a hint to think about this."]
        elif strategy_upper == "RECAP":
            message = (
                f"**Quick Recap on {concept_name}**:\n"
                f"• Pure distilled water is an insulator (poor conductor).\n"
                f"• Adding salt, acid, or base produces charged ions.\n"
                f"• These ions carry electric current through liquids."
            )
            replies = ["I understand the recap.", "Let's practice!"]
        else:
            resp = await self.generate_explanation(
                concept_name=concept_name,
                learning_objective=learning_objective,
                curriculum_context=curriculum_context,
                student_name=student_name,
            )
            resp.strategy = strategy_upper
            return resp

        return TutorResponse(
            message=message,
            pedagogical_intent="explain",
            strategy=strategy_upper,
            hint_level=0,
            suggested_quick_replies=replies,
        )

    async def evaluate_socratic_response(
        self,
        concept_name: str,
        socratic_question: str,
        student_response: str,
        curriculum_context: str,
    ) -> Dict[str, Any]:
        normalized = student_response.lower()
        # Look for conceptual words
        keywords = ["ion", "salt", "conduct", "acid", "glow", "flow", "yes", "current", "dissolve", "heat", "oxygen", "fire"]
        matches = [kw for kw in keywords if kw in normalized]

        if len(matches) >= 2 or ("yes" in normalized and ("ion" in normalized or "acid" in normalized)):
            return {
                "understanding_confirmed": True,
                "feedback": f"Excellent reasoning! You correctly recognized how the underlying mechanism functions. Ready to test this in practice?",
                "suggested_replies": ["Ready for practice question!", "Explain one more detail"],
            }
        elif len(matches) == 1:
            return {
                "understanding_confirmed": True,
                "feedback": f"Good intuition! You noticed {matches[0]}. Now let's see how it applies to a standard question.",
                "suggested_replies": ["Start practice question", "Show a hint"],
            }
        else:
            return {
                "understanding_confirmed": False,
                "feedback": "You're exploring interesting ideas, but remember: in liquids it's the dissolved ions that carry the current. Let's look at an example before practicing.",
                "suggested_replies": ["Show me a worked example", "Explain again"],
            }

    async def generate_misconception_remediation(
        self,
        concept_name: str,
        misconception_text: str,
        curriculum_context: str,
        student_name: str = "Krish",
    ) -> TutorResponse:
        message = (
            f"Let's untangle this concept together, {student_name}!\n\n"
            f"You noticed: *'{misconception_text}'*.\n\n"
            f"Here is what the textbook experiment shows: when we place a tester in distilled water, the bulb does not glow. "
            f"The moment we add a pinch of common salt, the bulb glows brightly! "
            f"This proves that it is the **dissolved mineral ions**, not pure water itself, that allows electricity to flow.\n\n"
            f"Does the contrast between pure water and salt solution make sense now?"
        )
        return TutorResponse(
            message=message,
            pedagogical_intent="remediation",
            strategy="CORRECT_MISCONCEPTION",
            hint_level=0,
            suggested_quick_replies=[
                "Yes, salt ions carry the current.",
                "Can we retest this now?",
            ],
        )

    async def evaluate_explain_it_back(
        self,
        concept_name: str,
        student_explanation: str,
        key_points: Optional[List[str]] = None,
        curriculum_context: str = "",
        concept_explanation: str = "",
    ) -> Dict[str, Any]:
        if not key_points:
            key_points = [
                "Pure distilled water lacks free ions and is a poor conductor",
                "Dissolved mineral salts dissociate into positive and negative ions",
                "These mobile ions carry electric current through the liquid",
            ]
        normalized = student_explanation.lower()
        matched = []
        missing = []

        for kp in key_points:
            words = [w for w in re.split(r'\W+', kp.lower()) if len(w) > 3]
            if any(w in normalized for w in words):
                matched.append(kp)
            else:
                missing.append(kp)

        score = round(len(matched) / max(len(key_points), 1), 2)
        is_correct = score >= 0.50

        if is_correct:
            feedback = (
                f"Fantastic synthesis in your own words, Krish! 🌟 You explained {len(matched)} key points accurately. "
                + (f"For perfection on exams, don't forget: {missing[0]}." if missing else "Your explanation shows solid conceptual mastery!")
            )
            depth = "DEEP" if score >= 0.80 else "SOLID"
        else:
            feedback = (
                f"Good effort trying to explain it back! You're on the right track, but some detail is missing: "
                f"remember to explain {', '.join(missing[:2])}."
            )
            depth = "SURFACE"

        return {
            "score": score,
            "accurate": is_correct,
            "depth": depth,
            "feedback": feedback,
            "criteria_scores": {
                "accuracy": score,
                "completeness": round(score * 0.9, 2),
                "clarity": 1.0 if is_correct else 0.5,
            },
            "suggested_replies": [
                "Review my learning gain",
                "Try another challenge",
                "Finish lesson",
            ],
        }

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

    async def generate_embeddings(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        import hashlib
        import math

        embeddings = []
        dim = 768
        for text in texts:
            # Deterministic pseudo-embedding based on text tokens and hashing
            vec = [0.0] * dim
            words = re.findall(r'\w+', text.lower())
            for i, word in enumerate(words):
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)
                idx = h % dim
                vec[idx] += 1.0 / (1.0 + (i * 0.05))

            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [round(x / norm, 5) for x in vec]
            else:
                vec = [1.0 / math.sqrt(dim)] * dim
            embeddings.append(vec)
        return embeddings

    async def extract_concepts_and_objectives(
        self,
        topic_title: str,
        topic_text: str,
    ) -> Dict[str, Any]:
        # Deterministic extraction of key concepts from text
        sentences = [s.strip() for s in re.split(r'[.!?]+', topic_text) if len(s.strip()) > 20]
        concept_name = topic_title
        summary = sentences[0] if sentences else f"Core principles of {topic_title}."
        if len(sentences) > 1:
            summary += " " + sentences[1]

        return {
            "concepts": [
                {
                    "name": concept_name,
                    "summary": summary[:400],
                    "difficulty_tier": 2,
                }
            ],
            "learning_objectives": [
                {
                    "statement": f"Understand and explain the principles of {topic_title} as described in the textbook.",
                    "bloom_taxonomy_level": "Understanding",
                }
            ],
        }

    async def generate_candidate_questions(
        self,
        concept_name: str,
        concept_summary: str,
        source_text: str,
    ) -> List[Dict[str, Any]]:
        return [
            {
                "question_type": "mcq",
                "cognitive_level": 2,
                "prompt": f"Based on the concept of '{concept_name}', what is the primary takeaway?",
                "explanation": f"According to the curriculum: {concept_summary[:200]}",
                "source_type": "generated_practice",
                "options": [
                    {"option_key": "A", "option_text": f"{concept_name} plays a key functional role in the process.", "is_correct": True, "feedback": "Correct! Directly grounded in the lesson."},
                    {"option_key": "B", "option_text": f"{concept_name} has no effect on the reaction.", "is_correct": False, "feedback": "Incorrect. The textbook demonstrates the opposite."},
                    {"option_key": "C", "option_text": "The process occurs only in absolute zero conditions.", "is_correct": False, "feedback": "Incorrect."},
                    {"option_key": "D", "option_text": "None of the above.", "is_correct": False, "feedback": "Incorrect."}
                ]
            },
            {
                "question_type": "rubric_explanation",
                "cognitive_level": 3,
                "prompt": f"In your own words, explain how '{concept_name}' operates, citing an example from your textbook.",
                "explanation": f"Students should state: {concept_summary[:200]}",
                "source_type": "generated_practice",
                "rubric": {
                    "expected_concepts": [concept_name, "scientific mechanism", "textbook observation"],
                    "required_points": [
                        f"Defines {concept_name} correctly.",
                        "Explains how conditions affect the phenomenon.",
                    ],
                    "misconception_traps": {
                        "spontaneous": f"Believing {concept_name} occurs without any energy transfer or interaction.",
                        "solids": f"Confusing the state of matter involved in {concept_name}."
                    },
                    "max_score": 1.0
                }
            }
        ]
