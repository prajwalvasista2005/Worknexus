import json
from pathlib import Path

def run_phase0_check():
    data_dir = Path(__file__).parent / "data"

    files = {
        "skills.json": data_dir / "skills.json",
        "sample_job_postings.json": data_dir / "sample_job_postings.json",
        "sample_courses.json": data_dir / "sample_courses.json",
        "sample_employer_feedback.json": data_dir / "sample_employer_feedback.json"
    }

    loaded_data = {}
    print("========================================")
    print("WorkNexus / SkillMesh — Phase 0 Data Validation")
    print("========================================\n")

    for filename, filepath in files.items():
        if not filepath.exists():
            raise FileNotFoundError(f"Missing required file: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            loaded_data[filename] = data
            print(f"[OK] {filename}: {len(data)} items loaded")
            print(f"     Example item: {json.dumps(data[0], indent=2)}\n")

    # Verification: EV Technician course checks
    courses = loaded_data["sample_courses.json"]
    ev_course = next((c for c in courses if c.get("name") == "EV Technician" or c.get("course_id") == 42), None)

    if not ev_course:
        raise ValueError("Course 'EV Technician' (course_id: 42) not found!")

    ev_skills = ev_course.get("skill_ids", [])
    print("----------------------------------------")
    print(f"Checking Course: {ev_course.get('name')} (ID: {ev_course.get('course_id')})")
    print(f"Covered Skill IDs: {ev_skills}")
    print(f"Coverage Map: {ev_course.get('coverage')}")

    has_can = "SK_CAN" in ev_skills
    print(f"Is 'SK_CAN' missing from skill_ids? {not has_can}")
    assert not has_can, "Error: SK_CAN should NOT be present in EV Technician course skills for gap demo!"

    print("\n[SUCCESS] Phase 0 validation passed completely!")
    print("========================================")

if __name__ == "__main__":
    run_phase0_check()
