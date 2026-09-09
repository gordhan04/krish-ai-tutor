import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unified_voice_interaction(client: AsyncClient):
    # 1. Login as Student Krish
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "krish@school.edu", "password": "krish123"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Start Lesson to obtain session_id
    sub_res = await client.get("/api/v1/curriculum/subjects", headers=headers)
    science = sub_res.json()[0]
    topic = science["books"][0]["chapters"][0]["sections"][0]["topics"][0]

    lesson_res = await client.post(
        "/api/v1/tutor/lesson/start",
        json={"topic_id": topic["id"]},
        headers=headers,
    )
    session_id = lesson_res.json()["session_id"]

    # 3. Verbal Socratic check in Voice Mode 'socratic'
    voice_res = await client.post(
        "/api/v1/voice/interact",
        json={
            "session_id": session_id,
            "transcript": "I predict the bulb will glow because salt water conducts electricity.",
            "mode": "socratic",
        },
        headers=headers,
    )
    assert voice_res.status_code == 200
    voice_data = voice_res.json()
    assert voice_data["session_id"] == session_id
    assert len(voice_data["tutor_text_response"]) > 0
    assert voice_data["audio_synthesis_instructions"]["engine"] == "web_speech_synthesis"
    assert voice_data["next_mode"] == "quiz"
