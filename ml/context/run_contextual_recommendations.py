import json
from pathlib import Path
from ml.context.contextual_recommender import ContextAwareRecommendationEngine

def main():
    print("==================================================")
    print("PHASE 6B: RUNNING CONTEXT-AWARE RECOMMENDATION ENGINE")
    print("==================================================")

    engine = ContextAwareRecommendationEngine()
    artifact, out_path = engine.run_and_save()

    meta = artifact["metadata"]
    print(f"Role Context Input:       {meta['role_context_input']}")
    print(f"Phase 6A Rec Input:       {meta['recommendation_input']}")
    print(f"Phase 5B Evidence Input:  {meta['evidence_input']}")
    print(f"Output Artifact:          {out_path}")
    print(f"Total Target Roles:       {meta['total_roles']}")
    print(f"Total Role-Skill Mappings:{meta['total_role_skill_mappings']}")
    print(f"Total Contextual Recs:    {meta['total_contextual_recommendations']}")
    print(f"Total Context Records:    {meta['total_role_skill_context_records']}")
    print()

    print("ROLE CONTEXTUAL RECOMMENDATION BREAKDOWN:")
    for role in artifact["roles"]:
        print("--------------------------------------------------")
        print(f"Role: {role['role_name']} [{role['role_id']}]")
        print(f"  Target Skills Total:      {role['target_skill_count']}")
        print(f"  • Recommended by Evidence:{role['recommended_target_skill_count']}")
        print(f"  • Not Recommended:        {role['not_recommended_target_skill_count']}")
        print(f"  • Unavailable in 6A:      {role['unavailable_target_skill_count']}")
        print("  Contextual Recommendations:")
        if role["contextual_recommendations"]:
            for r in role["contextual_recommendations"]:
                reasons = ", ".join(r["generic_recommendation"]["reason_ids"])
                print(f"    - {r['skill_id']} ({r['skill_name']}) [{r['category']}] -> {reasons}")
        else:
            print("    (None)")
        print("  Full Role Skill Context:")
        for item in role["role_skill_context"]:
            print(f"    * {item['skill_id']}: status={item['generic_recommendation_status']}, reason={item['context_reason']['reason_id']}")

    print("==================================================")
    print("PHASE 6B EXECUTION COMPLETE.")
    print("==================================================")

if __name__ == "__main__":
    main()
