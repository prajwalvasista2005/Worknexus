import sys
from typing import List

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

from ml.ingestion.loaders import (
    load_linkedin_india_sample,
    load_naukri_sample,
    load_parquet_sample
)
from ml.ingestion.schema import JobRecord
from ml.dedup.deduplicator import ConservativeDeduplicator

def analyze_source_stats(source_name: str, records: List[JobRecord]):
    total = len(records)
    with_desc = sum(1 for r in records if r.description and r.description.strip())
    with_title = sum(1 for r in records if r.title and r.title.strip())
    with_company = sum(1 for r in records if r.company and r.company.strip())
    with_location = sum(1 for r in records if r.location and r.location.strip())
    with_skills = sum(1 for r in records if r.explicit_skills and len(r.explicit_skills) > 0)

    print(f"\n--- Statistics for Source: '{source_name}' ---")
    print(f"  • Total records loaded:      {total}")
    print(f"  • With Title:                {with_title} (Missing: {total - with_title})")
    print(f"  • With Description:          {with_desc} (Missing: {total - with_desc})")
    print(f"  • With Company:              {with_company} (Missing: {total - with_company})")
    print(f"  • With Location:             {with_location} (Missing: {total - with_location})")
    print(f"  • With Explicit Skills:      {with_skills} (Missing: {total - with_skills})")


def run_unit_test_cases():
    print("\n============================================================")
    print("RUNNING EXPLICIT DEDUPLICATION SAFETY UNIT TESTS (CASES A-D)")
    print("============================================================")
    dedup = ConservativeDeduplicator()

    # Case A: ML Engineer | Company A | same description vs ML Engineer | Company A | same description => DUPLICATE
    rec_a1 = JobRecord(
        source="linkedin_india",
        source_record_id="case_a1",
        title="ML Engineer",
        description="Developing end-to-end computer vision and NLP models in PyTorch.",
        company="Company A",
        location="Bengaluru"
    )
    rec_a2 = JobRecord(
        source="naukri",
        source_record_id="case_a2",
        title="ML Engineer",
        description="Developing end-to-end computer vision and NLP models in PyTorch.",
        company="Company A",
        location="Bengaluru"
    )
    is_dup_a, reason_a = dedup.are_potential_duplicates(rec_a1, rec_a2)
    print(f"\n[CASE A] Exact Match (ML Engineer | Company A | same description):")
    print(f"  Decision is_duplicate: {is_dup_a} | Reason: {reason_a}")
    assert is_dup_a, "ASSERTION FAILED: Case A identical posting should be merged!"
    print("  [PASS] Correctly identified as duplicate.")

    # Case B: Senior ML Engineer | Company A vs ML Engineer | Company A (same skills, same location) => NOT DUPLICATE
    rec_b1 = JobRecord(
        source="linkedin_india",
        source_record_id="case_b1",
        title="Senior ML Engineer",
        description="PyTorch, Python, ML pipelines, Spark.",
        company="Company A",
        location="Bengaluru",
        explicit_skills=["PyTorch", "Python", "Spark"]
    )
    rec_b2 = JobRecord(
        source="naukri",
        source_record_id="case_b2",
        title="ML Engineer",
        description="PyTorch, Python, ML pipelines, Spark.",
        company="Company A",
        location="Bengaluru",
        explicit_skills=["PyTorch", "Python", "Spark"]
    )
    is_dup_b, reason_b = dedup.are_potential_duplicates(rec_b1, rec_b2)
    print(f"\n[CASE B] Different Seniority (Senior ML Engineer vs ML Engineer | same company & skills):")
    print(f"  Decision is_duplicate: {is_dup_b} | Reason: {reason_b}")
    assert not is_dup_b, "ASSERTION FAILED: Case B different seniorities must NOT be merged!"
    print("  [PASS] Correctly preserved as separate vacancies.")

    # Case C: ML Engineer | Company A vs ML Engineer | Company B => NOT DUPLICATE
    rec_c1 = JobRecord(
        source="linkedin_india",
        source_record_id="case_c1",
        title="ML Engineer",
        description="Core machine learning infrastructure.",
        company="Company A",
        location="Bengaluru"
    )
    rec_c2 = JobRecord(
        source="naukri",
        source_record_id="case_c2",
        title="ML Engineer",
        description="Core machine learning infrastructure.",
        company="Company B",
        location="Bengaluru"
    )
    is_dup_c, reason_c = dedup.are_potential_duplicates(rec_c1, rec_c2)
    print(f"\n[CASE C] Different Companies (ML Engineer | Company A vs Company B):")
    print(f"  Decision is_duplicate: {is_dup_c} | Reason: {reason_c}")
    assert not is_dup_c, "ASSERTION FAILED: Case C different companies must NEVER be merged!"
    print("  [PASS] Correctly preserved as separate vacancies.")

    # Case D: Same company + exact normalized title + near-identical description + same location => DUPLICATE
    rec_d1 = JobRecord(
        source="linkedin_india",
        source_record_id="case_d1",
        title="Data Scientist (NLP)",
        description="Build state-of-the-art NLP transformers and deployment pipelines with FastAPI on AWS.",
        company="Acme Analytics Pvt Ltd",
        location="Bengaluru"
    )
    rec_d2 = JobRecord(
        source="naukri",
        source_record_id="case_d2",
        title="Data Scientist - NLP",
        description="Build state-of-the-art NLP transformers and deployment pipelines with FastAPI on AWS cloud.",
        company="Acme Analytics",
        location="Bengaluru, Karnataka"
    )
    is_dup_d, reason_d = dedup.are_potential_duplicates(rec_d1, rec_d2)
    print(f"\n[CASE D] Multi-signal Agreement (Acme Analytics | Data Scientist - NLP | near-identical desc):")
    print(f"  Decision is_duplicate: {is_dup_d} | Reason: {reason_d}")
    assert is_dup_d, "ASSERTION FAILED: Case D matching cross-posting should be merged!"
    print("  [PASS] Correctly identified as duplicate.")


