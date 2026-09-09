# Adaptive Learning Engine & Pedagogical Intelligence (Phase C)

## 1. Architectural Philosophy

KRISH AI TUTOR Phase C transforms the system from a curriculum-grounded answering system into an **authentic adaptive teacher**. The core mission is to optimize Krish's learning rate, conceptual depth, long-term retention, and self-efficacy without cognitive overload or artificial chat elongation.

The system is governed by a foundational invariant:
> **Deterministic Business & Pedagogical Control:**
> AI models suggest explanations, grade socratic/open-ended reflections, and diagnose misconceptions; all state transitions, question deduplication, difficulty adjustments, mastery score calculations, spaced repetition scheduling, and XP allocations are executed strictly by deterministic Python engines.

---

## 2. The 14-Step Adaptive Learning Loop

The full lifecycle of an adaptive learning session proceeds through fourteen calibrated phases:

```
[1. Diagnostic Pre-Test] 
       │ (Assesses baseline knowledge; assigns pre_test_score)
       ▼
[2. Strategy Selection] 
       │ (Selects 1 of 4 pedagogical strategies based on prior history)
       ▼
[3. Targeted Teaching] 
       │ (Bite-sized textbook concept explanation with strategy focus)
       ▼
[4. Socratic Understanding Check] 
       │ (Open-ended reflection; student verbalizes mental model)
       ▼
[5. Adaptive Practice Serving] 
       │ (Deduplicated questions; dynamically stepped difficulty)
       ▼
[6. Rubric & Misconception Evaluation] 
       │ (Rubric matching + specific misconception flag detection)
       ▼
[7. Misconception Remediation (if error)] 
       │ (Targeted counter-explanation dismantling the specific trap)
       ▼
[8. Near-Transfer Retest] 
       │ (Validates resolution of misconception; marks resolved)
       ▼
[9. Feynman "Explain-It-Back"] 
       │ (Student explains concept in their own words to confirm mastery)
       ▼
[10. Deterministic Mastery Calculation] 
       │ (Weighted moving average: accuracy, difficulty, consistency)
       ▼
[11. Normalized Learning Gain Assessment] 
       │ (Calculates g = (Post - Pre) / (1.0 - Pre))
       ▼
[12. Stopping Condition Verification] 
       │ (Terminates gracefully once mastery >= 0.85; avoids AI drift)
       ▼
[13. Spaced Repetition Scheduling] 
       │ (Calibrated 1d -> 3d -> 7d -> 14d retention ladder)
       ▼
[14. Next Best Action Computation] 
       │ (Selects optimal next learning activity based on urgency matrix)
```

---

## 3. Pedagogical Strategies

Rather than using a generic monologue, the engine categorizes teaching into four pedagogical approaches via `TeachingStrategy`:

| Strategy | When Activated | Pedagogical Focus |
|---|---|---|
| `FIRST_PRINCIPLES` | High baseline diagnostic, advanced student | Derives facts from fundamental scientific laws (e.g. conservation of energy, atomic charge). |
| `WORKED_EXAMPLE` | Repeated errors or low prior mastery | Breaks down step-by-step problem solving with explicit input-output demonstration. |
| `REAL_WORLD_ANALOGY` | Novel, abstract concepts | Grounds invisible concepts in tangible everyday experiences (e.g. water pipe flow for electric circuits). |
| `VISUAL_STEP_BY_STEP` | Complex multi-stage physical/chemical processes | Focuses on structural sequencing, cause-and-effect stages, and visualizable mental models. |

**Selection Logic (`tutor_engine.select_teaching_strategy`):**
```python
if prior_mastery < 0.4 or consecutive_errors >= 2:
    return TeachingStrategy.WORKED_EXAMPLE
elif diagnostic_score >= 0.8:
    return TeachingStrategy.FIRST_PRINCIPLES
elif topic_is_abstract:
    return TeachingStrategy.REAL_WORLD_ANALOGY
else:
    return TeachingStrategy.VISUAL_STEP_BY_STEP
```

---

## 4. Question Deduplication & Adaptive Difficulty

### Question Deduplication
To prevent student frustration from seeing identical questions:
- Each `LearningSession` maintains an `attempted_question_ids: list[str]` JSON field.
- During question retrieval (`assessment_engine.get_practice_questions`):
  ```python
  query = select(Question).where(
      Question.topic_id == topic_id,
      Question.id.notin_(attempted_question_ids)
  )
  ```
- If the repository has exhausted unused questions, the engine safely falls back to least-recently attempted questions.

