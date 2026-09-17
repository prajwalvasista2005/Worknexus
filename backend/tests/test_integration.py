import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_system_flow():
    # 1. Health check
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    # 2. Register new user
    uid = uuid.uuid4().hex[:8]
    email = f"user_{uid}@example.com"
    password = "StrongPassword123!"

    reg_res = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"Test User {uid}",
            "role": "student",
        },
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == email

    # 3. Login with JSON credentials
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 4. Authenticated profile inspection
    me_res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 5. Token Refresh
    ref_res = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_res.status_code == 200
    new_tokens = ref_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    new_access = new_tokens["access_token"]
    new_refresh = new_tokens["refresh_token"]

    # Old refresh token is revoked
    old_ref_res = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert old_ref_res.status_code == 401

    # 6. Create Skill
    skill_code = f"SKL-{uid}"
    skill_res = client.post(
        "/skills/",
        json={
            "skill_id": skill_code,
            "name": f"Skill {uid}",
            "category": "Technology",
            "description": "Integration test skill",
        },
    )
    assert skill_res.status_code == 201
    skill_obj = skill_res.json()
    skill_pk = skill_obj["id"]

    # 7. Add skill to user profile
    user_skill_res = client.post(
        "/user-skills/",
        headers={"Authorization": f"Bearer {new_access}"},
        json={
            "skill_id": skill_pk,
            "proficiency_level": "intermediate",
            "source": "assessment",
        },
    )
    assert user_skill_res.status_code == 201
    user_skill_obj = user_skill_res.json()
    assert user_skill_obj["skill_id"] == skill_pk

    # 8. List my skills
    my_skills_res = client.get(
        "/user-skills/me",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert my_skills_res.status_code == 200
    assert any(s["skill_id"] == skill_pk for s in my_skills_res.json())

    # 9. Create Course
    course_code = f"CRS-{uid}"
    course_res = client.post(
        "/courses/",
        json={
            "course_id": course_code,
            "name": f"Course {uid}",
            "description": "Integration test course",
            "department": "Computer Science",
            "semester": "Semester 1",
            "is_active": True,
        },
    )
    assert course_res.status_code == 201
    course_obj = course_res.json()
    course_pk = course_obj["id"]

    # 10. Map skill to course
    map_res = client.post(
        "/course-skills/",
        json={
            "course_id": course_pk,
            "skill_id": skill_pk,
        },
    )
    assert map_res.status_code == 201

    # 11. Verify course skills
    c_skills_res = client.get(f"/courses/{course_pk}/skills")
    assert c_skills_res.status_code == 200
    assert len(c_skills_res.json()) >= 1

    # 12. Create Job Posting
    job_res = client.post(
        "/job-postings",
        json={
            "title": f"Lead AI Engineer {uid}",
            "company_name": "NexTech Global",
            "description": "Building next-gen curriculum platforms",
            "location": "Bengaluru",
            "source": "Direct",
        },
    )
    assert job_res.status_code == 201
    job_obj = job_res.json()
    job_pk = job_obj["id"]
    assert job_obj["title"] == f"Lead AI Engineer {uid}"

    # 13. Get Job Posting
    get_job_res = client.get(f"/job-postings/{job_pk}")
    assert get_job_res.status_code == 200
    assert get_job_res.json()["id"] == job_pk

    # 14. List Job Postings
    list_jobs_res = client.get("/job-postings")
    assert list_jobs_res.status_code == 200
    assert any(j["id"] == job_pk for j in list_jobs_res.json())

    # 15. Map Skill to Job Posting
    map_job_skill_res = client.post(
        "/job-skills",
        json={
            "job_id": job_pk,
            "skill_id": skill_code,
        },
    )
    assert map_job_skill_res.status_code == 201
    js_obj = map_job_skill_res.json()
    js_pk = js_obj["id"]
    assert js_obj["job_id"] == job_pk
    assert js_obj["skill_id"] == skill_code

    # 16. Get Job Skill Mapping
    get_js_res = client.get(f"/job-skills/{js_pk}")
    assert get_js_res.status_code == 200
    assert get_js_res.json()["id"] == js_pk

    # 17. List Job Skills
    list_js_res = client.get(f"/job-skills?job_id={job_pk}")
    assert list_js_res.status_code == 200
    assert any(m["id"] == js_pk for m in list_js_res.json())

    # 18. Delete Job Skill Mapping
    del_js_res = client.delete(f"/job-skills/{js_pk}")
    assert del_js_res.status_code == 200

    # 19. Delete Job Posting
    del_job_res = client.delete(f"/job-postings/{job_pk}")
    assert del_job_res.status_code == 200

    # 20. Logout
    logout_res = client.post(
        "/auth/logout",
        json={"refresh_token": new_refresh},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"

    # Revoked token cannot be refreshed
    after_logout_ref = client.post(
        "/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert after_logout_ref.status_code == 401
