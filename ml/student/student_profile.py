import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

DEFAULT_STUDENT_PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_student_profiles.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "student_skill_profiles.json"

ALLOWED_EVIDENCE_TYPES = {
    "self_reported",
    "course_completed",
    "project",
    "certification",
    "assessment"
}

ALLOWED_EVIDENCE_STRENGTHS = {
    "basic",
    "intermediate",
    "advanced"
}

class StudentProfileEngine:
    """
    Deterministic student skill profile engine.
    Validates, normalizes, and taxonomy-links a student's current skills
    and multi-source evidence provenance without synthesizing numerical proficiency scores.
    """

    def __init__(
        self,
        student_profile_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.profile_path = student_profile_path or DEFAULT_STUDENT_PROFILE_PATH
        self.tax_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.profile_path.exists():
            raise FileNotFoundError(f"Missing student profiles dataset at {self.profile_path}")
        if not self.tax_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.tax_path}")

        with open(self.profile_path, "r", encoding="utf-8") as f:
            self.student_data: List[Dict[str, Any]] = json.load(f)

        with open(self.tax_path, "r", encoding="utf-8") as f:
            self.tax_data: List[Dict[str, Any]] = json.load(f)

        self._index_taxonomy()

    def _index_taxonomy(self):
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

    def process_profiles(self) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        normalized_students: List[Dict[str, Any]] = []
        seen_student_ids: Set[str] = set()

        total_skill_records = 0
        all_unique_skill_ids: Set[str] = set()
        category_counts: Dict[str, int] = {}

        if not isinstance(self.student_data, list):
            raise ValueError("Student profiles dataset root must be a list.")

        for s_idx, raw_student in enumerate(self.student_data):
            if not isinstance(raw_student, dict):
                errors.append({
                    "index": s_idx,
                    "error": "Student record must be a dictionary."
                })
                continue

            student_id = raw_student.get("student_id")
            profile_name = raw_student.get("profile_name")
            raw_skills = raw_student.get("skills")

            # Validate student_id
            if not student_id or not isinstance(student_id, str) or not student_id.strip():
                errors.append({
                    "index": s_idx,
                    "student_id": student_id,
                    "error": "Student ID must be a non-empty string."
                })
                continue

            student_id = student_id.strip()
            if student_id in seen_student_ids:
                errors.append({
                    "index": s_idx,
                    "student_id": student_id,
                    "error": f"Duplicate student_id '{student_id}'."
                })
                continue
            seen_student_ids.add(student_id)

            # Validate profile_name
            if not profile_name or not isinstance(profile_name, str) or not profile_name.strip():
                errors.append({
                    "student_id": student_id,
                    "error": "Profile name must be a non-empty string."
                })
                continue
            profile_name = profile_name.strip()

            # Validate skills list
            if not isinstance(raw_skills, list):
                errors.append({
                    "student_id": student_id,
                    "error": "Skills field must be a list."
                })
                continue

            seen_skill_ids: Set[str] = set()
            normalized_skills: List[Dict[str, Any]] = []
            student_categories: Set[str] = set()

            for sk_idx, raw_sk in enumerate(raw_skills):
                if not isinstance(raw_sk, dict):
                    errors.append({
                        "student_id": student_id,
                        "skill_index": sk_idx,
                        "error": "Skill entry must be a dictionary."
                    })
                    continue

                skill_id = raw_sk.get("skill_id")
                if not skill_id or not isinstance(skill_id, str) or not skill_id.strip():
                    errors.append({
                        "student_id": student_id,
                        "skill_index": sk_idx,
                        "error": "Skill ID must be a non-empty string."
                    })
                    continue

                skill_id = skill_id.strip()
                if skill_id not in self.valid_skill_ids:
                    errors.append({
                        "student_id": student_id,
                        "skill_id": skill_id,
                        "error": f"Skill ID '{skill_id}' does not exist in canonical taxonomy."
                    })
                    continue

                if skill_id in seen_skill_ids:
                    errors.append({
                        "student_id": student_id,
                        "skill_id": skill_id,
                        "error": f"Duplicate skill_id '{skill_id}' in student profile."
                    })
                    continue
                seen_skill_ids.add(skill_id)

                # Process evidence
                raw_evidence_list = []
                if "evidence" in raw_sk:
                    if not isinstance(raw_sk["evidence"], list) or len(raw_sk["evidence"]) == 0:
                        errors.append({
                            "student_id": student_id,
                            "skill_id": skill_id,
                            "error": "Evidence list must be a non-empty list."
                        })
                        continue
                    raw_evidence_list = raw_sk["evidence"]
                else:
                    # Single flat evidence entry
                    ev_type = raw_sk.get("evidence_type")
                    ev_strength = raw_sk.get("evidence_strength")
                    if not ev_type or not ev_strength:
                        errors.append({
                            "student_id": student_id,
                            "skill_id": skill_id,
                            "error": "Missing evidence specification (either 'evidence' list or 'evidence_type' + 'evidence_strength')."
                        })
                        continue
                    raw_evidence_list = [{
                        "evidence_type": ev_type,
                        "evidence_strength": ev_strength
                    }]

                normalized_evidence: List[Dict[str, str]] = []
                ev_valid = True
                for ev_entry in raw_evidence_list:
                    if not isinstance(ev_entry, dict):
                        errors.append({
                            "student_id": student_id,
                            "skill_id": skill_id,
                            "error": "Evidence entry must be a dictionary."
                        })
                        ev_valid = False
                        break

                    ev_type = ev_entry.get("evidence_type")
                    ev_strength = ev_entry.get("evidence_strength")

                    if ev_type not in ALLOWED_EVIDENCE_TYPES:
                        errors.append({
                            "student_id": student_id,
                            "skill_id": skill_id,
                            "evidence_type": ev_type,
                            "error": f"Invalid evidence_type '{ev_type}'. Allowed types: {sorted(list(ALLOWED_EVIDENCE_TYPES))}."
                        })
                        ev_valid = False
                        break

                    if ev_strength not in ALLOWED_EVIDENCE_STRENGTHS:
                        errors.append({
                            "student_id": student_id,
                            "skill_id": skill_id,
                            "evidence_strength": ev_strength,
                            "error": f"Invalid evidence_strength '{ev_strength}'. Allowed values: {sorted(list(ALLOWED_EVIDENCE_STRENGTHS))}."
                        })
                        ev_valid = False
                        break

                    normalized_evidence.append({
                        "evidence_type": ev_type,
                        "evidence_strength": ev_strength
                    })

                if not ev_valid or len(normalized_evidence) == 0:
                    continue

                # Sort evidence deterministically by evidence_type ASC, then evidence_strength ASC
                normalized_evidence.sort(key=lambda x: (x["evidence_type"], x["evidence_strength"]))

                tax_info = self.skills_by_id[skill_id]
                skill_name = tax_info["name"]
                category = tax_info["category"]

                student_categories.add(category)
                all_unique_skill_ids.add(skill_id)
                category_counts[category] = category_counts.get(category, 0) + 1
                total_skill_records += 1

                normalized_skills.append({
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "category": category,
                    "evidence": normalized_evidence
                })

            # Sort skills deterministically by skill_id ASC
            normalized_skills.sort(key=lambda x: x["skill_id"])
            sorted_categories = sorted(list(student_categories))

            normalized_students.append({
                "student_id": student_id,
                "profile_name": profile_name,
                "skill_count": len(normalized_skills),
                "categories_present": sorted_categories,
                "skills": normalized_skills
            })

        # Sort students deterministically by student_id ASC
        normalized_students.sort(key=lambda x: x["student_id"])

        artifact = {
            "metadata": {
                "phase": "7A",
                "pipeline": "student_skill_profile",
                "taxonomy_version": self.taxonomy_version,
                "total_students": len(normalized_students),
                "total_skill_records": total_skill_records,
                "total_unique_skills": len(all_unique_skill_ids),
                "category_counts": dict(sorted(category_counts.items())),
                "scope_note": "Synthetic student skill profiles representing current claimed/verified skills and evidence provenance without proficiency scores or gap evaluations."
            },
            "students": normalized_students,
            "errors": errors
        }
        return artifact

    def run_and_save(self, output_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
        out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
        artifact = self.process_profiles()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        return artifact, out_file
