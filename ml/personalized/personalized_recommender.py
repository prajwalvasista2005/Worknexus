import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

DEFAULT_GAP_INPUT_PATH = Path(__file__).resolve().parent.parent / "gap_student" / "student_skill_gaps.json"
DEFAULT_RECOMMENDATION_PATH = Path(__file__).resolve().parent.parent / "recommend" / "skill_recommendations.json"
DEFAULT_CONTEXT_PATH = Path(__file__).resolve().parent.parent / "context" / "contextual_recommendations.json"
DEFAULT_EVIDENCE_PATH = Path(__file__).resolve().parent.parent / "evidence" / "multi_signal_evidence.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "student_skill_recommendations.json"

class PersonalizedSkillRecommendationEngine:
    """
    Deterministic Personalized Skill Recommendation Engine.
    Evaluates student-role skill gaps against Phase 6A generic recommendations
    and Phase 5B multi-signal evidence to generate explainable, evidence-backed
    skill development candidates without scoring, ranking, or course assignments.
    """

    def __init__(
        self,
        student_gap_path: Optional[Path] = None,
        recommendation_path: Optional[Path] = None,
        context_path: Optional[Path] = None,
        evidence_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.gap_path = student_gap_path or DEFAULT_GAP_INPUT_PATH
        self.rec_path = recommendation_path or DEFAULT_RECOMMENDATION_PATH
        self.context_path = context_path or DEFAULT_CONTEXT_PATH
        self.ev_path = evidence_path or DEFAULT_EVIDENCE_PATH
        self.tax_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.gap_path.exists():
            raise FileNotFoundError(f"Missing student skill gaps artifact at {self.gap_path}")
        if not self.rec_path.exists():
            raise FileNotFoundError(f"Missing generic recommendations artifact at {self.rec_path}")
        if not self.context_path.exists():
            raise FileNotFoundError(f"Missing contextual recommendations artifact at {self.context_path}")
        if not self.ev_path.exists():
            raise FileNotFoundError(f"Missing multi-signal evidence artifact at {self.ev_path}")
        if not self.tax_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.tax_path}")

        with open(self.gap_path, "r", encoding="utf-8") as f:
            self.gap_data: Dict[str, Any] = json.load(f)

        with open(self.rec_path, "r", encoding="utf-8") as f:
            self.rec_data: Dict[str, Any] = json.load(f)

        with open(self.context_path, "r", encoding="utf-8") as f:
            self.context_data: Dict[str, Any] = json.load(f)

        with open(self.ev_path, "r", encoding="utf-8") as f:
            self.ev_data: Dict[str, Any] = json.load(f)

        with open(self.tax_path, "r", encoding="utf-8") as f:
            self.tax_data: List[Dict[str, Any]] = json.load(f)

        self._index_inputs()

    def _index_inputs(self):
        # Index taxonomy
        self.skills_by_id: Dict[str, Dict[str, Any]] = {}
        for s in self.tax_data:
            s_id = s["id"]
            self.skills_by_id[s_id] = {
                "id": s_id,
                "name": s["name"],
                "category": s["category"]
            }
        self.valid_skill_ids = set(self.skills_by_id.keys())
        self.taxonomy_version = str(self.tax_data[0].get("version", "1")) if self.tax_data else "1"

        # Index Phase 6A generic recommendations
        self.rec_by_id: Dict[str, Dict[str, Any]] = {}
        for r in self.rec_data.get("recommendations", []):
            self.rec_by_id[r["skill_id"]] = r

        # Index Phase 5B evidence
        self.ev_by_id: Dict[str, Dict[str, Any]] = {}
        for e in self.ev_data.get("skills", []):
            self.ev_by_id[e["skill_id"]] = e

    def recommend(self) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        students_output: List[Dict[str, Any]] = []

        total_role_skill_records = 0
        total_personalized_recs = 0
        total_already_present = 0
        total_not_recommended = 0
        total_unavailable_context = 0

        for stu_gap in self.gap_data.get("students", []):
            stu_id = stu_gap.get("student_id")
            prof_name = stu_gap.get("profile_name", "")
            role_info = stu_gap.get("role", {})
            role_id = role_info.get("role_id")
            role_name = role_info.get("role_name", "")

            skill_gaps = stu_gap.get("skill_gaps", [])

            recommended_skills: List[str] = []
            already_present_skills: List[str] = []
            not_recommended_skills: List[str] = []
            unavailable_context_skills: List[str] = []

            skill_recommendations: List[Dict[str, Any]] = []

            for gap in skill_gaps:
                s_id = gap.get("skill_id")
                s_name = gap.get("skill_name") or self.skills_by_id.get(s_id, {}).get("name", s_id)
                category = gap.get("category") or self.skills_by_id.get(s_id, {}).get("category", "")
                student_status = gap.get("status")  # "present" or "missing"
                stu_has_skill = gap.get("student_has_skill", False)
                stu_evidence = gap.get("student_evidence", [])
                ctx_status = gap.get("contextual_recommendation_status", "not_available")
                ctx_reason = gap.get("context_reason", {})

                total_role_skill_records += 1

                if ctx_status == "not_available":
                    unavailable_context_skills.append(s_id)
                    total_unavailable_context += 1

                # Retrieve Phase 6A entry & Phase 5B evidence entry
                rec_entry = self.rec_by_id.get(s_id, {})
                ev_entry = self.ev_by_id.get(s_id, {})

                gen_status = rec_entry.get("recommendation", {}).get("status", "not_recommended") if rec_entry else "not_available"
                gen_reasons = rec_entry.get("recommendation", {}).get("reason_ids", []) if rec_entry else []

                ev_block = rec_entry.get("evidence") or ev_entry or {
                    "job_demand": {"observed": False, "job_count": None, "demand_percentage": None},
                    "employer_validation": {"observed": False, "unique_employer_count": None, "weighted_signal": None},
                    "evidence_relationship": "unobserved"
                }

                # Evaluate personalized recommendation status & reason IDs
                reason_ids: List[str] = []

                if student_status == "present" or stu_has_skill:
                    personalized_status = "already_present"
                    already_present_skills.append(s_id)
                    total_already_present += 1
                    reason_ids.append("already_present")
                else:
                    # Student is MISSING the skill
                    reason_ids.append("student_skill_gap")
                    reason_ids.append("role_requirement")

                    if ctx_status == "not_available":
                        personalized_status = "not_recommended"
                        not_recommended_skills.append(s_id)
                        total_not_recommended += 1
                        reason_ids.append("contextual_evidence_unavailable")
                    elif gen_status == "recommended":
                        personalized_status = "recommended"
                        recommended_skills.append(s_id)
                        total_personalized_recs += 1
                        reason_ids.append("generic_evidence_recommended")

                        # Check market demand evidence
                        job_dem = ev_block.get("job_demand", {})
                        if job_dem.get("observed") and (job_dem.get("job_count") or 0) > 0:
                            reason_ids.append("market_demand_evidence")

                        # Check employer validation evidence
                        emp_val = ev_block.get("employer_validation", {})
                        if emp_val.get("observed") and (emp_val.get("unique_employer_count") or 0) > 0:
                            reason_ids.append("employer_validation_evidence")

                        # Check multi-source evidence
                        if ev_block.get("evidence_relationship") == "both":
                            reason_ids.append("multi_source_evidence")

                        # Check course coverage gap
                        if "course_coverage_gap" in gen_reasons:
                            reason_ids.append("course_coverage_gap")
                    else:
                        # generic status is not_recommended
                        personalized_status = "not_recommended"
                        not_recommended_skills.append(s_id)
                        total_not_recommended += 1

                skill_recommendations.append({
                    "student_id": stu_id,
                    "role": {
                        "role_id": role_id,
                        "role_name": role_name
                    },
                    "skill_id": s_id,
                    "skill_name": s_name,
                    "category": category,
                    "student_status": student_status,
                    "personalized_status": personalized_status,
                    "recommendation_reason_ids": reason_ids,
                    "student_evidence": stu_evidence,
                    "evidence": ev_block,
                    "generic_recommendation": {
                        "status": gen_status,
                        "reason_ids": gen_reasons
                    },
                    "context": {
                        "contextual_recommendation_status": ctx_status,
                        "context_reason": ctx_reason
                    }
                })

            # Sort deterministically
            recommended_skills.sort()
            already_present_skills.sort()
            not_recommended_skills.sort()
            unavailable_context_skills.sort()
            skill_recommendations.sort(key=lambda x: x["skill_id"])

            students_output.append({
                "student_id": stu_id,
                "profile_name": prof_name,
                "role": {
                    "role_id": role_id,
                    "role_name": role_name
                },
                "summary": {
                    "total_role_skills": len(skill_recommendations),
                    "already_present_count": len(already_present_skills),
                    "recommended_skill_count": len(recommended_skills),
                    "not_recommended_missing_count": len(not_recommended_skills),
                    "unavailable_context_count": len(unavailable_context_skills)
                },
                "recommended_skills": recommended_skills,
                "already_present_skills": already_present_skills,
                "not_recommended_skills": not_recommended_skills,
                "skill_recommendations": skill_recommendations
            })

        # Sort students by student_id ASC
        students_output.sort(key=lambda x: x["student_id"])

        artifact = {
            "metadata": {
                "phase": "7C",
                "pipeline": "personalized_skill_recommendation",
                "student_gap_input": str(self.gap_path.as_posix()),
                "generic_recommendation_input": str(self.rec_path.as_posix()),
                "context_input": str(self.context_path.as_posix()),
                "evidence_input": str(self.ev_path.as_posix()),
                "taxonomy_version": self.taxonomy_version,
                "total_students": len(students_output),
                "total_role_skill_records": total_role_skill_records,
                "total_personalized_recommendations": total_personalized_recs,
                "total_already_present_skills": total_already_present,
                "total_not_recommended_missing_skills": total_not_recommended,
                "total_unavailable_context_skills": total_unavailable_context,
                "scope_note": "Personalized skill recommendations for assigned student-role pairs based on validated skill gaps and multi-source evidence without scoring, rankings, or course assignments."
            },
            "students": students_output,
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
