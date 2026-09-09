# Adaptive Assessment & Rubric Evaluation

## 1. Cognitive Taxonomy & Question Difficulties

Questions are indexed against five cognitive levels adapted for Class 8:

1. **Recall (Level 1):** Definitions, names of substances, direct textbook facts.
2. **Understanding (Level 2):** Explaining "why", distinguishing conductors vs insulators.
3. **Application (Level 3):** Predicting outcomes in a circuit experiment with lemon juice vs sugar solution.
4. **Reasoning (Level 4):** Diagnosing why an LED glows when a regular bulb does not, multi-step cause-and-effect.
5. **Challenge (Level 5):** Chapter Boss Battle questions combining multiple topics, electroplating nuances, and edge cases.

---

## 2. Adaptive Question Selection Algorithm

Question selection is purely deterministic:

```
current_concept_mastery < 0.40 -> Level 1 (Recall) or Level 2 (Understanding)
0.40 <= mastery < 0.70         -> Level 2 (Understanding) or Level 3 (Application)
0.70 <= mastery < 0.90         -> Level 3 (Application) or Level 4 (Reasoning)
mastery >= 0.90                -> Level 4 (Reasoning) or Level 5 (Challenge)
```

If Krish gets 2 consecutive questions wrong on a concept:
- Difficulty immediately drops by 1 tier.
- State transitions to `REMEDIATION`.
- Hint ladder activates.

---

## 3. Rubric-Based Subjective Evaluation

For open-ended questions and "Explain-It-Back" mode, the evaluation does NOT rely on a vague "Is this correct?" prompt. It evaluates against structured rubrics:

```json
{
  "score": 0.85,
  "is_correct": true,
  "missing_concepts": ["mention of positive and negative ions"],
  "misconception_detected": null,
  "detailed_feedback": "Excellent explanation of why salt water conducts electricity. You correctly identified that dissolved salt enables current flow, but remember to mention that it's the free ions (sodium and chloride) that carry the electric charge.",
  "recommended_action": "advance_to_application"
}
```

---

## 4. Misconception Detection & Catalog

When an answer indicates a known misconception (e.g. *"Liquids conduct electricity because electrons flow freely through liquid molecules like in copper wires"*):
1. The misconception pattern is identified from the concept's catalog.
2. A record is added to `misconceptions` table with student ID, concept ID, and evidence quote.
3. The parent dashboard displays the active misconception.
4. The tutor delivers targeted remediation contrasting the misconception with the physical reality (ions vs electrons).
