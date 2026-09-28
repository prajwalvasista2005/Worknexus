import json
from pathlib import Path
from ml.recommend.recommendation_engine import GenericSkillRecommendationEngine

def main():
    print("==================================================")
    print("PHASE 6A: RUNNING GENERIC SKILL RECOMMENDATION ENGINE")
    print("==================================================")

    engine = GenericSkillRecommendationEngine()
    artifact, out_path = engine.run_and_save()

    meta = artifact["metadata"]
    print(f"Evidence Input Artifact:  {meta['evidence_input']}")
    print(f"Course Gap Input Artifact:{meta['course_gap_input']}")
    print(f"Output Artifact:          {out_path}")
    print(f"Rule Version:             {meta['recommendation_rule_version']}")
    print(f"Total Evaluated Skills:   {meta['total_skills']}")
    print(f"  • Recommended Skills:   {meta['recommended_skills']}")
    print(f"  • Not Recommended:      {meta['not_recommended_skills']}")
    print()

    print("RECOMMENDED SKILLS SUMMARY (SAMPLE):")
    print(f"{'Skill ID':<18} {'Skill Name':<25} {'Category':<16} {'Status':<15} {'Decision Reasons'}")
    print("-" * 115)
    for r in artifact["recommendations"][:15]:
        status = r["recommendation"]["status"]
        reasons_str = ", ".join(r["recommendation"]["reason_ids"]) if r["recommendation"]["reason_ids"] else "(No active conditions met)"
        print(f"{r['skill_id']:<18} {r['skill_name']:<25} {r['category']:<16} {status:<15} {reasons_str}")
    print("...")
    print()

    # Summarize recommendation categories
    both_rec = [r["skill_id"] for r in artifact["recommendations"] if r["recommendation"]["status"] == "recommended" and r["decision_factors"]["multi_source_evidence"]]
    gap_rec = [r["skill_id"] for r in artifact["recommendations"] if r["recommendation"]["status"] == "recommended" and "course_coverage_gap" in r["recommendation"]["reason_ids"]]
    emp_only_rec = [r["skill_id"] for r in artifact["recommendations"] if r["recommendation"]["status"] == "recommended" and "employer_only_signal" in r["recommendation"]["reason_ids"]]
    not_rec = [r["skill_id"] for r in artifact["recommendations"] if r["recommendation"]["status"] == "not_recommended"]

    print("RECOMMENDATION BREAKDOWN BY EVIDENCE CONDITION:")
    print(f"  1. Dual Evidence (Market + Employer): {len(both_rec)} skills ({', '.join(both_rec)})")
    print(f"  2. Market Demand + Course Gap:        {len(gap_rec)} skills (e.g. SK_AWS, SK_JAVASCRIPT, SK_REST_API, SK_GIT...)")
    print(f"  3. Employer-Only Signal:              {len(emp_only_rec)} skills ({', '.join(emp_only_rec)})")
    print(f"  4. Not Recommended (Covered in Course):{len(not_rec)} skills ({', '.join(not_rec)})")
    print("==================================================")

if __name__ == "__main__":
    main()
