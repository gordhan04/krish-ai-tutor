import pytest
from httpx import AsyncClient


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
