import json
from pathlib import Path
from ml.student.student_profile import StudentProfileEngine

def main():
    print("==================================================")
    print("PHASE 7A: RUNNING STUDENT SKILL PROFILE ENGINE")
    print("==================================================")

    engine = StudentProfileEngine()
    artifact, out_path = engine.run_and_save()

    meta = artifact["metadata"]
    print(f"Output Artifact:          {out_path}")
    print(f"Taxonomy Version:         {meta['taxonomy_version']}")
    print(f"Total Students:           {meta['total_students']}")
    print(f"Total Skill Records:      {meta['total_skill_records']}")
    print(f"Total Unique Skills:      {meta['total_unique_skills']}")
    print(f"Category Counts:          {meta['category_counts']}")
    print()

    print("STUDENT SKILL PROFILES BREAKDOWN:")
    for student in artifact["students"]:
        print("--------------------------------------------------")
        print(f"Student: {student['profile_name']} [{student['student_id']}]")
        print(f"  Skill Count:         {student['skill_count']}")
        print(f"  Categories Present:  {', '.join(student['categories_present'])}")
        print("  Current Skills & Evidence Provenance:")
        for sk in student["skills"]:
            ev_list = [f"{ev['evidence_type']}:{ev['evidence_strength']}" for ev in sk["evidence"]]
            ev_str = ", ".join(ev_list)
            print(f"    • {sk['skill_id']:<18} ({sk['skill_name']:<30}) [{sk['category']:<24}] -> [{ev_str}]")

    print("==================================================")
    print("PHASE 7A EXECUTION COMPLETE.")
    print("==================================================")

if __name__ == "__main__":
    main()