### Dynamic Cognitive Step-Up
Difficulty adapts dynamically based on Krish's consecutive performance:
- `consecutive_correct_count >= 2`: Difficulty steps up (`BEGINNER` -> `INTERMEDIATE` -> `ADVANCED` -> `OLYMPIAD`).
- `incorrect_answer`: Difficulty steps down or remains at `BEGINNER`, and `consecutive_correct_count` resets to 0.

---

## 5. Misconception Remediation Loop

When Krish makes an error, the engine avoids generic "Try again":
1. **Misconception Tagging:** The evaluator flags specific misconceptions (e.g., `"confusing_electron_flow_with_ion_flow"`).
2. **Targeted Remediation:** The tutor generates an explicit counter-explanation focused solely on why this intuition is tempting but incorrect.
3. **Retest:** The engine serves a near-transfer question testing the identical concept.
4. **Resolution:** If the retest is passed, the misconception status is updated to `resolved = True` in the database, Krish is awarded +30 XP, and mastery is restored.

---

## 6. Feynman "Explain-It-Back" Technique

To guard against the illusion of explanatory depth (recognizing an answer without truly understanding it):
- The tutor transitions to `TutorState.EXPLAIN_IT_BACK`.
- Krish is asked: *"Imagine you're teaching this to your younger friend. In 2-3 sentences, explain why this happens."*
- Evaluated against 4 criteria:
  1. Scientific Accuracy (>= 0.70)
  2. Completeness (>= 0.70)
  3. Clarity of Expression (>= 0.65)
  4. Depth of Conceptual Understanding (>= 0.70)
- Achieving an overall score >= 0.75 unlocks `confirmed_mastery = True` and transitions the concept from superficial recall to validated comprehension.

---

## 7. Mastery Model & Normalized Learning Gain

### Mastery Score Formula
Mastery is continuous in [0.0, 1.0]:
$$M_{new} = M_{old} 	imes (1 - lpha) + S_{eval} 	imes lpha 	imes D_{weight}$$
where:
- $lpha = 0.25$ (learning rate)
- $S_{eval} \in [0.0, 1.0]$ (evaluation score)
- $D_{weight} \in \{0.8 \text{ (Beginner)}, 1.0 \text{ (Intermediate)}, 1.2 \text{ (Advanced)}, 1.4 \text{ (Olympiad)}\}$

### Normalized Learning Gain ($g$)
Evaluates pedagogical effectiveness between Pre-Test ($S_{pre}$) and Post-Test ($S_{post}$):
$$g = \begin{cases} \frac{S_{post} - S_{pre}}{1.0 - S_{pre}} & \text{if } S_{pre} < 1.0 \\ 1.0 & \text{if } S_{pre} = 1.0 \text{ and } S_{post} = 1.0 \end{cases}$$

---

## 8. Stopping Condition & Session Completion

Unlike generic conversational agents that converse indefinitely, KRISH AI TUTOR has an explicit stopping condition:
- **Mastery Target:** Session concept mastery reaches >= 0.85 with `confirmed_mastery = True`.
- **Target Achieved:** The tutor triggers `CHAPTER_COMPLETE`, congratulates Krish, summarizes key takeaways, records completion time, and presents next steps.
- **Cognitive Protection:** If Krish struggles repeatedly (>= 3 failed remediation loops on the same concept), the tutor halts practice, provides a summary bookmark, and recommends a scheduled revision rather than inducing fatigue.

---

## 9. Spaced Repetition & Retention Stages

Retention is modeled across two distinct stages:
1. `INITIAL_MASTERY`: Concept recently learned and passed ($M \ge 0.80$).
2. `RETAINED_MASTERY`: Concept tested and verified across spaced revision intervals.

### Calibrated Spaced Repetition Intervals
Intervals double upon successful revision:
$$\Delta t \in \{1 \text{ day}, 3 \text{ days}, 7 \text{ days}, 14 \text{ days}\}$$

### Comeback Bonus
Krish is awarded a **+50 XP Comeback Bonus** when revising a topic on or after its scheduled `next_revision_date`, reinforcing consistent study habits.

---

## 10. Next Best Action Algorithm

When Krish opens the application, the `mastery_engine.calculate_next_best_action` determines the highest-yield pedagogical action via a deterministic priority waterfall:

1. **Priority 1: Overdue Spaced Revision** (Revising aging memories before decay).
2. **Priority 2: Active Unfinished Session** (Resuming a paused topic).
3. **Priority 3: Active Misconception** (Remediating fragile mental models).
4. **Priority 4: Next Sequential Topic** (Expanding curriculum progress).
