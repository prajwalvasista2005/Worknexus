import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

from ml.ingestion.loaders import (
    load_linkedin_india_sample,
    load_naukri_sample,
    load_parquet_sample,
    DEFAULT_DATA_DIR
)
from ml.dedup.deduplicator import ConservativeDeduplicator
from ml.extract import extract_skills
from ml.ingestion.schema import DeduplicatedJobRecord

DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parent / "extracted_job_skills.json"

class BatchJobSkillExtractor:
    """
    Deterministic batch processor executing skill extraction over deduplicated JobRecords.
    Produces a structured ML artifact with complete provenance and validated skill contracts.
    """

    def __init__(self, taxonomy_path: Optional[Path] = None):
        tax_path = taxonomy_path or DEFAULT_TAXONOMY_PATH
        if not tax_path.exists():
            raise FileNotFoundError(f"Canonical taxonomy missing at {tax_path}")
        with open(tax_path, "r", encoding="utf-8") as f:
            self.taxonomy: List[Dict[str, Any]] = json.load(f)
        self.valid_skill_ids = {s["id"] for s in self.taxonomy}
        self.taxonomy_version = str(self.taxonomy[0].get("version", "1")) if self.taxonomy else "1"

    def process_jobs(
        self,
        deduped_records: List[DeduplicatedJobRecord]
    ) -> Dict[str, Any]:
        """
        Processes a list of deduplicated job records deterministically.
        Extracts skills using title + description (without explicit_skills),
        validates output constraints, and retains job provenance.
        """
        processed_jobs: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        jobs_with_skills_count = 0
        total_skill_mentions = 0
        unique_skills_set = set()

        for rec in deduped_records:
            job_id = rec.canonical_id
            primary_source = rec.source_records[0]["source"] if rec.source_records else "unknown"
            primary_src_id = rec.source_records[0]["source_record_id"] if rec.source_records else ""
            title = rec.title or ""
            desc = rec.description or ""

            extraction_text = f"{title} {desc}".strip()

            try:
                raw_skills = extract_skills(extraction_text)

                # Strict validation of extracted skill list
                validated_skills: List[Dict[str, Any]] = []
                seen_skills_in_job = set()

                for item in raw_skills:
                    if set(item.keys()) != {"skill_id", "confidence_score"}:
                        raise ValueError(f"Invalid schema keys {set(item.keys())} in job {job_id}")

                    s_id = item["skill_id"]
                    conf = item["confidence_score"]

                    if s_id not in self.valid_skill_ids:
                        raise ValueError(f"Unknown canonical skill_id '{s_id}' in job {job_id}")

                    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
                        raise ValueError(f"Invalid confidence score {conf} for skill {s_id} in job {job_id}")

                    if s_id in seen_skills_in_job:
                        raise ValueError(f"Duplicate skill_id '{s_id}' extracted for single job {job_id}")

                    seen_skills_in_job.add(s_id)
                    unique_skills_set.add(s_id)
                    validated_skills.append({
                        "skill_id": s_id,
                        "confidence_score": conf
                    })

                if validated_skills:
                    jobs_with_skills_count += 1
                    total_skill_mentions += len(validated_skills)

                processed_jobs.append({
                    "job_id": job_id,
                    "source": primary_source,
                    "source_record_id": primary_src_id,
                    "title": title,
                    "skills": validated_skills
                })

            except Exception as e:
                errors.append({
                    "job_id": job_id,
                    "source": primary_source,
                    "error": str(e)
                })

        total_input = len(deduped_records)
        total_processed = len(processed_jobs)
        total_failed = len(errors)
        total_zero_skills = total_processed - jobs_with_skills_count

        artifact = {
            "metadata": {
                "phase": "2",
                "pipeline": "batch_job_skill_extraction",
                "extractor": "ml.extract.extract_skills",
                "taxonomy_version": self.taxonomy_version,
                "total_input_jobs": total_input,
                "total_processed_jobs": total_processed,
                "total_failed_jobs": total_failed,
                "total_jobs_with_skills": jobs_with_skills_count,
                "total_zero_skill_jobs": total_zero_skills,
                "total_skill_mentions": total_skill_mentions,
                "unique_skills_detected": len(unique_skills_set)
            },
            "jobs": processed_jobs,
            "errors": errors
        }
        return artifact

    def run_pipeline(
        self,
        output_path: Optional[Path] = None,
        data_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end Phase 2: Ingestion -> Dedup -> Extraction -> Artifact serialization.
        """
        out_file = output_path or DEFAULT_ARTIFACT_PATH

        # Step 1: Load Phase 0.5 real data samples
        linkedin_jobs = load_linkedin_india_sample(limit=100, data_dir=data_dir)
        naukri_jobs = load_naukri_sample(limit=100, data_dir=data_dir)
        parquet_jobs = load_parquet_sample(limit=100, data_dir=data_dir)
        all_raw = linkedin_jobs + naukri_jobs + parquet_jobs

        # Step 2: Run Conservative Deduplication
        deduplicator = ConservativeDeduplicator()
        deduped_records, _ = deduplicator.deduplicate(all_raw)

        # Step 3: Run Batch Extraction
        t0 = time.perf_counter()
        artifact = self.process_jobs(deduped_records)
        duration = time.perf_counter() - t0

        # Step 4: Write artifact deterministically
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)

        return artifact, duration

def run_batch_extraction():
    print("="*75)
    print("WORKNEXUS PHASE 2 — BATCH JOB SKILL EXTRACTION")
    print("="*75)

    extractor = BatchJobSkillExtractor()
    artifact, duration = extractor.run_pipeline()
    meta = artifact["metadata"]

    print(f"\nPipeline Execution Complete in {duration:.3f}s")
    print(f"  • Total Input Jobs:          {meta['total_input_jobs']}")
    print(f"  • Successfully Processed:    {meta['total_processed_jobs']}")
    print(f"  • Failed Jobs:               {meta['total_failed_jobs']}")
    print(f"  • Jobs With Skills:          {meta['total_jobs_with_skills']} ({meta['total_jobs_with_skills']/meta['total_processed_jobs']:.1%})")
    print(f"  • Zero-Skill Jobs:           {meta['total_zero_skill_jobs']} ({meta['total_zero_skill_jobs']/meta['total_processed_jobs']:.1%})")
    print(f"  • Total Skill Mentions:      {meta['total_skill_mentions']}")
    print(f"  • Unique Skills Detected:    {meta['unique_skills_detected']}")
    print(f"  • Artifact Written:          {DEFAULT_ARTIFACT_PATH}")

    # Baseline comparison against Phase 1D
    print("\n" + "-"*75)
    print("PHASE 1D BASELINE REGRESSION CHECK")
    print("-"*75)
    baseline = {
        "total_input_jobs": 295,
        "total_jobs_with_skills": 211,
        "total_zero_skill_jobs": 84,
        "total_skill_mentions": 536,
        "unique_skills_detected": 32
    }
    all_matched = True
    for key, base_val in baseline.items():
        actual_val = meta[key]
        status = "PASS" if actual_val == base_val else "REVIEW"
        if actual_val != base_val:
            all_matched = False
        print(f"  • {key:25}: Baseline={base_val:4d} | Actual={actual_val:4d} -> [{status}]")

    print(f"\nRegression Status: {'PASS — Results match baseline exactly' if all_matched else 'REVIEW — Results differ'}")
    print("="*75)

if __name__ == "__main__":
    run_batch_extraction()
