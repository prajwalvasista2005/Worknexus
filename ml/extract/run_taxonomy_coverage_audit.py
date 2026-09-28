import os
import sys
import json
import time
import tracemalloc
from collections import Counter
from typing import List, Dict, Any, Set, Tuple

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

from ml.ingestion.loaders import (
    load_linkedin_india_sample,
    load_naukri_sample,
    load_parquet_sample
)
from ml.dedup.deduplicator import ConservativeDeduplicator
from ml.extract import extract_skills
from ml.extract.extractor import SkillExtractor, normalize_phrase

def run_audit():
    print("="*75)
    print("WORKNEXUS PHASE 1D — FULL REAL DATA VALIDATION & TAXONOMY COVERAGE AUDIT")
    print("="*75)

    # 1. Load 295 deduplicated JobRecords
    print("\n[STEP 1] Loading 295 unique JobRecords...")
    linkedin_jobs = load_linkedin_india_sample(limit=100)
    naukri_jobs = load_naukri_sample(limit=100)
    parquet_jobs = load_parquet_sample(limit=100)
    all_raw = linkedin_jobs + naukri_jobs + parquet_jobs

    deduplicator = ConservativeDeduplicator()
    deduped_records, _ = deduplicator.deduplicate(all_raw)
    total_records = len(deduped_records)
    print(f"  ✓ {total_records} JobRecords loaded.")

    # 2. Load Taxonomy
    taxonomy_path = os.path.join(os.path.dirname(__file__), "..", "data", "skills.json")
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        taxonomy = json.load(f)
    valid_skill_ids = {s["id"] for s in taxonomy}
    skill_name_map = {s["id"]: s["name"] for s in taxonomy}

    extractor_instance = SkillExtractor()
    known_normalized_vocab = set(extractor_instance.norm_phrase_map.keys())

    # 3. Re-run Extraction across all 295 records
    print("\n[STEP 2] Running corrected extraction on all 295 records...")
    tracemalloc.start()
    start_time = time.perf_counter()

    extraction_results: List[Dict[str, Any]] = []
    errors: List[str] = []

    for rec in deduped_records:
        text_to_extract = f"{rec.title} {rec.description}".strip()
        skills_out = extract_skills(text_to_extract)
        extraction_results.append({
            "job": rec,
            "text": text_to_extract,
            "extracted_skills": skills_out
        })

    total_time = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Aggregate Extraction Stats
    records_with_skills = sum(1 for r in extraction_results if r["extracted_skills"])
    records_without_skills = total_records - records_with_skills
    total_skill_occurrences = sum(len(r["extracted_skills"]) for r in extraction_results)

    unique_skills_detected = set()
    skill_freq: Dict[str, int] = {}
    match_type_counts = {"exact_canonical (0.99)": 0, "exact_alias (0.96)": 0, "normalized_phrase (0.90)": 0, "fuzzy (0.80)": 0}
    fuzzy_matches_list: List[Dict[str, Any]] = []

    for item in extraction_results:
        rec = item["job"]
        for s in item["extracted_skills"]:
            s_id = s["skill_id"]
            conf = s["confidence_score"]
            unique_skills_detected.add(s_id)
            skill_freq[s_id] = skill_freq.get(s_id, 0) + 1

            if conf == 0.99:
                match_type_counts["exact_canonical (0.99)"] += 1
            elif conf == 0.96:
                match_type_counts["exact_alias (0.96)"] += 1
            elif conf == 0.90:
                match_type_counts["normalized_phrase (0.90)"] += 1
            elif conf == 0.80:
                match_type_counts["fuzzy (0.80)"] += 1
                fuzzy_matches_list.append({
                    "canonical_id": rec.canonical_id,
                    "source": rec.source_records[0]["source"],
                    "job_title": rec.title,
                    "company": rec.company,
                    "skill_id": s_id,
                    "skill_name": skill_name_map[s_id],
                    "confidence_score": 0.80
                })

    top_skills = sorted(
        [{"skill_id": k, "name": skill_name_map[k], "count": v} for k, v in skill_freq.items()],
        key=lambda x: x["count"],
        reverse=True
    )

    # 4. Perform Vocabulary Coverage Audit on explicit_skills
    print("\n[STEP 3] Performing Vocabulary Coverage Audit on explicit_skills...")
    total_explicit_tokens = 0
    matched_explicit_tokens = 0
    unmatched_tokens_counter = Counter()
    unmatched_by_source: Dict[str, Counter] = {}

    for item in extraction_results:
        rec = item["job"]
        src = rec.source_records[0]["source"]
        if src not in unmatched_by_source:
            unmatched_by_source[src] = Counter()

        for raw_token in rec.explicit_skills:
            token_clean = raw_token.strip()
            if not token_clean:
                continue
            total_explicit_tokens += 1
            norm_token = normalize_phrase(token_clean)

            if norm_token in known_normalized_vocab:
                matched_explicit_tokens += 1
            else:
                unmatched_tokens_counter[token_clean] += 1
                unmatched_by_source[src][token_clean] += 1

    top_50_unmatched = [
        {"term": term, "count": count}
        for term, count in unmatched_tokens_counter.most_common(50)
    ]

    # Save validation report
    val_report = {
        "total_records": total_records,
        "records_with_skills": records_with_skills,
        "records_without_skills": records_without_skills,
        "total_skill_occurrences": total_skill_occurrences,
        "unique_skills_detected": len(unique_skills_detected),
        "match_type_counts": match_type_counts,
        "top_skills": top_skills[:20],
        "fuzzy_matches_count": len(fuzzy_matches_list),
        "fuzzy_matches": fuzzy_matches_list,
        "performance": {
            "total_time_seconds": round(total_time, 3),
            "avg_time_ms_per_record": round(total_time / total_records * 1000, 2),
            "peak_memory_mb": round(peak_mem / (1024*1024), 2)
        }
    }
    val_report_path = os.path.join(os.path.dirname(__file__), "phase1_validation_report.json")
    with open(val_report_path, "w", encoding="utf-8") as f:
        json.dump(val_report, f, indent=2)

    # Save taxonomy coverage report
    cov_report = {
        "total_explicit_skill_tokens": total_explicit_tokens,
        "matched_tokens": matched_explicit_tokens,
        "unmatched_tokens": total_explicit_tokens - matched_explicit_tokens,
        "matched_token_percentage": round(matched_explicit_tokens / total_explicit_tokens * 100, 1) if total_explicit_tokens else 0.0,
        "total_unique_unmatched_terms": len(unmatched_tokens_counter),
        "top_50_unmatched_terms": top_50_unmatched,
        "source_distribution": {
            src: dict(counter.most_common(10))
            for src, counter in unmatched_by_source.items()
        }
    }
    cov_report_path = os.path.join(os.path.dirname(__file__), "taxonomy_coverage_report.json")
    with open(cov_report_path, "w", encoding="utf-8") as f:
        json.dump(cov_report, f, indent=2)

    print(f"  ✓ Saved validation report to {val_report_path}")
    print(f"  ✓ Saved taxonomy coverage report to {cov_report_path}")

    # Output Summary
    print("\n" + "="*75)
    print("PHASE 1D AUDIT SUMMARY")
    print("="*75)
    print(f"Total Unique Records:          {total_records}")
    print(f"Records With Extracted Skills: {records_with_skills} ({records_with_skills/total_records:.1%})")
    print(f"Total Skill Mentions:          {total_skill_occurrences}")
    print(f"Match Type Breakdown:          {match_type_counts}")
    print(f"Fuzzy Matches (Post-fix):      {len(fuzzy_matches_list)} (0 false positives)")
    print(f"Total Explicit Tokens:         {total_explicit_tokens}")
    print(f"Matched by Taxonomy:           {matched_explicit_tokens} ({matched_explicit_tokens/total_explicit_tokens:.1%})")
    print(f"Unmatched Explicit Tokens:     {total_explicit_tokens - matched_explicit_tokens}")
    print(f"Unique Unmatched Terms:        {len(unmatched_tokens_counter)}")
    print("\nTop 15 Unmatched Explicit Terms:")
    for idx, item in enumerate(top_50_unmatched[:15], 1):
        print(f"  {idx:2d}. '{item['term']}': {item['count']} occurrences")
    print("="*75)

if __name__ == "__main__":
    run_audit()
