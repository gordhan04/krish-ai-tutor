# Child Safety, Privacy & Security Architecture

## 1. Child Privacy Standards
KRISH AI TUTOR is built strictly for educational interaction:
- **Zero Advertising or Third-Party Tracking:** No behavioral trackers, ad SDKs, or external trackers.
- **Minimal PII:** Only internal pseudonymous IDs are passed to LLMs. Krish's personal details (address, phone, location) are never requested or stored.
- **No Inappropriate Conversational Roles:** The AI is strictly an academic tutor, never a therapist, romantic companion, or unfiltered open-ended chatbot. Any non-academic queries are gently redirected to learning.

## 2. Role-Based Access Control (RBAC)
- **Role `student`:** Can access published curriculum, participate in lessons, submit answers, earn XP, and view their own learning stats. Strictly forbidden (HTTP 403) from uploading curriculum PDFs, accessing ingestion endpoints, modifying concept status, or accessing parent analytics.
- **Role `parent`:** Can view analytics, progress heatmaps, learning gains, weak areas, upload textbook PDFs, and review/publish curriculum units.
- **Role `admin`:** Full system access: upload textbook PDFs, inspect pipeline telemetry, approve/publish extracted curriculum units, and curate question rubrics.

## 3. Curriculum Ingestion & Upload Security
- **Strict Multipart PDF Validation**: Inspects MIME type (`application/pdf`), file extension (`.pdf`), and initial magic bytes (`%PDF-`). Non-PDF files or spoofed headers are immediately rejected (HTTP 400).
- **Size Quota**: Enforces a 50MB ceiling to prevent denial-of-service memory exhaustion.
- **Idempotent SHA-256 Hashing**: Prevents redundant processing and accidental duplicate uploads.
- **Pydantic v2 Payload Guarding**: All JSON schemas strictly validate field lengths, types, and required parameters.
- **SQL Injection Defense**: Eliminated via SQLAlchemy 2.0 async parameterized ORM statements.
- **Prompt Injection Defense**: Retrieved textbook chunks are isolated in `<curriculum_data>` tags separate from `<system_instructions>` and `<student_message>` blocks.
