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
| `TEACHING` | Breaks concept down into bite-sized explanations using textbook chunks | Concept presented; prompt understanding check |
| `CHECKING_UNDERSTANDING`| Socratic prompt ("What do you predict happens to the bulb?") | Student verbal/text reflection |
| `PRACTICE` | Adaptive question served based on concept difficulty level | Student submits answer |
| `EVALUATING` | Rubric scoring, missing points detection, misconception extraction | Evaluator returns structured result |
| `REMEDIATION` | Progressive hint ladder activated upon error | Student requests hint or retries |
| `RETEST` | Near-transfer question testing the same concept | Student submits new answer |
| `MASTERY_UPDATE` | Deterministic mastery recalculation, XP awards, event logged | Ready for next concept or completion |
| `CHAPTER_COMPLETE` | Final chapter summary, Boss Battle challenge, progress update | Session finishes |

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
