import pytest
import io
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token
from tests.fixtures.ncert_pdf_generator import generate_class_8_combustion_textbook_pdf


@pytest.mark.asyncio
async def test_unauthorized_upload_rejected(client: AsyncClient):
    """Verifies that unauthenticated requests cannot upload curriculum."""
    pdf_bytes = generate_class_8_combustion_textbook_pdf()
    response = await client.post(
        "/api/v1/curriculum/upload",
        files={"file": ("textbook.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_student_forbidden_from_curriculum_upload(client: AsyncClient):
    """Verifies that students cannot upload curriculum documents (admin/parent only)."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "krish@school.edu", "password": "krish123"},
    )
    assert login_res.status_code == 200
    student_token = login_res.json()["access_token"]

    pdf_bytes = generate_class_8_combustion_textbook_pdf()
    response = await client.post(
        "/api/v1/curriculum/upload",
        headers={"Authorization": f"Bearer {student_token}"},
        files={"file": ("textbook.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_mime_and_magic_bytes_rejected(client: AsyncClient):
    """Verifies rejection of non-PDF or spoofed files."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "parent@school.edu", "password": "parent123"},
    )
    assert login_res.status_code == 200
    parent_token = login_res.json()["access_token"]

    # 1. Non-pdf extension
    txt_file = b"This is a text file, not a PDF."
    resp1 = await client.post(
        "/api/v1/curriculum/upload",
        headers={"Authorization": f"Bearer {parent_token}"},
        files={"file": ("notes.txt", io.BytesIO(txt_file), "text/plain")},
    )
    assert resp1.status_code == 400

    # 2. Spoofed extension with fake magic bytes
    fake_pdf = b"NOT_A_REAL_PDF_HEADER_JUST_RANDOM_TEXT_HERE"
    resp2 = await client.post(
        "/api/v1/curriculum/upload",
        headers={"Authorization": f"Bearer {parent_token}"},
        files={"file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert resp2.status_code == 400
    assert "Invalid file signature" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_valid_pdf_upload_and_duplicate_prevention(client: AsyncClient):
    """Verifies valid upload returns 202 Accepted and duplicate upload is detected."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "parent@school.edu", "password": "parent123"},
    )
    assert login_res.status_code == 200
    parent_token = login_res.json()["access_token"]
    pdf_bytes = generate_class_8_combustion_textbook_pdf()

    # Initial Upload
    resp1 = await client.post(
        "/api/v1/curriculum/upload",
        headers={"Authorization": f"Bearer {parent_token}"},
        files={"file": ("ncert_class8_combustion.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp1.status_code == 202
    data1 = resp1.json()
    assert data1["is_duplicate"] is False
    assert data1["status"] == "UPLOADED"
    doc_id = data1["document_id"]

    # Duplicate Upload with same content
    resp2 = await client.post(
        "/api/v1/curriculum/upload",
        headers={"Authorization": f"Bearer {parent_token}"},
        files={"file": ("duplicate_upload.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp2.status_code == 202
    data2 = resp2.json()
    assert data2["is_duplicate"] is True
    assert data2["document_id"] == doc_id
    assert "already been uploaded" in data2["message"]
