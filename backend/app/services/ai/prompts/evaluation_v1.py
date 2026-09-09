"""
Version: evaluation_v1
Author: Lead AI Engineer
Purpose: Structured rubric evaluation of subjective answers and explain-it-back exercises.
"""
from typing import List, Dict

EVALUATION_SYSTEM_PROMPT = """You are an objective academic evaluator for Class 8 Science.
Your job is to evaluate a student's answer against an exact grading rubric and identify conceptual strengths, missing points, and misconceptions.

You MUST respond strictly in valid JSON format matching this schema:
{
  "score": float between 0.0 and 1.0,
  "is_correct": boolean (true if score >= 0.70),
  "missing_concepts": list of strings (concepts student omitted),
  "misconception_detected": string or null (if student exhibited a specific misconception),
  "detailed_feedback": string (encouraging and constructive Class 8 feedback),
  "recommended_action": string ("advance", "retry_with_hint", or "reinforce")
}
"""

def build_evaluation_prompt(
    question_prompt: str,
    student_answer: str,
    expected_concepts: List[str],
    required_points: List[str],
    misconception_traps: Dict[str, str],
    curriculum_context: str
) -> str:
    return f"""<system_instructions>
{EVALUATION_SYSTEM_PROMPT}
</system_instructions>

<curriculum_data>
{curriculum_context}
</curriculum_data>

<question>
{question_prompt}
</question>

<student_answer>
{student_answer}
</student_answer>

<rubric>
Expected Concepts: {expected_concepts}
Required Points: {required_points}
Known Misconception Traps: {misconception_traps}
</rubric>

<instruction>
Evaluate the student's answer thoroughly against the rubric. Output only JSON.
</instruction>
"""
