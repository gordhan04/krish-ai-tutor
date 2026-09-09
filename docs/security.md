# Child Safety, Privacy & Security Architecture

## 1. Child Privacy Standards
KRISH AI TUTOR is built strictly for educational interaction:
- **Zero Advertising or Third-Party Tracking:** No behavioral trackers, ad SDKs, or external trackers.
- **Minimal PII:** Only internal pseudonymous IDs are passed to LLMs. Krish's personal details (address, phone, location) are never requested or stored.
- **No Inappropriate Conversational Roles:** The AI is strictly an academic tutor, never a therapist, romantic companion, or unfiltered open-ended chatbot. Any non-academic queries are gently redirected to learning.

## 2. Role-Based Access Control (RBAC)
- **Role `student`:** Can access curriculum, participate in lessons, submit answers, earn XP, and view their own learning stats. Cannot access parent dashboard, cannot upload textbooks, cannot alter curriculum.
- **Role `parent`:** Can view analytics, progress heatmaps, learning gains, weak areas, and manage student settings.
- **Role `admin`:** Can upload textbook PDFs, inspect and approve extracted concepts, and curate questions.

## 3. Input Validation & Defense in Depth
- Pydantic v2 schemas enforce strict types, string limits, and payload validation.
- SQL injection is eliminated via SQLAlchemy 2.0 parameterized statements.
- File upload validation checks magic bytes, MIME types, and file size quotas (maximum 25MB).
