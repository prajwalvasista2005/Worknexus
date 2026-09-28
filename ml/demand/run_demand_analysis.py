import json
from pathlib import Path
from ml.demand.demand_aggregator import DemandAggregator

def main():
    print("==================================================")
    print("PHASE 3: RUNNING SKILL DEMAND AGGREGATION & TRENDS")
    print("==================================================")
    
    aggregator = DemandAggregator()
    artifact, output_path = aggregator.run_and_save()
    
    meta = artifact["metadata"]
    print(f"Input artifact: {meta['input_artifact']}")
    print(f"Output artifact: {output_path}")
    print(f"Total Jobs Evaluated: {meta['total_jobs']}")
    print(f"Jobs with >=1 Skill: {meta['jobs_with_skills']}")
    print(f"Zero-Skill Jobs: {meta['zero_skill_jobs']}")
    print(f"Total Skill Mentions: {meta['total_skill_mentions']}")
    print(f"Unique Detected Skills: {meta['unique_skills_detected']}")
    print()

    print("TOP 10 IN-DEMAND SKILLS:")
    print(f"{'Rank':<5} {'Skill ID':<16} {'Skill Name':<25} {'Category':<18} {'Jobs':<6} {'Share (%)':<10} {'Sources':<8}")
    print("-" * 90)
    for idx, s in enumerate(artifact["skills"][:10], 1):
        print(f"{idx:<5} {s['skill_id']:<16} {s['skill_name']:<25} {s['category']:<18} {s['job_count']:<6} {s['demand_percentage']:>5.2f}%    {s['source_coverage_count']}/3")
    print()

    print("CATEGORY SUMMARY:")
    print(f"{'Category':<20} {'Skills':<8} {'Unique Jobs':<12} {'Job Coverage (%)':<16} {'Total Assignments':<18}")
    print("-" * 75)
    for c in artifact["categories"]:
        print(f"{c['category']:<20} {c['number_of_skills_detected']:<8} {c['unique_jobs_with_category_skill']:<12} {c['percentage_of_jobs_with_any_category_skill']:>6.2f}%           {c['total_skill_job_assignments']:<18}")
    print()

    print("SOURCE DISTRIBUTION:")
    for src, sdata in artifact["source_demand"].items():
        print(f"  - {src}: {sdata['source_total_jobs']} total jobs, {sdata['skills_detected_count']} unique skills detected")
    print()

    print("TOP 5 CO-OCCURRING SKILL PAIRS:")
    for idx, pair in enumerate(artifact["co_occurrence"][:5], 1):
        print(f"  {idx}. {pair['skill_a_name']} + {pair['skill_b_name']}: {pair['co_occurrence_count']} jobs ({pair['co_occurrence_percentage']}%)")
    print("==================================================")

if __name__ == "__main__":
    main()
