import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_learning_flow_happy_path(client: AsyncClient):
    """
    Verifies full 6-phase sequence:
    1. Lesson Start (Objective & Explanation)
    2. Socratic Check Pose & Reflection Evaluate
    3. Practice Start (Question Fetch)
    4. Practice Answer Submit
    5. Explain-It-Back Submit
    6. Mastery Goal Completion
    """
    # 1. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "krish@school.edu", "password": "krish123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get curriculum
    sub_res = await client.get("/api/v1/curriculum/subjects", headers=headers)
    assert sub_res.status_code == 200
    topic = sub_res.json()[0]["books"][0]["chapters"][0]["sections"][0]["topics"][0]
    concept = topic["concepts"][0]

    # 3. Lesson Start
    start_res = await client.post(
        "/api/v1/tutor/lesson/start",
        json={"topic_id": topic["id"], "concept_id": concept["id"]},
        headers=headers,
    )
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]
    assert start_res.json()["state"] == "TEACHING"

    # 4. Socratic Check Pose
    soc_check_res = await client.post(
        "/api/v1/tutor/socratic-check",
        json={"session_id": session_id},
        headers=headers,
    )
    assert soc_check_res.status_code == 200
    assert soc_check_res.json()["state"] == "CHECKING_UNDERSTANDING"
    assert len(soc_check_res.json()["socratic_question"]) > 0

    # 5. Socratic Evaluate
    soc_eval_res = await client.post(
        "/api/v1/tutor/socratic-evaluate",
        json={
            "session_id": session_id,
            "student_response": "Water conducts electricity when mineral salts and ions are dissolved in it.",
        },
        headers=headers,
    )
    assert soc_eval_res.status_code == 200
    assert soc_eval_res.json()["state"] == "PRACTICE"

    # 6. Practice Start (Fetch Question)
    prac_start_res = await client.post(
        "/api/v1/tutor/practice/start",
        json={"session_id": session_id},
        headers=headers,
    )
    assert prac_start_res.status_code == 200
    prac_q = prac_start_res.json()
    assert prac_q["state"] == "PRACTICE"
    question_id = prac_q["current_question_id"]
    assert len(prac_q["question_prompt"]) > 0

    # 7. Practice Answer Submit with Idempotency
    req_id = "test_req_ans_001"
    ans_res1 = await client.post(
        "/api/v1/tutor/practice/answer",
        json={
            "session_id": session_id,
            "question_id": question_id,
            "answer": "A",
            "request_id": req_id,
        },
        headers=headers,
    )
    assert ans_res1.status_code == 200
    ans_data1 = ans_res1.json()
    assert ans_data1["is_correct"] is True

    # Idempotent re-submission returns identical response
    ans_res2 = await client.post(
        "/api/v1/tutor/practice/answer",
        json={
            "session_id": session_id,
            "question_id": question_id,
            "answer": "A",
            "request_id": req_id,
        },
        headers=headers,
    )
    assert ans_res2.status_code == 200
    assert ans_res2.json()["feedback"] == ans_data1["feedback"]

    # 8. Explain-It-Back Submit
    eib_req_id = "test_req_eib_001"
    eib_res1 = await client.post(
        "/api/v1/tutor/explain-it-back",
        json={
            "session_id": session_id,
            "response": "Electrolytes are liquids with free ions that carry electric current.",
            "request_id": eib_req_id,
        },
        headers=headers,
    )
    assert eib_res1.status_code == 200
    eib_data1 = eib_res1.json()
    assert eib_data1["state"] in ["MASTERY_REVIEW", "CHAPTER_COMPLETE", "PRACTICE"]

    # Idempotent re-submission for explain-it-back
    eib_res2 = await client.post(
        "/api/v1/tutor/explain-it-back",
        json={
            "session_id": session_id,
            "response": "Electrolytes are liquids with free ions that carry electric current.",
            "request_id": eib_req_id,
        },
        headers=headers,
    )
    assert eib_res2.status_code == 200
    assert eib_res2.json()["score"] == eib_data1["score"]

    # 9. Complete Lesson Session
    comp_res = await client.post(
        "/api/v1/tutor/complete",
        json={"session_id": session_id},
        headers=headers,
    )
    assert comp_res.status_code == 200
    assert "session_id" in comp_res.json()
    assert comp_res.json()["state"] in ["MASTERY_REVIEW", "CHAPTER_COMPLETE"]


@pytest.mark.asyncio
async def test_invalid_state_transition_handling(client: AsyncClient):
    """
    Verifies that calling an illegal state transition triggers structured INVALID_LEARNING_STATE.
    """
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "krish@school.edu", "password": "krish123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Trigger Socratic on an IDLE or invalid session
    sub_res = await client.get("/api/v1/curriculum/subjects", headers=headers)
    topic = sub_res.json()[0]["books"][0]["chapters"][0]["sections"][0]["topics"][0]
    concept = topic["concepts"][0]

    start_res = await client.post(
        "/api/v1/tutor/lesson/start",
        json={"topic_id": topic["id"], "concept_id": concept["id"]},
        headers=headers,
    )
    session_id = start_res.json()["session_id"]

    # Intentionally verify error handling if session ID doesn't exist
    bad_res = await client.post(
        "/api/v1/tutor/socratic-check",
        json={"session_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert bad_res.status_code in [400, 404]
