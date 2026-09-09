# KRISH AI TUTOR (Class 8)

> **A curriculum-aware AI tutor + adaptive assessment system + personal learning coach for Krish (Class 8).**

KRISH AI TUTOR is built from the ground up to optimize for **learning outcomes first, engagement second**. It grounds all tutoring strictly in school textbooks (NCERT Class 8 Science), employs an explicit tutor state machine, provides a 5-tier hint ladder, deterministically tracks concept-level mastery, detects misconceptions, offers healthy habit-forming gamification (XP, streaks with grace days, daily missions), and provides an actionable dashboard for parents.

---

## Architecture Overview

- **Backend:** Python 3.13 + FastAPI + SQLAlchemy 2.0 (asyncio) + Pydantic v2.
- **Database:** PostgreSQL + `pgvector` (production/Docker) with automated dual-driver SQLite fallback (`aiosqlite`) for zero-friction local development.
- **Frontend:** Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS + Lucide React.
- **AI Orchestration:** Pluggable `AIProvider` supporting Google Gemini (Flash / Pro), OpenAI (GPT-4o), and deterministic Mock AI with strict prompt injection boundaries.
- **Voice Tutoring:** Web Speech API integration (SpeechRecognition & SpeechSynthesis) backed by the same unified Tutor Engine.

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.13+
- Node.js v20+ and npm

### 2. Backend Setup
```bash
# Create virtual environment
python -m venv backend/.venv

# Activate virtual environment (Windows PowerShell)
.\backend\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations & seed data
alembic -c backend/alembic.ini upgrade head

# Start FastAPI server
uvicorn app.main:app --app-dir backend --reload --port 8000
```
Backend API docs available at: `http://localhost:8000/docs`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to interact with Krish's learning space.

---

## Core Learning Loop (Vertical Slice Proven)

1. **Student Home:** Krish sees Level, XP progress, study streak with grace badge, and **Today's Mission** (*Chemical Effects of Electric Current*, 12 mins).
2. **Start Mission / Lesson:** AI Tutor retrieves grounded textbook excerpts (e.g. NCERT Class 8, Page 140) and teaches the core concept (*Electrolytes & Ionic Conductivity*).
3. **Check Understanding & Hints:** The tutor poses a Socratic check. If Krish struggles, he can climb the **5-Tier Hint Ladder** (Level 1 Clue $\to$ Level 2 Concept $\to$ Level 3 First Step $\to$ Level 4 Walkthrough $\to$ Level 5 Full Solution).
4. **Adaptive Practice:** Adaptive question served (MCQ or open-ended). Krish can answer via text or voice.
5. **Rubric Evaluation & Misconception Diagnosis:** The system evaluates the response against expected concepts and misconception traps (e.g., confusing electrons with mobile ions in liquids).
6. **Mastery & Telemetry:** Deterministic calculation updates concept mastery score, awards XP, updates streaks, and logs learning events.
7. **Parent Dashboard:** Real-time visibility into learning gain (+38.5%), concept mastery heatmaps, and actionable parent recommendations.

---

## Automated Test Suite

Run all tests hermetically with:
```bash
.\backend\.venv\Scripts\pytest.exe backend/tests -v
```
All tests run against in-memory SQLite and mock providers, executing in under 1 second.
