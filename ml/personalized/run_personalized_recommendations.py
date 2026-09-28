import json
from pathlib import Path
from ml.personalized.personalized_recommender import PersonalizedSkillRecommendationEngine

def main():
    print("==================================================")
    print("PHASE 7C: RUNNING PERSONALIZED SKILL RECOMMENDATION ENGINE")
    print("==================================================")

    engine = PersonalizedSkillRecommendationEngine()
    artifact, out_path = engine.run_and_save()

    meta = artifact["metadata"]
    print(f"Output Artifact:            {out_path}")
    print(f"Taxonomy Version:           {meta['taxonomy_version']}")
    print(f"Total Students:             {meta['total_students']}")
    print(f"Total Role-Skill Records:   {meta['total_role_skill_records']}")
    print(f"  • Personalized Recs:      {meta['total_personalized_recommendations']}")
    print(f"  • Already Present Skills: {meta['total_already_present_skills']}")
    print(f"  • Not Recommended Gaps:   {meta['total_not_recommended_missing_skills']}")
    print(f"  • Unavailable Context:    {meta['total_unavailable_context_skills']}")
    print()

    print("PERSONALIZED SKILL RECOMMENDATIONS BREAKDOWN:")
    for stu in artifact["students"]:
        print("--------------------------------------------------")
        role_name = stu["role"]["role_name"]
        role_id = stu["role"]["role_id"]
        print(f"Student: {stu['profile_name']} [{stu['student_id']}]")
        print(f"Target Role: {role_name} [{role_id}]")
        print(f"  Total Role Skills:          {stu['summary']['total_role_skills']}")
        print(f"  • Already Present ({stu['summary']['already_present_count']}):         {', '.join(stu['already_present_skills']) if stu['already_present_skills'] else '(None)'}")
        print(f"  • Recommended Gaps ({stu['summary']['recommended_skill_count']}):        {', '.join(stu['recommended_skills']) if stu['recommended_skills'] else '(None)'}")
        print(f"  • Not Recommended Gaps ({stu['summary']['not_recommended_missing_count']}):    {', '.join(stu['not_recommended_skills']) if stu['not_recommended_skills'] else '(None)'}")
        print(f"  • Unavailable Context ({stu['summary']['unavailable_context_count']}):     {stu['summary']['unavailable_context_count']}")
        print("  Personalized Skill Recommendations:")
        if stu["recommended_skills"]:
            for r in stu["skill_recommendations"]:
                if r["personalized_status"] == "recommended":
                    reasons = ", ".join(r["recommendation_reason_ids"])
                    print(f"    * [REC] {r['skill_id']:<18} ({r['skill_name']:<30}) [{r['category']:<24}] -> [{reasons}]")
        else:
            print("    (No missing skills meet generic recommendation criteria)")

        print("  Non-Recommended / Present Records:")
        for r in stu["skill_recommendations"]:
            if r["personalized_status"] != "recommended":
                tag = r["personalized_status"].upper()
                reasons = ", ".join(r["recommendation_reason_ids"])
                print(f"    • {r['skill_id']:<18} ({r['skill_name']:<30}) -> [{tag}] [{reasons}]")

    print("==================================================")
    print("PHASE 7C EXECUTION COMPLETE.")
    print("==================================================")

if __name__ == "__main__":
    main()
