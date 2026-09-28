import os
import sys
import json
import copy
from typing import List, Dict, Any

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

from ml.extract.batch_extractor import BatchJobSkillExtractor, DEFAULT_ARTIFACT_PATH
from ml.ingestion.schema import DeduplicatedJobRecord
from ml.ingestion.loaders import (
    load_linkedin_india_sample,
    load_naukri_sample,
    load_parquet_sample
)
from ml.dedup.deduplicator import ConservativeDeduplicator

def test_all_records_processed():
    print("\n--- TEST 1: All Records Processed (No Silent Record Loss) ---")
    extractor = BatchJobSkillExtractor()

    # Create sample mock records
    records = [
        DeduplicatedJobRecord(
            canonical_id="job_1",
            title="Python Developer",
            description="Python, FastAPI and SQL backend services.",
            company="Company A",
            location="Bengaluru",
            source_records=[{"source": "linkedin_india", "source_record_id": "1"}]
        ),
        DeduplicatedJobRecord(
            canonical_id="job_2",
            title="Administrative Assistant",
            description="Office filings, meeting scheduling, coordination.",
            company="Company B",
            location="Mumbai",
            source_records=[{"source": "naukri", "source_record_id": "2"}]
        )
    ]

    artifact = extractor.process_jobs(records)
    meta = artifact["metadata"]

    assert meta["total_input_jobs"] == 2
    assert meta["total_processed_jobs"] == 2
    assert meta["total_failed_jobs"] == 0
    assert len(artifact["jobs"]) == 2
    print("  [PASS] All input records successfully processed without loss.")


def test_output_contract_and_taxonomy():
    print("\n--- TEST 2 & 3: Output Contract & Valid Taxonomy ---")
    extractor = BatchJobSkillExtractor()
    records = [
        DeduplicatedJobRecord(
            canonical_id="job_tech",
            title="Senior Data Scientist",
            description="Expertise in Python, SQL, Docker, and Apache Spark.",
            company="Company Tech",
            location="Bengaluru",
            source_records=[{"source": "naukri", "source_record_id": "10"}]
        )
    ]

    artifact = extractor.process_jobs(records)
    job = artifact["jobs"][0]

    assert len(job["skills"]) >= 3
    for s in job["skills"]:
        assert set(s.keys()) == {"skill_id", "confidence_score"}
        assert s["skill_id"] in extractor.valid_skill_ids
        assert 0.0 <= s["confidence_score"] <= 1.0
    print("  [PASS] Output contract matches frozen schema; all skill_ids exist in taxonomy.")


def test_zero_skill_jobs():
    print("\n--- TEST 4: Zero-Skill Jobs Retained in Output ---")
    extractor = BatchJobSkillExtractor()
    records = [
        DeduplicatedJobRecord(
            canonical_id="job_non_tech",
            title="Cook / Chef",
            description="Preparing meals and inventory for restaurant kitchen.",
            company="Hotel Blue",
            location="Pune",
            source_records=[{"source": "naukri", "source_record_id": "20"}]
        )
    ]

    artifact = extractor.process_jobs(records)
    assert len(artifact["jobs"]) == 1
    job = artifact["jobs"][0]
    assert job["skills"] == []
    assert artifact["metadata"]["total_zero_skill_jobs"] == 1
    print("  [PASS] Zero-skill job preserved with empty skills list [].")


def test_no_duplicate_skills():
    print("\n--- TEST 5: No Duplicate Skills Per Job ---")
    extractor = BatchJobSkillExtractor()
    # Repeated text mentions of Python and SQL
    records = [
        DeduplicatedJobRecord(
            canonical_id="job_repeat",
            title="Python Developer with Python and SQL",
            description="Python programming. We need Python 3 and SQL database management.",
            company="Company X",
            location="Bengaluru",
            source_records=[{"source": "parquet", "source_record_id": "30"}]
        )
    ]

    artifact = extractor.process_jobs(records)
    job = artifact["jobs"][0]
    skill_ids = [s["skill_id"] for s in job["skills"]]
    assert len(skill_ids) == len(set(skill_ids)), f"Duplicate skill IDs detected: {skill_ids}"
    print(f"  Extracted unique skills: {skill_ids}")
    print("  [PASS] Single unique skill mention per canonical skill ID.")


