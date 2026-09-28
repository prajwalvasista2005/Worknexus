import json
from pathlib import Path
from ml.gap.gap_analyzer import SkillGapAnalyzer

def main():
    print("==================================================")
    print("PHASE 4: RUNNING SKILL GAP ANALYSIS")
    print("==================================================")

    analyzer = SkillGapAnalyzer()
    artifact, out_path = analyzer.run_and_save()

    meta = artifact["metadata"]
    print(f"Demand Input Artifact: {meta['demand_input']}")
    print(f"Course Input Dataset:  {meta['course_input']}")
    print(f"Output Artifact:       {out_path}")
    print(f"Total Courses:         {meta['total_courses']}")
    print(f"Observed Demand Skills:{meta['observed_demand_skills']}")
    print(f"Total Observed Demand: {meta['total_observed_demand']} (job_count sum)")
    print()

    print("COURSE-LEVEL COVERAGE SUMMARY:")
    print(f"{'ID':<6} {'Course Name':<35} {'Skills':<8} {'Cov/Dem':<10} {'SkillCov(%)':<13} {'DemCov(%)':<12} {'MissingDem'}")
    print("-" * 100)
    for c in artifact["courses"]:
        cid = c["course_id"]
        cname = c["course_name"][:34]
        n_skills = len(c["course_skills"])
        cov_dem = f"{c['covered_demand_skill_count']}/{c['observed_demand_skill_count']}"
        skill_cov_pct = f"{c['skill_coverage_ratio']*100:>5.2f}%"
        dem_cov_pct = f"{c['demand_coverage_ratio']*100:>5.2f}%"
        miss_dem = f"{c['missing_demand']}/{c['total_observed_demand']}"
        print(f"{cid:<6} {cname:<35} {n_skills:<8} {cov_dem:<10} {skill_cov_pct:<13} {dem_cov_pct:<12} {miss_dem}")
    print()

    print("TOP 10 DEMANDED SKILLS & COURSE COVERAGE (GLOBAL VIEW):")
    print(f"{'Rank':<5} {'Skill ID':<16} {'Skill Name':<25} {'Category':<18} {'Jobs':<6} {'Demand(%)':<10} {'Courses Cov'}")
    print("-" * 95)
    for idx, g in enumerate(artifact["global_skill_gap"][:10], 1):
        print(f"{idx:<5} {g['skill_id']:<16} {g['skill_name']:<25} {g['category']:<18} {g['job_count']:<6} {g['demand_percentage']:>5.2f}%    {g['courses_covering']}/{meta['total_courses']}")
    print()

    if artifact["unmapped_course_skills"]:
        print(f"UNMAPPED COURSE SKILLS ({len(artifact['unmapped_course_skills'])}):")
        for u in artifact["unmapped_course_skills"]:
            print(f"  - Course {u['course_id']} ({u['course_name']}): {u['unmapped_skill']}")
    else:
        print("Unmapped course skills: 0 (All course skills validated against canonical taxonomy)")
    print("==================================================")

if __name__ == "__main__":
    main()
