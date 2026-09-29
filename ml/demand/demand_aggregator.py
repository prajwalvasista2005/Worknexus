import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict, Counter

DEFAULT_INPUT_ARTIFACT_PATH = Path(__file__).resolve().parent.parent / "extract" / "extracted_job_skills.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "demand_analysis.json"

class DemandAggregator:
    """
    Computes explainable, job-based demand statistics, source-normalized metrics,
    category aggregations, and pairwise skill co-occurrences on the Phase 2 extraction artifact.
    """

    def __init__(
        self,
        input_artifact_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.input_path = input_artifact_path or DEFAULT_INPUT_ARTIFACT_PATH
        self.tax_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.input_path.exists():
            raise FileNotFoundError(f"Input Phase 2 artifact missing at {self.input_path}")
        if not self.tax_path.exists():
            raise FileNotFoundError(f"Taxonomy file missing at {self.tax_path}")

        with open(self.input_path, "r", encoding="utf-8") as f:
            self.input_data = json.load(f)

        with open(self.tax_path, "r", encoding="utf-8") as f:
            self.taxonomy_data = json.load(f)

        self._validate_and_index_taxonomy()

    def _validate_and_index_taxonomy(self):
        self.skills_by_id: Dict[str, Dict[str, Any]] = {}
        for s in self.taxonomy_data:
            s_id = s["id"]
            self.skills_by_id[s_id] = {
                "id": s_id,
                "name": s["name"],
                "category": s["category"]
            }
        self.valid_categories = sorted(list({s["category"] for s in self.taxonomy_data}))

    def aggregate(self) -> Dict[str, Any]:
        meta_in = self.input_data.get("metadata", {})
        jobs = self.input_data.get("jobs", [])

        total_jobs = len(jobs)
        if total_jobs == 0:
            raise ValueError("Input artifact contains 0 jobs.")

        # Data integrity verification against Phase 2 metadata
        if "total_input_jobs" in meta_in and meta_in["total_input_jobs"] != total_jobs:
            raise ValueError(f"Metadata total_input_jobs ({meta_in['total_input_jobs']}) != actual jobs count ({total_jobs})")

        # Trackers
        jobs_with_skills_count = 0
        total_skill_mentions_count = 0
        source_job_counts: Dict[str, int] = defaultdict(int)

        # Skill-level aggregators: skill_id -> list of (source, confidence)
        skill_occurrences: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        # Category-level trackers: category -> set of job_ids
        category_job_sets: Dict[str, Set[str]] = defaultdict(set)
        category_skill_assignments: Dict[str, int] = defaultdict(int)
        category_detected_skills: Dict[str, Set[str]] = defaultdict(set)

        # Pairwise co-occurrence tracker: (skill_a, skill_b) -> int (where skill_a < skill_b)
        co_occurrence_counts: Dict[Tuple[str, str], int] = defaultdict(int)

        for job in jobs:
            job_id = job.get("job_id", "")
            source = job.get("source", "unknown")
            source_job_counts[source] += 1

            skills = job.get("skills", [])
            if skills:
                jobs_with_skills_count += 1
                total_skill_mentions_count += len(skills)

            # Ensure uniqueness per job (Phase 2 guarantees, but enforced here)
            job_skill_ids = set()
            for s in skills:
                s_id = s["skill_id"]
                conf = float(s.get("confidence_score", 0.0))

                if s_id not in self.skills_by_id:
                    raise ValueError(f"Unknown skill_id '{s_id}' found in job {job_id}")

                if s_id not in job_skill_ids:
                    job_skill_ids.add(s_id)
                    skill_occurrences[s_id].append((source, conf))

                    cat = self.skills_by_id[s_id]["category"]
                    category_job_sets[cat].add(job_id)
                    category_skill_assignments[cat] += 1
                    category_detected_skills[cat].add(s_id)

            # Co-occurrence across distinct skill pairs in this job
            sorted_job_skills = sorted(list(job_skill_ids))
            num_skills = len(sorted_job_skills)
            for i in range(num_skills):
                for j in range(i + 1, num_skills):
                    pair = (sorted_job_skills[i], sorted_job_skills[j])
                    co_occurrence_counts[pair] += 1

        zero_skill_jobs_count = total_jobs - jobs_with_skills_count
        detected_unique_skills = len(skill_occurrences)

        # 1. Global Skill Demand Table
        skills_summary: List[Dict[str, Any]] = []
        for s_id, occurrences in skill_occurrences.items():
            job_count = len(occurrences)
            demand_share = job_count / total_jobs
            demand_pct = demand_share * 100.0

            confidences = [c for _, c in occurrences]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            sources_present = sorted(list({src for src, _ in occurrences}))

            skills_summary.append({
                "skill_id": s_id,
                "skill_name": self.skills_by_id[s_id]["name"],
                "category": self.skills_by_id[s_id]["category"],
                "job_count": job_count,
                "demand_share": round(demand_share, 4),
                "demand_percentage": round(demand_pct, 2),
                "average_confidence": round(avg_conf, 2),
                "source_coverage_count": len(sources_present),
                "sources_present": sources_present
            })

        # Deterministic sort: job_count DESC, skill_id ASC
        skills_summary.sort(key=lambda x: (-x["job_count"], x["skill_id"]))

        # 2. Source-Level Demand
        source_demand: Dict[str, Any] = {}
        for source in sorted(source_job_counts.keys()):
            src_total = source_job_counts[source]
            src_skills_list: List[Dict[str, Any]] = []

            for s_id, occurrences in skill_occurrences.items():
                src_occs = [c for src, c in occurrences if src == source]
                if src_occs:
                    src_count = len(src_occs)
                    src_share = src_count / src_total if src_total > 0 else 0.0
                    src_pct = src_share * 100.0
                    src_avg_conf = sum(src_occs) / src_count

                    src_skills_list.append({
                        "skill_id": s_id,
                        "skill_name": self.skills_by_id[s_id]["name"],
                        "category": self.skills_by_id[s_id]["category"],
                        "source_job_count": src_count,
                        "source_demand_share": round(src_share, 4),
                        "source_demand_percentage": round(src_pct, 2),
                        "source_average_confidence": round(src_avg_conf, 2)
                    })

            # Sort source skills by source_job_count DESC, skill_id ASC
            src_skills_list.sort(key=lambda x: (-x["source_job_count"], x["skill_id"]))

            source_demand[source] = {
                "source_total_jobs": src_total,
                "skills_detected_count": len(src_skills_list),
                "skills": src_skills_list
            }

        # 3. Category Aggregation
        categories_summary: List[Dict[str, Any]] = []
        for cat in self.valid_categories:
            detected_skills_count = len(category_detected_skills.get(cat, set()))
            total_assignments = category_skill_assignments.get(cat, 0)
            unique_jobs_with_cat = len(category_job_sets.get(cat, set()))
            cat_job_pct = (unique_jobs_with_cat / total_jobs * 100.0) if total_jobs > 0 else 0.0
            avg_skill_jobs = (total_assignments / detected_skills_count) if detected_skills_count > 0 else 0.0

            categories_summary.append({
                "category": cat,
                "number_of_skills_detected": detected_skills_count,
                "total_skill_job_assignments": total_assignments,
                "unique_jobs_with_category_skill": unique_jobs_with_cat,
                "percentage_of_jobs_with_any_category_skill": round(cat_job_pct, 2),
                "average_skill_job_count": round(avg_skill_jobs, 2)
            })

        # Deterministic sort: category name ASC
        categories_summary.sort(key=lambda x: x["category"])

        # 4. Pairwise Skill Co-occurrence
        co_occurrence_list: List[Dict[str, Any]] = []
        for (s_a, s_b), pair_count in co_occurrence_counts.items():
            co_occurrence_list.append({
                "skill_a_id": s_a,
                "skill_a_name": self.skills_by_id[s_a]["name"],
                "skill_b_id": s_b,
                "skill_b_name": self.skills_by_id[s_b]["name"],
                "co_occurrence_count": pair_count,
                "co_occurrence_percentage": round((pair_count / total_jobs) * 100.0, 2)
            })

        # Deterministic sort: co_occurrence_count DESC, skill_a_id ASC, skill_b_id ASC
        co_occurrence_list.sort(key=lambda x: (-x["co_occurrence_count"], x["skill_a_id"], x["skill_b_id"]))

        # 5. Temporal Availability Inspection
        has_dates = all("posted_at" in j and j["posted_at"] is not None for j in jobs)
        if not has_dates:
            temporal_analysis = {
                "status": "not_available",
                "reason": "Phase 2 batch artifact retains minimal provenance schema and does not store posting dates."
            }
        else:
            temporal_analysis = {
                "status": "available",
                "periods": []
            }

        artifact = {
            "metadata": {
                "phase": "3",
                "pipeline": "skill_demand_aggregation",
                "input_artifact": str(self.input_path.as_posix()),
                "taxonomy_version": self.input_data.get("metadata", {}).get("taxonomy_version", "1"),
                "total_jobs": total_jobs,
                "jobs_with_skills": jobs_with_skills_count,
                "zero_skill_jobs": zero_skill_jobs_count,
                "total_skill_mentions": total_skill_mentions_count,
                "unique_skills_detected": detected_unique_skills,
                "scope_note": "Observed demand metrics calculated across the deduplicated Phase 3 evaluation corpus."
            },
            "skills": skills_summary,
            "source_demand": source_demand,
            "categories": categories_summary,
            "co_occurrence": co_occurrence_list,
            "temporal_analysis": temporal_analysis
        }
        return artifact

    def run_and_save(self, output_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
        out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
        artifact = self.aggregate()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        return artifact, out_file
