import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

DEFAULT_DEMAND_PATH = Path(__file__).resolve().parent.parent / "demand" / "demand_analysis.json"
DEFAULT_EMPLOYER_PATH = Path(__file__).resolve().parent.parent / "employer" / "employer_feedback_analysis.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "multi_signal_evidence.json"

class MultiSignalEvidenceAggregator:
    """
    Combines two independent, validated sources of skill evidence:
      1. Job-posting demand from Phase 3 (demand_analysis.json)
      2. Employer-feedback validation from Phase 5A (employer_feedback_analysis.json)
    Preserves all measurements separately without arbitrary score synthesis.
    """

    def __init__(
        self,
        demand_artifact_path: Optional[Path] = None,
        employer_artifact_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.demand_path = demand_artifact_path or DEFAULT_DEMAND_PATH
        self.employer_path = employer_artifact_path or DEFAULT_EMPLOYER_PATH
        self.taxonomy_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.demand_path.exists():
            raise FileNotFoundError(f"Missing Phase 3 demand artifact at {self.demand_path}")
        if not self.employer_path.exists():
            raise FileNotFoundError(f"Missing Phase 5A employer artifact at {self.employer_path}")
        if not self.taxonomy_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.taxonomy_path}")

        with open(self.demand_path, "r", encoding="utf-8") as f:
            self.demand_data: Dict[str, Any] = json.load(f)

        with open(self.employer_path, "r", encoding="utf-8") as f:
            self.employer_data: Dict[str, Any] = json.load(f)

        with open(self.taxonomy_path, "r", encoding="utf-8") as f:
            self.taxonomy_data: List[Dict[str, Any]] = json.load(f)

        self._index_taxonomy_and_inputs()

    def _index_taxonomy_and_inputs(self):
        self.skills_by_id: Dict[str, Dict[str, Any]] = {}
        for s in self.taxonomy_data:
            s_id = s["id"]
            self.skills_by_id[s_id] = {
                "id": s_id,
                "name": s["name"],
                "category": s["category"]
            }
        self.valid_skill_ids = set(self.skills_by_id.keys())
        self.taxonomy_version = str(self.taxonomy_data[0].get("version", "1")) if self.taxonomy_data else "1"

        # Index Phase 3 demand
        self.demand_skills_map: Dict[str, Dict[str, Any]] = {}
        for s in self.demand_data.get("skills", []):
            s_id = s["skill_id"]
            if s_id not in self.valid_skill_ids:
                raise ValueError(f"Demand artifact contains unknown skill '{s_id}'")
            self.demand_skills_map[s_id] = s

        # Index Phase 5A employer signals
        self.employer_skills_map: Dict[str, Dict[str, Any]] = {}
        for s in self.employer_data.get("skill_signals", []):
            s_id = s["skill_id"]
            if s_id not in self.valid_skill_ids:
                raise ValueError(f"Employer artifact contains unknown skill '{s_id}'")
            self.employer_skills_map[s_id] = s

    def aggregate(self) -> Dict[str, Any]:
        demand_meta = self.demand_data.get("metadata", {})
        employer_meta = self.employer_data.get("metadata", {})

        total_jobs = demand_meta.get("total_jobs", 295)
        total_fb_records = employer_meta.get("total_feedback_records", 5)

        demand_skill_set = set(self.demand_skills_map.keys())
        employer_skill_set = set(self.employer_skills_map.keys())
        union_skill_set = sorted(list(demand_skill_set | employer_skill_set))

        skills_output: List[Dict[str, Any]] = []
        evidence_matrix: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        both_count = 0
        job_only_count = 0
        employer_only_count = 0

        for s_id in union_skill_set:
            s_name = self.skills_by_id[s_id]["name"]
            s_cat = self.skills_by_id[s_id]["category"]

            in_demand = s_id in demand_skill_set
            in_employer = s_id in employer_skill_set

            if in_demand and in_employer:
                rel = "both"
                sources = ["job_postings", "employer_feedback"]
                both_count += 1
            elif in_demand:
                rel = "job_only"
                sources = ["job_postings"]
                job_only_count += 1
            else:
                rel = "employer_feedback_only"
                sources = ["employer_feedback"]
                employer_only_count += 1

            # Build job_demand block
            if in_demand:
                d_entry = self.demand_skills_map[s_id]
                job_demand_block = {
                    "observed": True,
                    "job_count": d_entry["job_count"],
                    "total_jobs": total_jobs,
                    "demand_share": d_entry["demand_share"],
                    "demand_percentage": d_entry["demand_percentage"],
                    "source_coverage_count": d_entry["source_coverage_count"],
                    "sources_present": d_entry.get("sources_present", [])
                }
            else:
                job_demand_block = {
                    "observed": False,
                    "job_count": None,
                    "total_jobs": None,
                    "demand_share": None,
                    "demand_percentage": None,
                    "source_coverage_count": None,
                    "sources_present": None
                }

            # Build employer_validation block
            if in_employer:
                e_entry = self.employer_skills_map[s_id]
                employer_block = {
                    "observed": True,
                    "feedback_count": e_entry["feedback_count"],
                    "unique_employer_count": e_entry["unique_employer_count"],
                    "weighted_signal_sum": e_entry["weighted_signal_sum"],
                    "average_weighted_signal": e_entry["average_weighted_signal"],
                    "max_weighted_signal": e_entry["max_weighted_signal"]
                }
            else:
                employer_block = {
                    "observed": False,
                    "feedback_count": None,
                    "unique_employer_count": None,
                    "weighted_signal_sum": None,
                    "average_weighted_signal": None,
                    "max_weighted_signal": None
                }

            # Generate descriptive summary strictly from facts
            if in_demand and in_employer:
                j_cnt = job_demand_block["job_count"]
                e_emp = employer_block["unique_employer_count"]
                e_fb = employer_block["feedback_count"]
                desc = f"Observed in {j_cnt} of {total_jobs} job postings and mentioned across {e_fb} feedback records from {e_emp} employer(s)."
            elif in_demand:
                j_cnt = job_demand_block["job_count"]
                desc = f"Observed in {j_cnt} of {total_jobs} job postings; no employer feedback observed in current sample."
            else:
                e_emp = employer_block["unique_employer_count"]
                e_fb = employer_block["feedback_count"]
                desc = f"Mentioned across {e_fb} feedback records from {e_emp} employer(s); no job posting occurrences in current sample."

            skills_output.append({
                "skill_id": s_id,
                "skill_name": s_name,
                "category": s_cat,
                "evidence_relationship": rel,
                "evidence_sources": sources,
                "job_demand": job_demand_block,
                "employer_validation": employer_block,
                "description": desc
            })

            evidence_matrix.append({
                "skill_id": s_id,
                "skill_name": s_name,
                "category": s_cat,
                "job_postings": in_demand,
                "employer_feedback": in_employer
            })

        # Deterministic sort: skill_id ASC
        skills_output.sort(key=lambda x: x["skill_id"])
        evidence_matrix.sort(key=lambda x: x["skill_id"])

        artifact = {
            "metadata": {
                "phase": "5B",
                "pipeline": "multi_signal_skill_evidence",
                "job_demand_input": str(self.demand_path.as_posix()),
                "employer_feedback_input": str(self.employer_path.as_posix()),
                "taxonomy_version": self.taxonomy_version,
                "job_dataset_total_jobs": total_jobs,
                "job_dataset_skill_count": len(demand_skill_set),
                "employer_feedback_total_records": total_fb_records,
                "employer_feedback_skill_count": len(employer_skill_set),
                "union_skill_count": len(union_skill_set),
                "both_sources_skill_count": both_count,
                "job_only_skill_count": job_only_count,
                "employer_only_skill_count": employer_only_count,
                "scope_note": "Multi-signal evidence record combining job posting demand and employer feedback validation without arbitrary score synthesis."
            },
            "skills": skills_output,
            "evidence_matrix": evidence_matrix,
            "errors": errors
        }
        return artifact

    def run_and_save(self, output_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
        out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
        artifact = self.aggregate()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        return artifact, out_file
