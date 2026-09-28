import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

DEFAULT_STUDENT_PROFILE_PATH = Path(__file__).resolve().parent.parent / "student" / "student_skill_profiles.json"
DEFAULT_ROLE_CONTEXT_PATH = Path(__file__).resolve().parent.parent / "context" / "contextual_recommendations.json"
DEFAULT_ROLE_ASSIGNMENT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_student_role_assignments.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "student_skill_gaps.json"

class StudentSkillGapAnalyzer:
    """
    Deterministic Student Skill Gap Analysis engine.
    Compares a student's current canonical skills against explicit target-role requirements
    derived from Phase 6B contextual recommendations without computing proficiency match scores.
    """

    def __init__(
        self,
        student_profile_path: Optional[Path] = None,
        role_context_path: Optional[Path] = None,
        role_assignment_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.profile_path = student_profile_path or DEFAULT_STUDENT_PROFILE_PATH
        self.role_path = role_context_path or DEFAULT_ROLE_CONTEXT_PATH
        self.assignment_path = role_assignment_path or DEFAULT_ROLE_ASSIGNMENT_PATH
        self.tax_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.profile_path.exists():
            raise FileNotFoundError(f"Missing student profiles artifact at {self.profile_path}")
        if not self.role_path.exists():
            raise FileNotFoundError(f"Missing Phase 6B role context artifact at {self.role_path}")
        if not self.assignment_path.exists():
            raise FileNotFoundError(f"Missing student-role assignments dataset at {self.assignment_path}")
        if not self.tax_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.tax_path}")

        with open(self.profile_path, "r", encoding="utf-8") as f:
            self.profile_data: Dict[str, Any] = json.load(f)

        with open(self.role_path, "r", encoding="utf-8") as f:
            self.role_data: Dict[str, Any] = json.load(f)

        with open(self.assignment_path, "r", encoding="utf-8") as f:
            self.assignment_data: Dict[str, Any] = json.load(f)

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

        # Index student profiles
        self.students_by_id: Dict[str, Dict[str, Any]] = {}
        for s in self.profile_data.get("students", []):
            self.students_by_id[s["student_id"]] = s

        # Index role contexts from Phase 6B
        self.roles_by_id: Dict[str, Dict[str, Any]] = {}
        for r in self.role_data.get("roles", []):
            self.roles_by_id[r["role_id"]] = r

    def analyze_gaps(self) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        raw_assignments = self.assignment_data.get("assignments", [])

        if not isinstance(raw_assignments, list):
            raise ValueError("Role assignments root must contain an 'assignments' list.")

        # Validation of assignments
        seen_assignment_students: Set[str] = set()
        valid_assignments: List[Dict[str, str]] = []

        all_profile_student_ids = set(self.students_by_id.keys())

        for a_idx, assign in enumerate(raw_assignments):
            if not isinstance(assign, dict):
                errors.append({"index": a_idx, "error": "Assignment entry must be a dictionary."})
                continue

            stu_id = assign.get("student_id")
            role_id = assign.get("role_id")

            if not stu_id or stu_id not in self.students_by_id:
                errors.append({
                    "index": a_idx,
                    "student_id": stu_id,
                    "error": f"Assigned student_id '{stu_id}' not found in Phase 7A student profiles."
                })
                continue

            if not role_id or role_id not in self.roles_by_id:
                errors.append({
                    "index": a_idx,
                    "role_id": role_id,
                    "error": f"Assigned role_id '{role_id}' not found in Phase 6B role contexts."
                })
                continue

            if stu_id in seen_assignment_students:
                errors.append({
                    "index": a_idx,
                    "student_id": stu_id,
                    "error": f"Duplicate assignment for student_id '{stu_id}'."
                })
                continue
            seen_assignment_students.add(stu_id)

            valid_assignments.append({
                "student_id": stu_id,
                "role_id": role_id
            })

        # Check that all synthetic students have an assignment
        missing_assignment_students = all_profile_student_ids - seen_assignment_students
        if missing_assignment_students:
            for m_id in sorted(list(missing_assignment_students)):
                errors.append({
                    "student_id": m_id,
                    "error": f"Student '{m_id}' is missing a target role assignment."
                })

        output_students: List[Dict[str, Any]] = []
        total_role_skill_records = 0
        total_present_skills = 0
        total_missing_skills = 0
        total_unavailable_context_skills = 0

        for assign in valid_assignments:
            stu_id = assign["student_id"]
            role_id = assign["role_id"]

            student_profile = self.students_by_id[stu_id]
            role_context = self.roles_by_id[role_id]

            # Index student skills by skill_id
            student_skills_map: Dict[str, Dict[str, Any]] = {
                sk["skill_id"]: sk for sk in student_profile.get("skills", [])
            }

            role_skill_context = role_context.get("role_skill_context", [])
            total_role_skills = len(role_skill_context)

            present_skills: List[str] = []
            missing_skills: List[str] = []
            unavailable_context_skills: List[str] = []
            skill_gaps: List[Dict[str, Any]] = []

            for r_sk in role_skill_context:
                s_id = r_sk["skill_id"]
                s_name = r_sk.get("skill_name") or self.skills_by_id.get(s_id, {}).get("name", s_id)
                category = r_sk.get("category") or self.skills_by_id.get(s_id, {}).get("category", "")
                gen_status = r_sk.get("generic_recommendation_status", "not_available")
                ctx_reason = r_sk.get("context_reason", {})

                # Check if role skill has unavailable contextual evidence in Phase 6B
                is_context_unavailable = (gen_status == "not_available")
                if is_context_unavailable:
                    unavailable_context_skills.append(s_id)
                    total_unavailable_context_skills += 1

                total_role_skill_records += 1

                # Check if student possesses the skill
                if s_id in student_skills_map:
                    # Skill is PRESENT
                    stu_sk_record = student_skills_map[s_id]
                    stu_evidence = stu_sk_record.get("evidence", [])
                    # Sort evidence deterministically
                    sorted_evidence = sorted(stu_evidence, key=lambda x: (x["evidence_type"], x["evidence_strength"]))

                    present_skills.append(s_id)
                    total_present_skills += 1

                    skill_gaps.append({
                        "skill_id": s_id,
                        "skill_name": s_name,
                        "category": category,
                        "status": "present",
                        "student_has_skill": True,
                        "role_requires_skill": True,
                        "generic_recommendation_status": gen_status,
                        "contextual_recommendation_status": gen_status,
                        "student_evidence": sorted_evidence,
                        "context_reason": ctx_reason
                    })
                else:
                    # Skill is MISSING from student
                    missing_skills.append(s_id)
                    total_missing_skills += 1

                    skill_gaps.append({
                        "skill_id": s_id,
                        "skill_name": s_name,
                        "category": category,
                        "status": "missing",
                        "student_has_skill": False,
                        "role_requires_skill": True,
                        "generic_recommendation_status": gen_status,
                        "contextual_recommendation_status": gen_status,
                        "student_evidence": [],
                        "context_reason": ctx_reason
                    })

            # Sort deterministically
            present_skills.sort()
            missing_skills.sort()
            unavailable_context_skills.sort()
            skill_gaps.sort(key=lambda x: x["skill_id"])

            output_students.append({
                "student_id": stu_id,
                "profile_name": student_profile.get("profile_name", ""),
                "role": {
                    "role_id": role_id,
                    "role_name": role_context.get("role_name", "")
                },
                "summary": {
                    "total_role_skills": total_role_skills,
                    "present_skill_count": len(present_skills),
                    "missing_skill_count": len(missing_skills),
                    "unavailable_context_count": len(unavailable_context_skills)
                },
                "present_skills": present_skills,
                "missing_skills": missing_skills,
                "unavailable_context_skills": unavailable_context_skills,
                "skill_gaps": skill_gaps
            })

        # Sort students by student_id ASC
        output_students.sort(key=lambda x: x["student_id"])

        artifact = {
            "metadata": {
                "phase": "7B",
                "pipeline": "student_skill_gap_analysis",
                "student_profile_input": str(self.profile_path.as_posix()),
                "role_context_input": str(self.role_path.as_posix()),
                "role_assignment_input": str(self.assignment_path.as_posix()),
                "taxonomy_version": self.taxonomy_version,
                "total_students": len(output_students),
                "total_assignments": len(valid_assignments),
                "total_role_skill_records": total_role_skill_records,
                "total_present_skills": total_present_skills,
                "total_missing_skills": total_missing_skills,
                "total_unavailable_context_skills": total_unavailable_context_skills,
                "scope_note": "Student skill gap analysis comparing normalized student profiles against explicit target-role requirements using canonical skill ID matching without proficiency scoring, percentage match, or recommendations."
            },
            "students": output_students,
            "errors": errors
        }
        return artifact

    def run_and_save(self, output_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
        out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
        artifact = self.analyze_gaps()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        return artifact, out_file
