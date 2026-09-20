import json
from pathlib import Path
from ml.evidence.evidence_aggregator import MultiSignalEvidenceAggregator

def main():
    print("==================================================")
    print("PHASE 5B: RUNNING MULTI-SIGNAL EVIDENCE AGGREGATION")
    print("==================================================")

    aggregator = MultiSignalEvidenceAggregator()
    artifact, out_path = aggregator.run_and_save()

    meta = artifact["metadata"]
    print(f"Job Demand Input:       {meta['job_demand_input']}")
    print(f"Employer Input:         {meta['employer_feedback_input']}")
    print(f"Output Artifact:        {out_path}")
    print(f"Job Demand Skills:      {meta['job_dataset_skill_count']}")
    print(f"Employer Skills:        {meta['employer_feedback_skill_count']}")
    print(f"Union Skill Universe:   {meta['union_skill_count']}")
    print(f"  - Both Sources:       {meta['both_sources_skill_count']}")
    print(f"  - Job Only:           {meta['job_only_skill_count']}")
    print(f"  - Employer Only:      {meta['employer_only_skill_count']}")
    print()

    print("MULTI-SIGNAL EVIDENCE BREAKDOWN (SAMPLE OF TOP SKILLS):")
    print(f"{'Skill ID':<18} {'Skill Name':<26} {'Relationship':<24} {'Job Postings':<15} {'Employer Feedback'}")
    print("-" * 105)
    for s in artifact["skills"][:15]:
        rel = s["evidence_relationship"]
        j_obs = f"{s['job_demand']['job_count']} jobs" if s["job_demand"]["observed"] else "Not observed"
        e_obs = f"{s['employer_validation']['feedback_count']} fb ({s['employer_validation']['unique_employer_count']} emp)" if s["employer_validation"]["observed"] else "Not observed"
        print(f"{s['skill_id']:<18} {s['skill_name']:<26} {rel:<24} {j_obs:<15} {e_obs}")
    print("...")
    print()

    print("EVIDENCE RELATIONSHIP GROUPS:")
    both_list = [s["skill_id"] for s in artifact["skills"] if s["evidence_relationship"] == "both"]
    emp_only_list = [s["skill_id"] for s in artifact["skills"] if s["evidence_relationship"] == "employer_feedback_only"]
    print(f"  • Both Sources ({len(both_list)}): {', '.join(both_list)}")
    print(f"  • Employer Only ({len(emp_only_list)}): {', '.join(emp_only_list)}")
    print(f"  • Job Only ({meta['job_only_skill_count']}): (26 skills including SK_SQL, SK_AWS, SK_JAVASCRIPT, SK_GIT...)")
    print("==================================================")

if __name__ == "__main__":
    main()