def main():
    print("="*60)
    print("WORKNEXUS REAL DATA INGESTION & DEDUPLICATION TEST")
    print("="*60)

    # 1. Load 100 records from each source
    print("\nLoading real-world collected datasets (100 records each)...")
    linkedin_records = load_linkedin_india_sample(limit=100)
    naukri_records = load_naukri_sample(limit=100)
    parquet_records = load_parquet_sample(limit=100)

    # Analyze field availability
    analyze_source_stats("linkedin_india (archive3.zip)", linkedin_records)
    analyze_source_stats("naukri (archive1.zip)", naukri_records)
    analyze_source_stats("parquet (train-00000-of-00001.parquet)", parquet_records)

    # Combine all raw records
    all_raw_records: List[JobRecord] = linkedin_records + naukri_records + parquet_records
    total_raw = len(all_raw_records)

    # 2. Run conservative deduplication
    print("\n" + "="*60)
    print("RUNNING CONSERVATIVE DEDUPLICATION ON COMBINED CORPUS")
    print("="*60)
    deduplicator = ConservativeDeduplicator()
    unique_records, decision_log = deduplicator.deduplicate(all_raw_records)

    merged_count = len(decision_log)
    retained_count = len(unique_records)

    print(f"\n• Total Raw Records Ingested:        {total_raw}")
    print(f"• Duplicate Matches Identified:      {merged_count}")
    print(f"• Records Merged:                   {merged_count}")
    print(f"• Final Unique Records Retained:    {retained_count}")

    # Counts by primary source
    source_counts = {}
    for r in unique_records:
        src = r.source_records[0]["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
    print(f"• Retained by Primary Source:        {source_counts}")

    # Inspect duplicate decisions
    print("\n" + "-"*60)
    print(f"DUPLICATE DECISION LOG (Total: {merged_count})")
    print("-"*60)
    if merged_count == 0:
        print("No duplicates detected among the disjoint 100-sample sets across sources.")
    else:
        for idx, dec in enumerate(decision_log[:10], 1):
            print(f"\nDecision #{idx}:")
            print(f"  Primary:   [{dec['primary_source']} | {dec['primary_id']}] {dec['primary_company']} - {dec['primary_title']}")
            print(f"  Duplicate: [{dec['duplicate_source']} | {dec['duplicate_id']}] {dec['duplicate_company']} - {dec['duplicate_title']}")
            print(f"  Reason:    {dec['reason']}")

    # 3. Run unit test cases
    run_unit_test_cases()

    print("\n============================================================")
    print("[SUCCESS] All ingestion and deduplication tests completed successfully!")
    print("============================================================\n")

if __name__ == "__main__":
    main()
