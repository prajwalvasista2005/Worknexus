import sys
import json
from pathlib import Path
from ml.course_selection.course_selector import select_course_candidates, DEFAULT_OUTPUT_ARTIFACT_PATH

def main():
    print("=" * 70)
    print("PHASE 7E: COURSE SELECTION CANDIDATES PIPELINE")
    print("=" * 70)

    try:
        result = select_course_candidates()
    except Exception as e:
        print(f"Error running Phase 7E course selection: {e}")
        sys.exit(1)

    meta = result.get("metadata", {})
    students = result.get("students", [])
    global_usage = result.get("global_course_usage", [])
    errors = result.get("errors", [])

    print(f"\nPipeline: {meta.get('pipeline')}")
    print(f"Phase: {meta.get('phase')}")
    print(f"Total Students: {meta.get('total_students')}")
    print(f"Total Personalized Recommended Skills: {meta.get('total_personalized_skills')}")
    print(f"Total Unique Candidate Courses: {meta.get('total_candidate_courses')}")
    print(f"Total Uncovered Personalized Skills: {meta.get('total_uncovered_personalized_skills')}")
    print(f"Scope: {meta.get('scope_note')}")
    print(f"Output Artifact: {DEFAULT_OUTPUT_ARTIFACT_PATH}")

    print("\n" + "=" * 70)
    print("PER-STUDENT COURSE SELECTION CANDIDATES")
    print("=" * 70)

    for stu in students:
        s_id = stu["student_id"]
        role = stu["role"]["role_name"]
        role_id = stu["role"]["role_id"]
        summary = stu["summary"]
        recs = stu["personalized_skill_ids"]
        candidates = stu["candidate_courses"]
        uncovered = stu["uncovered_personalized_skills"]

        print(f"\nStudent: {s_id} | Target Role: {role} ({role_id})")
        print(f"  Personalized Recommendations ({len(recs)}): {', '.join(recs) if recs else 'None'}")
        print(f"  Summary: {summary['candidate_course_count']} candidate course(s), {summary['covered_personalized_skill_count']} covered skill(s), {summary['uncovered_personalized_skill_count']} uncovered skill(s)")

        if candidates:
            print("  Candidate Courses:")
            for c in candidates:
                skills_str = ", ".join(c["covered_personalized_skill_ids"])
                print(f"    - Course {c['course_id']}: \"{c['course_name']}\" -> Covers {c['covered_personalized_skill_count']} skill(s): [{skills_str}]")
        else:
            print("  Candidate Courses: None")

        if uncovered:
            print(f"  Uncovered Skills: {', '.join(uncovered)}")

    print("\n" + "=" * 70)
    print("GLOBAL COURSE USAGE (CANDIDATE INTERSECTION)")
    print("=" * 70)

    for gu in global_usage:
        stus_str = ", ".join(gu["candidate_for_students"])
        print(f"  - Course {gu['course_id']}: \"{gu['course_name']}\" -> Candidate for {len(gu['candidate_for_students'])} student(s): [{stus_str}]")

    if errors:
        print("\n" + "=" * 70)
        print("ERRORS / WARNINGS")
        print("=" * 70)
        for err in errors:
            print(f"  - [{err.get('type')}] {err.get('message')}")
    else:
        print("\nValidation: 0 Errors encountered.")

    print("\n" + "=" * 70)
    print("PHASE 7E EXECUTION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
