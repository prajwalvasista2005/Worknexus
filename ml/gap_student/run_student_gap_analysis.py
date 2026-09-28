import json
from pathlib import Path
from ml.gap_student.student_gap_analyzer import StudentSkillGapAnalyzer

def main():
    print("==================================================")
    print("PHASE 7B: RUNNING STUDENT SKILL GAP ANALYSIS")
    print("==================================================")

    analyzer = StudentSkillGapAnalyzer()
    artifact, out_path = analyzer.run_and_save()

    meta = artifact["metadata"]
    print(f"Output Artifact:            {out_path}")
    print(f"Taxonomy Version:           {meta['taxonomy_version']}")
    print(f"Total Students:             {meta['total_students']}")
    print(f"Total Assignments:          {meta['total_assignments']}")
    print(f"Total Role-Skill Records:   {meta['total_role_skill_records']}")
    print(f"  • Present Skills:         {meta['total_present_skills']}")
    print(f"  • Missing Skills:         {meta['total_missing_skills']}")
    print(f"  • Unavailable Context:    {meta['total_unavailable_context_skills']}")
    print()

    print("STUDENT SKILL GAP COMPARISON BREAKDOWN:")
    for stu in artifact["students"]:
        print("--------------------------------------------------")
        role_name = stu["role"]["role_name"]
        role_id = stu["role"]["role_id"]
        print(f"Student: {stu['profile_name']} [{stu['student_id']}]")
        print(f"Assigned Role: {role_name} [{role_id}]")
        print(f"  Total Role Skills:        {stu['summary']['total_role_skills']}")
        print(f"  • Present Skills ({stu['summary']['present_skill_count']}):       {', '.join(stu['present_skills']) if stu['present_skills'] else '(None)'}")
        print(f"  • Missing Skills ({stu['summary']['missing_skill_count']}):       {', '.join(stu['missing_skills']) if stu['missing_skills'] else '(None)'}")
        print(f"  • Unavailable Context ({stu['summary']['unavailable_context_count']}):  {', '.join(stu['unavailable_context_skills']) if stu['unavailable_context_skills'] else '(None)'}")
        print("  Detailed Gap Records:")
        for gap in stu["skill_gaps"]:
            status_tag = gap["status"].upper()
            ctx_tag = f"ctx={gap['contextual_recommendation_status']}"
            if gap["status"] == "present":
                ev_str = ", ".join([f"{e['evidence_type']}:{e['evidence_strength']}" for e in gap["student_evidence"]])
                print(f"    - {gap['skill_id']:<18} ({gap['skill_name']:<30}) -> [{status_tag}] ({ctx_tag}) evidence=[{ev_str}]")
            else:
                print(f"    - {gap['skill_id']:<18} ({gap['skill_name']:<30}) -> [{status_tag}] ({ctx_tag})")

    print("==================================================")
    print("PHASE 7B EXECUTION COMPLETE.")
    print("==================================================")

if __name__ == "__main__":
    main()
