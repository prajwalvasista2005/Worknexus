import json
from pathlib import Path
from ml.employer.feedback_analyzer import EmployerFeedbackAnalyzer

def main():
    print("==================================================")
    print("PHASE 5A: RUNNING EMPLOYER FEEDBACK INTELLIGENCE")
    print("==================================================")

    analyzer = EmployerFeedbackAnalyzer()
    artifact, out_path = analyzer.run_and_save()

    meta = artifact["metadata"]
    print(f"Feedback Input Dataset: {meta['input_file']}")
    print(f"Output Artifact:        {out_path}")
    print(f"Total Feedback Records: {meta['total_feedback_records']}")
    print(f"Processed Records:      {meta['processed_feedback_records']}")
    print(f"Failed Records:         {meta['failed_feedback_records']}")
    print(f"Records with Skills:    {meta['feedback_records_with_skills']}")
    print(f"Zero-Skill Records:     {meta['zero_skill_feedback_records']}")
    print(f"Unique Employers:       {meta['unique_employers']}")
    print(f"Unique Courses:         {meta['unique_courses']}")
    print(f"Unique Skills Detected: {meta['unique_skills_detected']}")
    print()

    print("AGGREGATED EMPLOYER SKILL SIGNALS:")
    print(f"{'Skill ID':<18} {'Skill Name':<28} {'Feedbacks':<10} {'Employers':<10} {'Signal Sum':<12} {'Avg Signal':<12} {'Max Signal'}")
    print("-" * 105)
    for s in artifact["skill_signals"]:
        print(f"{s['skill_id']:<18} {s['skill_name']:<28} {s['feedback_count']:<10} {s['unique_employer_count']:<10} {s['weighted_signal_sum']:<12.4f} {s['average_weighted_signal']:<12.4f} {s['max_weighted_signal']:<12.4f}")
    print()

    print("COURSE-LEVEL EMPLOYER SIGNALS:")
    for c in artifact["course_signals"]:
        print(f"Course {c['course_id']} (Feedbacks: {c['feedback_count']}, Employers: {c['employer_count']}):")
        for sk in c["skills"]:
            print(f"  - {sk['skill_id']:<16} ({sk['skill_name']:<25}): {sk['feedback_count']} feedbacks, {sk['unique_employer_count']} employers, Avg Signal: {sk['average_weighted_signal']:.4f}")
    print("==================================================")

if __name__ == "__main__":
    main()
