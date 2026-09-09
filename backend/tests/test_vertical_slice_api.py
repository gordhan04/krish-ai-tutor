import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_vertical_slice_api(client: AsyncClient):
    # 1. Login as Student Krish
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "krish@school.edu", "password": "krish123"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert token_data["display_name"] == "Krish"
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Student Dashboard
    dash_res = await client.get("/api/v1/student/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["display_name"] == "Krish"
    assert "Chemical Effects" in dash["daily_mission"]["title"]

    # 3. Retrieve Subjects & Chapters
    sub_res = await client.get("/api/v1/curriculum/subjects", headers=headers)
    assert sub_res.status_code == 200
    subjects = sub_res.json()
    assert len(subjects) > 0
    science = subjects[0]
    chapter = science["books"][0]["chapters"][0]
    topic = chapter["sections"][0]["topics"][0]
    concept = topic["concepts"][0]

    # 4. Start Lesson Session
    lesson_res = await client.post(
        "/api/v1/tutor/lesson/start",
        json={"topic_id": topic["id"], "concept_id": concept["id"]},
        headers=headers,
    )
    assert lesson_res.status_code == 200
    lesson = lesson_res.json()
    session_id = lesson["session_id"]
    assert "Electrolytes" in lesson["concept_name"]
    assert len(lesson["message"]) > 0

    # 5. Fetch Practice Question
    q_res = await client.get(
        f"/api/v1/assessment/question?topic_id={topic['id']}&concept_id={concept['id']}",
        headers=headers,
    )
    assert q_res.status_code == 200
    question = q_res.json()
    assert len(question["prompt"]) > 0

    # 6. Request a Progressive Hint
    hint_res = await client.post(
        "/api/v1/tutor/hint",
        json={"session_id": session_id, "question_prompt": question["prompt"]},
        headers=headers,
    )
    assert hint_res.status_code == 200
    hint = hint_res.json()
    assert hint["hint_level"] == 1

    # 7. Submit Answer to Question
    ans_res = await client.post(
        "/api/v1/assessment/answer",
        json={
            "question_id": question["id"],
            "student_answer": "",
            "selected_option_key": "A",
            "session_id": session_id,
        },
        headers=headers,
    )
    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert ans_data["is_correct"] is True
    assert ans_data["xp_awarded"] > 0
    assert ans_data["mastery_score"] > 0.0

    # 8. Verify Parent Dashboard Reflects Krish's Progress
    p_login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "parent@school.edu", "password": "parent123"},
    )
    assert p_login_res.status_code == 200
    p_token = p_login_res.json()["access_token"]
    parent_headers = {"Authorization": f"Bearer {p_token}"}

    parent_res = await client.get("/api/v1/parent/dashboard", headers=parent_headers)
    assert parent_res.status_code == 200
    parent_data = parent_res.json()
    assert parent_data["student_name"] == "Krish"
    assert parent_data["overall_accuracy"] > 0
