# AI Tutor Engine & State Machine

## 1. Pedagogical Vision

KRISH AI TUTOR is an active educational coach, not a passive answering machine. It adopts the Socratic method, grounds all responses in Krish's Class 8 textbook curriculum, and follows a strict hint ladder before revealing answers.

```
       +-------------------------------------------------------------+
       |                                                             |
       v                                                             |
+--------------+     lesson_start      +------------------+          |
|     IDLE     | --------------------> |   LESSON_START   |          |
+--------------+                       +--------+---------+          |
                                                |                    |
                                                v                    |
                                       +------------------+          |
                         +------------ |     TEACHING     | <--------+
                         |             +--------+---------+          | (next concept)
                         |                      |                    |
                         |                      v                    |
                         |             +------------------+          |
                         |             | CHECK_UNDERSTAND | ---------+
                         |             +--------+---------+
                         |                      | (wants practice)
                         |                      v
                         |             +------------------+
                         +-----------> |     PRACTICE     |
                                       +--------+---------+
                                                | (submit answer)
                                                v
                                       +------------------+
                                       |    EVALUATING    |
                                       +---+------------+-+
                                           |            |
                                (incorrect)|            | (correct)
                                           v            v
                                   +------------+  +--------------+
                                   | REMEDIATION|  |MASTERY_UPDATE|
                                   | & HINTS    |  +-------+------+
                                   +-----+------+          |
                                         | (retry)         |
                                         v                 v
                                   +------------+  +--------------+
                                   |   RETEST   |  | CHAPTER_DONE |
                                   +------------+  +--------------+
```

---

## 2. Tutor States

| State | Purpose | Transition Trigger |
|---|---|---|
| `IDLE` | No active session | User clicks "Start Lesson" |
| `LESSON_START` | Initializes topic context, learning objectives, and prior mastery | Initial greeting & objective orientation |
| `DIAGNOSTIC` | Baseline pre-assessment before instructional delivery | Topic start; student submits pre-test |
| `TEACHING` | Delivers strategy-guided bite-sized explanation grounded in chunks | Concept presented; prompt understanding check |
| `CHECKING_UNDERSTANDING`| Socratic prompt ("What do you predict happens to the bulb?") | Student verbal/text reflection |
| `PRACTICE` | Adaptive question served based on concept difficulty level | Student submits answer |
| `EVALUATING` | Rubric scoring, missing points detection, misconception extraction | Evaluator returns structured result |
| `REMEDIATION` | Targeted misconception remediation & progressive hint ladder | Evaluator detects error or misconception |
| `RETEST` | Near-transfer question testing the same concept | Student submits new answer |
| `EXPLAIN_IT_BACK` | Feynman technique verification of deep understanding | Student explains concept in own words |
| `MASTERY_UPDATE` | Deterministic mastery recalculation, XP awards, event logged | Retest or explain-it-back passed |
| `CHAPTER_COMPLETE` | Final completion summary, learning gain report, revision scheduled | Mastery target achieved (Stopping Condition) |

---

## 3. The 5-Level Hint Ladder

When Krish struggles with an exercise or conceptual question, the tutor will NEVER immediately dump the final answer. Instead, it climbs the **Hint Ladder**:

- **Level 0 (Try First):** Encouragement to re-read or reason independently.
- **Level 1 (Subtle Clue):** Points attention to a key variable or textbook clue without revealing relationships (e.g., *"Think about what ions do in water"*).
- **Level 2 (Conceptual Hint):** Explains the underlying scientific principle (e.g., *"Pure distilled water has no free ions, but tap water contains dissolved mineral salts"*).
- **Level 3 (First Step):** Walks Krish through the initial setup or first mathematical/logical step.
- **Level 4 (Guided Walkthrough):** Provides almost the complete solution, leaving only the final conclusion for Krish to calculate or state.
- **Level 5 (Full Solution & Insight):** Reveals the complete explanation and highlights why the common trap occurred.

---

## 4. Structured Output Contract

All tutor decisions return typed Pydantic payloads:

```json
{
  "state": "TEACHING",
  "message": "Let's look at how electricity passes through liquids...",
  "current_concept_id": "concept-123",
  "hint_level": 0,
  "should_ask_question": true,
  "next_recommended_action": "check_understanding",
  "pedagogical_intent": "introduce_electrolyte_concept"
}
```

---

## 5. Pedagogical Strategies & Feynman Technique

1. **Pedagogical Strategy Selection:** The tutor dynamically selects from 4 teaching strategies:
   - `FIRST_PRINCIPLES`: For students with high baseline or quick mastery.
   - `WORKED_EXAMPLE`: For students requiring procedural step-by-step guidance.
   - `REAL_WORLD_ANALOGY`: For grounding abstract invisible concepts.
   - `VISUAL_STEP_BY_STEP`: For multi-stage physical/chemical processes.
2. **Feynman Technique (`EXPLAIN_IT_BACK`):**
   - The student is prompted to explain the learned concept in their own simple words.
   - The AI evaluates accuracy, completeness, clarity, and conceptual depth.
   - Confirmation is required for high-retention mastery classification (`confirmed_mastery = True`).

---

## 6. Deterministic Stopping Condition

To protect Krish's cognitive stamina and eliminate AI conversational drift, the tutor engine enforces deterministic exit criteria:
- **Mastery Target:** Reaching concept mastery $\ge 0.85$ with `confirmed_mastery = True` immediately transitions the session to `CHAPTER_COMPLETE`.
- **Cognitive Protection:** If Krish struggles repeatedly across 3 remediation attempts, the engine pauses active testing, issues an encouraging summary, and schedules a spaced revision.

