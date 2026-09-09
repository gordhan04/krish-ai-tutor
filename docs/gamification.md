# Healthy Gamification & Habit Formation

## 1. Core Principles

The gamification engine in KRISH AI TUTOR is designed around **learning outcomes first, engagement second**.
- We do NOT reward idle screen time or meaningless clicking.
- XP is granted for mastering concepts, solving application questions, completing revisions, and explaining concepts.
- Streaks include rest days and consistency metrics (e.g. 14 of 16 days) to prevent toxic guilt or abandonment.

---

## 2. XP & Leveling Formula

Krish begins at Level 1 (0 XP). Each level requires an escalating threshold of XP based on a quadratic curve:

$$\text{XP}_{\text{required}}(L) = 100 \times L^{1.5}$$

### XP Reward Matrix:
| Action | XP Awarded |
|---|---|
| Complete Concept Explanation | 20 XP |
| Answer Level 1 (Recall) Question | 10 XP |
| Answer Level 2/3 (Application) Question | 25 XP |
| Answer Level 4/5 (Challenge) Question | 50 XP |
| Complete "Explain-It-Back" with >80% rubric | 40 XP |
| Remediate an identified misconception | 60 XP |
| Complete Daily Mission | 100 XP |
| Defeat Chapter Boss Battle | 250 XP |

---

## 3. Daily Mission Generator

Each day at 00:00 (or on first login), the system generates a tailored mission based on Krish's learning frontier:
- 1st Priority: Overdue spaced-repetition revisions.
- 2nd Priority: Active unresolved misconceptions.
- 3rd Priority: Next incomplete topic in the active chapter.

Estimated mission time is capped at **12-18 minutes** to respect healthy study habits.
