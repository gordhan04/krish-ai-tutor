# Testing Strategy & Evaluation Framework

## 1. Testing Pyramid

- **Unit Tests:**
  - Mastery calculation formula.
  - State machine transitions & legal/illegal transitions.
  - 5-level hint ladder progression.
  - Rubric parsing and scoring bounds.
  - Token/character chunking rules.
- **Integration Tests:**
  - Database schema & repositories with async engine.
  - RAG metadata filtering with cosine similarity.
  - Event logging and session persistence.
- **API Tests:**
  - Full request-response cycle from login to lesson completion.
- **AI Evaluation Framework:**
  - Hermetic testing using `MockAIProvider` to verify system stability in CI.
  - Prompt regression test cases checking grounding against curriculum context.
