import json
import sys
from typing import List

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

from ml.ingestion.loaders import (
    load_linkedin_india_sample,
    load_naukri_sample,
    load_parquet_sample
)
from ml.ingestion.schema import JobRecord, DeduplicatedJobRecord
from ml.dedup.deduplicator import ConservativeDeduplicator

def run_real_data_ingestion_pipeline():
    print("="*70)
    print("WorkNexus — Real-World Collected Job-Posting Data Ingestion Pipeline")
    print("="*70)

    # 1. Load real collected data from different sources
    print("\n[STEP 1] Ingesting real-world collected job-posting data...")
    linkedin_jobs = load_linkedin_india_sample(limit=100)
    naukri_jobs = load_naukri_sample(limit=100)
    parquet_jobs = load_parquet_sample(limit=100)

    print(f"  [OK] LinkedIn India (archive3.zip):               {len(linkedin_jobs)} records loaded")
    print(f"  [OK] Naukri Data Science India (archive1.zip):    {len(naukri_jobs)} records loaded")
    print(f"  [OK] Parquet Corpus (train-00000-of-00001.parquet): {len(parquet_jobs)} records loaded")

    total_ingested = len(linkedin_jobs) + len(naukri_jobs) + len(parquet_jobs)
    print(f"\n  Total Raw Records Ingested into common JobRecord schema: {total_ingested}")

    # 2. Inspect Sample Common Normalized Records
    print("\n[STEP 2] Inspecting sample normalized JobRecords across sources:")
    print("\n-- Sample 1 (LinkedIn India) --")
    print(json.dumps(linkedin_jobs[0].to_dict(), indent=2)[:350] + "\n  ...")

    print("\n-- Sample 2 (Naukri India) --")
    print(json.dumps(naukri_jobs[0].to_dict(), indent=2)[:350] + "\n  ...")

    print("\n-- Sample 3 (Parquet Corpus) --")
    print(json.dumps(parquet_jobs[0].to_dict(), indent=2)[:350] + "\n  ...")

    # 3. Execute Conservative Cross-Source Deduplication
    print("\n[STEP 3] Executing conservative cross-source deduplication...")
    all_jobs: List[JobRecord] = linkedin_jobs + naukri_jobs + parquet_jobs

    # Inject a known cross-source duplicate to verify real merging in action
    mock_cross_source_dup = JobRecord(
        source="naukri_mirror",
        source_record_id="dup_mirror_001",
        title=linkedin_jobs[0].title,
        description=linkedin_jobs[0].description[:250],
        company=linkedin_jobs[0].company,
        location=linkedin_jobs[0].location
    )
    all_jobs_with_probe = all_jobs + [mock_cross_source_dup]

    deduplicator = ConservativeDeduplicator()
    deduped_records, decisions = deduplicator.deduplicate(all_jobs_with_probe)

    print(f"  [OK] Total Input Records (including cross-source probe): {len(all_jobs_with_probe)}")
    print(f"  [OK] Duplicate Vacancies Detected:                      {len(decisions)}")
    print(f"  [OK] Unique Postings Retained:                          {len(deduped_records)}")

    # Show merged provenance
    merged_cluster = next((r for r in deduped_records if len(r.source_records) > 1), None)
    if merged_cluster:
        print("\n  Sample Merged Record Provenance:")
        print(f"    Canonical ID:   {merged_cluster.canonical_id}")
        print(f"    Company:        {merged_cluster.company}")
        print(f"    Title:          {merged_cluster.title}")
        print(f"    Source Records: {merged_cluster.source_records}")

    print("\n" + "="*70)
    print("REAL DATA SUCCESSFULLY LOADED")
    print("="*70)

if __name__ == "__main__":
    run_real_data_ingestion_pipeline()
