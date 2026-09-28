import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

DEFAULT_RECOMMENDATION_PATH = Path(__file__).resolve().parent.parent / "personalized" / "student_skill_recommendations.json"
DEFAULT_COURSE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_courses.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "personalized_course_mapping.json"

class PersonalizedCourseMapper:
    """
    Deterministic Course / Learning-Path Mapping Engine.
    Maps Phase 7C personalized skill recommendations to existing catalog courses
    via exact canonical skill ID matching without course ranking, fit scores, or sequencing.
    """

    def __init__(
        self,
        recommendation_path: Optional[Path] = None,
        course_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.rec_path = recommendation_path or DEFAULT_RECOMMENDATION_PATH
        self.course_path = course_path or DEFAULT_COURSE_PATH
        self.tax_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.rec_path.exists():
            raise FileNotFoundError(f"Missing Phase 7C personalized recommendations artifact at {self.rec_path}")
        if not self.course_path.exists():
            raise FileNotFoundError(f"Missing course catalog dataset at {self.course_path}")
        if not self.tax_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.tax_path}")

        with open(self.rec_path, "r", encoding="utf-8") as f:
            self.rec_data: Dict[str, Any] = json.load(f)

        with open(self.course_path, "r", encoding="utf-8") as f:
            self.course_data: List[Dict[str, Any]] = json.load(f)

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

        # Index courses by skill_id
        self.courses_by_skill_id: Dict[str, List[Dict[str, Any]]] = {}
        self.valid_course_ids: Set[int] = set()

        for c in self.course_data:
            c_id = c["course_id"]
            c_name = c["name"]
            self.valid_course_ids.add(c_id)

            # Deduplicate skill IDs within course
            course_skill_ids = set(c.get("skill_ids", []))
            for s_id in course_skill_ids:
                if s_id not in self.courses_by_skill_id:
                    self.courses_by_skill_id[s_id] = []
                self.courses_by_skill_id[s_id].append({
                    "course_id": c_id,
                    "course_name": c_name
                })

        # Sort matching courses for each skill by course_id ASC
        for s_id in self.courses_by_skill_id:
            self.courses_by_skill_id[s_id].sort(key=lambda x: x["course_id"])

    def map_courses(self) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        students_output: List[Dict[str, Any]] = []

        total_personalized_skills = 0
        total_covered_skills = 0
        total_not_covered_skills = 0

        for stu in self.rec_data.get("students", []):
            stu_id = stu.get("student_id")
            role_info = stu.get("role", {})
            role_id = role_info.get("role_id")
            role_name = role_info.get("role_name", "")

            # Filter only personalized recommendations
            all_recs = stu.get("skill_recommendations", [])
            recommended_recs = [
                r for r in all_recs
                if r.get("personalized_status") == "recommended"
            ]

            # Sort recommended skills by skill_id ASC
            recommended_recs.sort(key=lambda x: x["skill_id"])

            skill_course_mapping: List[Dict[str, Any]] = []
            covered_count = 0
            not_covered_count = 0

            for rec in recommended_recs:
                s_id = rec["skill_id"]
                s_name = rec.get("skill_name") or self.skills_by_id.get(s_id, {}).get("name", s_id)
                category = rec.get("category") or self.skills_by_id.get(s_id, {}).get("category", "")

                total_personalized_skills += 1

                if s_id not in self.valid_skill_ids:
                    errors.append({
                        "student_id": stu_id,
                        "skill_id": s_id,
                        "error": f"Recommended skill '{s_id}' not found in canonical taxonomy."
                    })
                    continue

                matching_courses = self.courses_by_skill_id.get(s_id, [])
                if matching_courses:
                    cov_status = "covered"
                    covered_count += 1
                    total_covered_skills += 1
                else:
                    cov_status = "not_covered"
                    not_covered_count += 1
                    total_not_covered_skills += 1

                skill_course_mapping.append({
                    "skill_id": s_id,
                    "skill_name": s_name,
                    "category": category,
                    "coverage_status": cov_status,
                    "matching_courses": matching_courses
                })

            students_output.append({
                "student_id": stu_id,
                "role": {
                    "role_id": role_id,
                    "role_name": role_name
                },
                "summary": {
                    "total_personalized_skills": len(skill_course_mapping),
                    "covered_personalized_skills": covered_count,
                    "not_covered_personalized_skills": not_covered_count
                },
                "skill_course_mapping": skill_course_mapping
            })

        # Sort students by student_id ASC
        students_output.sort(key=lambda x: x["student_id"])

        # Build global skill-course mapping across all taxonomy skills
        global_mapping: List[Dict[str, Any]] = []
        for s_id in sorted(list(self.valid_skill_ids)):
            tax_entry = self.skills_by_id[s_id]
            matching_courses = self.courses_by_skill_id.get(s_id, [])
            cov_status = "covered" if matching_courses else "not_covered"

            global_mapping.append({
                "skill_id": s_id,
                "skill_name": tax_entry["name"],
                "category": tax_entry["category"],
                "coverage_status": cov_status,
                "courses_containing_skill": matching_courses
            })

        global_mapping.sort(key=lambda x: x["skill_id"])

        artifact = {
            "metadata": {
                "phase": "7D",
                "pipeline": "personalized_course_skill_mapping",
                "personalized_recommendation_input": str(self.rec_path.as_posix()),
                "course_input": str(self.course_path.as_posix()),
                "taxonomy_input": str(self.tax_path.as_posix()),
                "taxonomy_version": self.taxonomy_version,
                "total_students": len(students_output),
                "total_personalized_skills": total_personalized_skills,
                "total_covered_personalized_skills": total_covered_skills,
                "total_not_covered_personalized_skills": total_not_covered_skills,
                "scope_note": "Deterministic mapping of Phase 7C personalized skill recommendations to existing catalog courses without ranking, scoring, or learning path generation."
            },
            "students": students_output,
            "global_skill_course_mapping": global_mapping,
            "errors": errors
        }
        return artifact

    def run_and_save(self, output_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
        out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
        artifact = self.map_courses()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        return artifact, out_file
