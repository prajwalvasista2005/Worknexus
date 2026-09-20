import json
from pathlib import Path
from ml.course_mapping.course_mapper import PersonalizedCourseMapper

def main():
    print("==================================================")
    print("PHASE 7D: RUNNING PERSONALIZED COURSE / SKILL MAPPING")
    print("==================================================")

    mapper = PersonalizedCourseMapper()
    artifact, out_path = mapper.run_and_save()

    meta = artifact["metadata"]
    print(f"Output Artifact:            {out_path}")
    print(f"Taxonomy Version:           {meta['taxonomy_version']}")
    print(f"Total Students:             {meta['total_students']}")
    print(f"Total Personalized Skills:  {meta['total_personalized_skills']}")
    print(f"  • Covered by Courses:     {meta['total_covered_personalized_skills']}")
    print(f"  • Not Covered by Courses: {meta['total_not_covered_personalized_skills']}")
    print()

    print("STUDENT PERSONALIZED SKILL-TO-COURSE MAPPING:")
    for stu in artifact["students"]:
        print("--------------------------------------------------")
        role_name = stu["role"]["role_name"]
        role_id = stu["role"]["role_id"]
        print(f"Student: {stu['student_id']} (Assigned: {role_name} [{role_id}])")
        print(f"  Personalized Recommendations: {stu['summary']['total_personalized_skills']}")
        print(f"  • Covered:     {stu['summary']['covered_personalized_skills']}")
        print(f"  • Not Covered: {stu['summary']['not_covered_personalized_skills']}")
        print("  Skill Course Coverage:")
        for m in stu["skill_course_mapping"]:
            status_tag = m["coverage_status"].upper()
            if m["matching_courses"]:
                courses_str = ", ".join([f"Course {c['course_id']} ({c['course_name']})" for c in m["matching_courses"]])
                print(f"    * {m['skill_id']:<18} ({m['skill_name']:<30}) -> [{status_tag}] in: {courses_str}")
            else:
                print(f"    * {m['skill_id']:<18} ({m['skill_name']:<30}) -> [{status_tag}] (No matching course in catalog)")

    print()
    print("GLOBAL SKILL-TO-COURSE CATALOG SUMMARY (SAMPLE):")
    covered_global = [g for g in artifact["global_skill_course_mapping"] if g["coverage_status"] == "covered"]
    print(f"Total Canonical Skills in Catalog: {len(covered_global)} / {len(artifact['global_skill_course_mapping'])}")
    for g in covered_global[:10]:
        c_names = ", ".join([f"{c['course_id']}:{c['course_name']}" for c in g["courses_containing_skill"]])
        print(f"  • {g['skill_id']:<18} ({g['skill_name']:<30}) -> [{c_names}]")
    print("  ...")

    print("==================================================")
    print("PHASE 7D EXECUTION COMPLETE.")
    print("==================================================")

if __name__ == "__main__":
    main()
