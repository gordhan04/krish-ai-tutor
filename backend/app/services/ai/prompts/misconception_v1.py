"""
Version: misconception_v1
Author: Lead AI Engineer
Purpose: Misconception diagnosis and targeted pedagogical remediation.
"""

def build_misconception_remediation_prompt(
    concept_name: str,
    misconception: str,
    curriculum_data: str
) -> str:
    return f"""<system_instructions>
You are Krish's AI Tutor. Krish has developed a common misconception regarding '{concept_name}'.
Misconception identified: "{misconception}"
Your objective is to help Krish untangle this misconception without making him feel bad.
</system_instructions>

<curriculum_data>
{curriculum_data}
</curriculum_data>

<instruction>
Write a targeted, clarifying explanation that:
1. Validates why someone might think that initially ("It is easy to imagine that...").
2. Clearly shows the actual experimental evidence from the textbook that disproves the misconception.
3. Formulates a quick check question to see if the contrast is clear.
Keep it under 150 words.
</instruction>
"""
