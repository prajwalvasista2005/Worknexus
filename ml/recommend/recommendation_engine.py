import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict

DEFAULT_EVIDENCE_PATH = Path(__file__).resolve().parent.parent / "evidence" / "multi_signal_evidence.json"
DEFAULT_GAP_PATH = Path(__file__).resolve().parent.parent / "gap" / "skill_gap_analysis.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "skill_recommendations.json"

class GenericSkillRecommendationEngine:
    """
    Deterministic rule-based generic skill recommendation engine.
    Applies explicit, transparent evidence rules over Phase 5B multi-signal evidence
    and Phase 4 course gap context without universal score synthesis or black-box rankings.
    """

    def __init__(
        self,
        evidence_artifact_path: Optional[Path] = None,
        gap_artifact_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.evidence_path = evidence_artifact_path or DEFAULT_EVIDENCE_PATH
        self.gap_path = gap_artifact_path or DEFAULT_GAP_PATH
        self.taxonomy_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.evidence_path.exists():
            raise FileNotFoundError(f"Missing Phase 5B evidence artifact at {self.evidence_path}")
        if not self.gap_path.exists():
            raise FileNotFoundError(f"Missing Phase 4 gap artifact at {self.gap_path}")
        if not self.taxonomy_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.taxonomy_path}")

        with open(self.evidence_path, "r", encoding="utf-8") as f:
            self.evidence_data: Dict[str, Any] = json.load(f)

        with open(self.gap_path, "r", encoding="utf-8") as f:
            self.gap_data: Dict[str, Any] = json.load(f)

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

        # Index course coverage from Phase 4
        self.course_coverage_map: Dict[str, List[Any]] = defaultdict(list)
        for c in self.gap_data.get("courses", []):
            cid = c.get("course_id")
            for sid in c.get("course_skills", []):
                self.course_coverage_map[sid].append(cid)

    def recommend(self) -> Dict[str, Any]:
        evidence_skills = self.evidence_data.get("skills", [])
        total_skills_count = len(evidence_skills)

        recommendations_list: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        recommended_count = 0
        not_recommended_count = 0

        for s in evidence_skills:
            s_id = s["skill_id"]
            if s_id not in self.valid_skill_ids:
                errors.append({
                    "skill_id": s_id,
                    "error": f"Skill '{s_id}' not found in taxonomy."
                })
                continue

            s_name = s.get("skill_name") or self.skills_by_id[s_id]["name"]
            s_cat = s.get("category") or self.skills_by_id[s_id]["category"]

            job_demand = s.get("job_demand", {})
            employer_val = s.get("employer_validation", {})

            # Rule A: Market Demand
            market_demand = bool(job_demand.get("observed") and (job_demand.get("job_count") or 0) > 0)

            # Rule B: Employer Validation
            employer_validation = bool(employer_val.get("observed") and (employer_val.get("unique_employer_count") or 0) > 0)

            # Rule C: Course Coverage
            covered_course_ids = sorted(self.course_coverage_map.get(s_id, []))
            course_coverage = len(covered_course_ids) > 0

            # Rule D: Multi-Source Evidence
            multi_source_evidence = bool(s.get("evidence_relationship") == "both")

            decision_factors = {
                "market_demand": market_demand,
                "employer_validation": employer_validation,
                "course_coverage": course_coverage,
                "multi_source_evidence": multi_source_evidence
            }

            # Rule E: Recommendation Conditions
            cond1 = market_demand and employer_validation
            cond2 = market_demand and not course_coverage
            cond3 = employer_validation and not market_demand

            is_recommended = cond1 or cond2 or cond3

            reason_ids: List[str] = []
            if is_recommended:
                recommended_count += 1
                status = "recommended"

                if market_demand:
                    reason_ids.append("observed_market_demand")
                if employer_validation:
                    reason_ids.append("employer_validated")
                if multi_source_evidence:
                    reason_ids.append("observed_in_both_sources")
                if cond2:
                    reason_ids.append("course_coverage_gap")
                if cond3:
                    reason_ids.append("employer_only_signal")
            else:
                not_recommended_count += 1
                status = "not_recommended"
                reason_ids = []

            recommendations_list.append({
                "skill_id": s_id,
                "skill_name": s_name,
                "category": s_cat,
                "recommendation": {
                    "status": status,
                    "reason_ids": reason_ids
                },
                "decision_factors": decision_factors,
                "evidence": {
                    "evidence_relationship": s.get("evidence_relationship"),
                    "evidence_sources": s.get("evidence_sources", []),
                    "job_demand": job_demand,
                    "employer_validation": employer_val,
                    "description": s.get("description", "")
                },
                "course_context": {
                    "covered_by_course": course_coverage,
                    "covering_course_ids": covered_course_ids
                }
            })

        # Deterministic sort: skill_id ASC
        recommendations_list.sort(key=lambda x: x["skill_id"])

        artifact = {
            "metadata": {
                "phase": "6A",
                "pipeline": "generic_skill_recommendation",
                "evidence_input": str(self.evidence_path.as_posix()),
                "course_gap_input": str(self.gap_path.as_posix()),
                "taxonomy_version": self.taxonomy_version,
                "recommendation_rule_version": "6A-v1",
                "total_skills": total_skills_count,
                "recommended_skills": recommended_count,
                "not_recommended_skills": not_recommended_count,
                "scope_note": "Generic rule-based skill recommendations derived strictly from market demand, employer validation, and curriculum gap evidence without black-box scoring."
            },
            "recommendations": recommendations_list,
            "errors": errors
        }
        return artifact

    def run_and_save(self, output_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
        out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
        artifact = self.recommend()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        return artifact, out_file
