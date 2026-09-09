import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, Student


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    """Unauthenticated requests without Bearer token must return 401 Unauthorized."""
    res = await client.get("/api/v1/student/dashboard")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_role_based_access_control(client: AsyncClient):
    """A student token must be forbidden from accessing the parent dashboard (403)."""
    # 1. Login as student Krish
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "krish@school.edu", "password": "krish123"},
    )
    assert login_res.status_code == 200
    student_token = login_res.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Student trying to access parent dashboard -> 403 Forbidden
    parent_res = await client.get("/api/v1/parent/dashboard", headers=student_headers)
    assert parent_res.status_code == 403
    assert "Access denied" in parent_res.json()["detail"]

    # 2. Login as parent
    p_login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "parent@school.edu", "password": "parent123"},
    )
    assert p_login_res.status_code == 200
    parent_token = p_login_res.json()["access_token"]
    parent_headers = {"Authorization": f"Bearer {parent_token}"}

    # Parent accessing parent dashboard -> 200 OK
    p_dash_res = await client.get("/api/v1/parent/dashboard", headers=parent_headers)
    assert p_dash_res.status_code == 200
    assert p_dash_res.json()["student_name"] == "Krish"


@pytest.mark.asyncio
async def test_session_idor_prevention(client: AsyncClient, db_session: AsyncSession):
    """Verifies that Student A cannot access or mutate Student B's learning session."""
    from app.core.security import create_access_token

    # 1. Login as Student Krish (Student A)
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "krish@school.edu", "password": "krish123"},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Start a session for Student A
    sub_res = await client.get("/api/v1/curriculum/subjects", headers=headers_a)
    topic = sub_res.json()[0]["books"][0]["chapters"][0]["sections"][0]["topics"][0]
    concept = topic["concepts"][0]

    sess_res = await client.post(
        "/api/v1/tutor/lesson/start",
        json={"topic_id": topic["id"], "concept_id": concept["id"]},
        headers=headers_a,
    )
    session_id_a = sess_res.json()["session_id"]

    # 3. Create real Student B in database
    user_b = User(email="other_student@school.edu", hashed_password="pw", role="student")
    db_session.add(user_b)
    await db_session.flush()
    student_b = Student(user_id=user_b.id, display_name="Other Student", grade_level=8)
    db_session.add(student_b)
    await db_session.commit()

    token_b = create_access_token(
        data={"sub": user_b.id, "role": "student", "student_id": student_b.id}
    )
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 4. Student B attempts to call /hint on Student A's session -> 403 Forbidden
    hint_res = await client.post(
        "/api/v1/tutor/hint",
        json={"session_id": session_id_a, "question_prompt": "Test prompt"},
        headers=headers_b,
    )
    assert hint_res.status_code == 403
    assert "Access denied" in hint_res.json()["detail"]

    # 5. Student B attempts to call /complete on Student A's session -> 403 Forbidden
    complete_res = await client.post(
        "/api/v1/tutor/complete",
        json={"session_id": session_id_a},
        headers=headers_b,
    )
    assert complete_res.status_code == 403

    # 6. Student B attempts voice interaction on Student A's session -> 403 Forbidden
    voice_res = await client.post(
        "/api/v1/voice/interact",
        json={"session_id": session_id_a, "transcript": "Hello", "mode": "teach"},
        headers=headers_b,
    )
    assert voice_res.status_code == 403


@pytest.mark.asyncio
async def test_parent_cannot_view_unauthorized_student(client: AsyncClient, db_session: AsyncSession):
    """Verifies that a parent not linked to any child cannot view another parent's child."""
    from app.core.security import create_access_token

    # Create an unlinked parent in database
    parent_b = User(email="other_parent@school.edu", hashed_password="pw", role="parent")
    db_session.add(parent_b)
    await db_session.commit()

    token_p = create_access_token(
        data={"sub": parent_b.id, "role": "parent"}
    )
    headers_p = {"Authorization": f"Bearer {token_p}"}

    # Unlinked parent attempting to access /parent/dashboard -> 404 Not Found
    dash_res = await client.get("/api/v1/parent/dashboard", headers=headers_p)
    assert dash_res.status_code == 404
    assert "No authorized student" in dash_res.json()["detail"]