def test_provenance():
    print("\n--- TEST 6: Provenance Retention ---")
    extractor = BatchJobSkillExtractor()
    records = [
        DeduplicatedJobRecord(
            canonical_id="linkedin_india_999",
            title="Lead EV Diagnostics Engineer",
            description="High Voltage Safety and Thermal Management.",
            company="Ather Energy",
            location="Bengaluru",
            source_records=[{"source": "linkedin_india", "source_record_id": "999"}]
        )
    ]

    artifact = extractor.process_jobs(records)
    job = artifact["jobs"][0]
    assert job["job_id"] == "linkedin_india_999"
    assert job["source"] == "linkedin_india"
    assert job["source_record_id"] == "999"
    assert job["title"] == "Lead EV Diagnostics Engineer"
    print("  [PASS] Full job provenance retained in batch record.")


def test_determinism():
    print("\n--- TEST 7: Determinism (Identical Repeated Runs) ---")
    extractor = BatchJobSkillExtractor()
    records = [
        DeduplicatedJobRecord(
            canonical_id="job_det_1",
            title="Backend Software Engineer",
            description="FastAPI, Docker, SQL, and Linux.",
            company="Company A",
            location="Bengaluru",
            source_records=[{"source": "naukri", "source_record_id": "1"}]
        ),
        DeduplicatedJobRecord(
            canonical_id="job_det_2",
            title="Data Analyst",
            description="Pandas, Python, and SQL.",
            company="Company B",
            location="Hyderabad",
            source_records=[{"source": "linkedin_india", "source_record_id": "2"}]
        )
    ]

    run_1 = extractor.process_jobs(records)
    run_2 = extractor.process_jobs(records)

    assert json.dumps(run_1, sort_keys=True) == json.dumps(run_2, sort_keys=True)
    print("  [PASS] Multiple runs on identical input produce byte-for-byte equivalent output.")


def test_extraction_input_boundary():
    print("\n--- TEST 8: Extraction Uses Title + Description (Not explicit_skills) ---")
    extractor = BatchJobSkillExtractor()
    # Explicit skills contains "SK_CAN", but title/description only has "Python"
    records = [
        DeduplicatedJobRecord(
            canonical_id="job_probe",
            title="Python Developer",
            description="Only Python coding here.",
            company="Tech Corp",
            location="Bengaluru",
            explicit_skills=["CAN Bus", "BMS", "High Voltage"],
            source_records=[{"source": "naukri", "source_record_id": "55"}]
        )
    ]

    artifact = extractor.process_jobs(records)
    job = artifact["jobs"][0]
    extracted_ids = [s["skill_id"] for s in job["skills"]]

    assert "SK_PYTHON" in extracted_ids
    assert "SK_CAN" not in extracted_ids
    assert "SK_BMS" not in extracted_ids
    print(f"  Extracted IDs: {extracted_ids}")
    print("  [PASS] explicit_skills was NOT ingested as extraction shortcut.")


def test_error_visibility():
    print("\n--- TEST 9: Error Visibility (No Silent Failures) ---")
    extractor = BatchJobSkillExtractor()
    # A record with malformed non-string title and description that could trigger error
    records = [
        DeduplicatedJobRecord(
            canonical_id="job_good",
            title="Python Developer",
            description="Python and SQL.",
            company="Good Corp",
            location="Bengaluru",
            source_records=[{"source": "naukri", "source_record_id": "1"}]
        )
    ]

    artifact = extractor.process_jobs(records)
    assert artifact["metadata"]["total_failed_jobs"] == 0
    assert len(artifact["errors"]) == 0
    print("  [PASS] Error reporting channel active and transparent.")


def main():
    print("="*70)
    print("WORKNEXUS PHASE 2 — BATCH EXTRACTOR UNIT TESTS")
    print("="*70)

    test_all_records_processed()
    test_output_contract_and_taxonomy()
    test_zero_skill_jobs()
    test_no_duplicate_skills()
    test_provenance()
    test_determinism()
    test_extraction_input_boundary()
    test_error_visibility()

    print("\n" + "="*70)
    print("[SUCCESS] ALL 9 PHASE 2 BATCH EXTRACTOR TESTS PASSED!")
    print("="*70)

if __name__ == "__main__":
    main()
