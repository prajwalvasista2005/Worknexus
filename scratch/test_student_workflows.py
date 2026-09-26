import sys
sys.path.extend([".", "backend"])

from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

# Login as student
res = c.post("/api/v1/auth/login", json={"email": "student@worknexus.io", "password": "SecurePassword123!"})
print("Login status:", res.status_code)
tok = res.json()["access_token"]
headers = {"Authorization": f"Bearer {tok}"}

# Me
me = c.get("/api/v1/auth/me", headers=headers).json()
print("Student ID:", me["id"], "Email:", me["email"])

# Roles
roles = c.get("/api/v1/roles/", headers=headers).json()
print("Total roles:", len(roles))
first_role = roles[0]["id"]
print("Testing role:", first_role)

# Gap
gap = c.get(f"/api/v1/ml/students/{me['id']}/gap/{first_role}", headers=headers).json()
print("Gap summary:", gap.get("summary"))
print("Missing skills count:", len(gap.get("missing_skills", [])))
print("First missing skill:", gap.get("missing_skills", [])[:2])

# Course candidates
candidates = c.get(f"/api/v1/ml/students/{me['id']}/course-candidates/{first_role}", headers=headers).json()
print("Candidate courses count:", len(candidates.get("candidate_courses", [])))
print("Candidate courses:", candidates.get("candidate_courses"))

# Recommendations
recs = c.get(f"/api/v1/ml/students/{me['id']}/recommendations/{first_role}", headers=headers).json()
print("Personalized recs:", recs.get("summary"))
