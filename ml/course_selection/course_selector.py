import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

DEFAULT_RECOMMENDATION_PATH = Path(__file__).resolve().parent.parent / "personalized" / "student_skill_recommendations.json"
DEFAULT_MAPPING_PATH = Path(__file__).resolve().parent.parent / "course_mapping" / "personalized_course_mapping.json"
DEFAULT_COURSE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_courses.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "course_selection_candidates.json"

class CourseCandidateSelector:
    """
    Deterministic Course Selection Candidates Engine.
    Identifies candidate courses that collectively address the student's personalized
    skill recommendations from Phase 7C and Phase 7D without ranking, fit scores,
    or learning path sequencing.
    """

    def __init__(
        self,
        recommendation_path: Optional[Path] = None,
        mapping_path: Optional[Path] = None,
        course_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.rec_path = recommendation_path or DEFAULT_RECOMMENDATION_PATH
        self.map_path = mapping_path or DEFAULT_MAPPING_PATH
        self.course_path = course_path or DEFAULT_COURSE_PATH
        self.tax_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.rec_path.exists():
            raise FileNotFoundError(f"Missing Phase 7C personalized recommendations artifact at {self.rec_path}")
        if not self.map_path.exists():
            raise FileNotFoundError(f"Missing Phase 7D course mapping artifact at {self.map_path}")
        if not self.course_path.exists():
            raise FileNotFoundError(f"Missing course catalog dataset at {self.course_path}")
        if not self.tax_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.tax_path}")

        with open(self.rec_path, "r", encoding="utf-8") as f:
            self.rec_data: Dict[str, Any] = json.load(f)

        with open(self.map_path, "r", encoding="utf-8") as f:
            self.map_data: Dict[str, Any] = json.load(f)

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

        # Index courses
        self.courses_by_id: Dict[int, Dict[str, Any]] = {}
        self.valid_course_ids: Set[int] = set()
        for c in self.course_data:
            c_id = c["course_id"]
            self.valid_course_ids.add(c_id)
            self.courses_by_id[c_id] = {
                "course_id": c_id,
                "course_name": c["name"],
                "role": c.get("role", ""),
                "skill_ids": set(c.get("skill_ids", []))
            }

        # Index Phase 7D mappings by student_id -> skill_id -> list of matching courses
        self.student_skill_mapping: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for stu in self.map_data.get("students", []):
            s_id = stu.get("student_id")
            self.student_skill_mapping[s_id] = {}
            for item in stu.get("skill_course_mapping", []):
                sk_id = item.get("skill_id")
                self.student_skill_mapping[s_id][sk_id] = item.get("matching_courses", [])

    def select_candidates(self) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        students_output: List[Dict[str, Any]] = []

        total_personalized_skills = 0
        total_uncovered_personalized_skills = 0
        global_candidate_courses_set: Set[int] = set()

        # Track global course usage: course_id -> list of student_ids
        course_usage_map: Dict[int, List[str]] = {c_id: [] for c_id in sorted(self.valid_course_ids)}

        for stu in self.rec_data.get("students", []):
            stu_id = stu.get("student_id")
            role_info = stu.get("role", {})
            role_id = role_info.get("role_id")
            role_name = role_info.get("role_name", "")

            # Filter ONLY personalized recommended skills
            all_recs = stu.get("skill_recommendations", [])
            recommended_recs = [
                r for r in all_recs
                if r.get("personalized_status") == "recommended"
            ]

            # Sort recommended skills alphabetically by skill_id ASC
            recommended_recs.sort(key=lambda r: r["skill_id"])
            personalized_skill_ids = [r["skill_id"] for r in recommended_recs]
            total_personalized_skills += len(personalized_skill_ids)

            # Map student's candidate courses
            # A course is a candidate if it covers at least 1 personalized skill for this student
            candidate_courses_dict: Dict[int, Dict[str, Any]] = {}
            covered_skill_ids_for_student: Set[str] = set()

            for sk_id in personalized_skill_ids:
                if sk_id not in self.valid_skill_ids:
                    errors.append({
                        "type": "UNKNOWN_SKILL_ID",
                        "student_id": stu_id,
                        "skill_id": sk_id,
                        "message": f"Skill ID '{sk_id}' not found in canonical taxonomy."
                    })
                    continue

                # Find which courses teach this skill from authoritative course catalog / 7D mapping
                matching_courses = self.student_skill_mapping.get(stu_id, {}).get(sk_id, [])
                if not matching_courses:
                    # Fallback verification against course catalog
                    for c_id, c_info in self.courses_by_id.items():
                        if sk_id in c_info["skill_ids"]:
                            matching_courses.append({
                                "course_id": c_id,
                                "course_name": c_info["course_name"]
                            })

                if matching_courses:
                    covered_skill_ids_for_student.add(sk_id)
                    for mc in matching_courses:
                        c_id = mc["course_id"]
                        c_name = mc.get("course_name") or self.courses_by_id[c_id]["course_name"]

                        if c_id not in candidate_courses_dict:
                            candidate_courses_dict[c_id] = {
                                "course_id": c_id,
                                "course_name": c_name,
                                "covered_personalized_skill_ids": set()
                            }
                        candidate_courses_dict[c_id]["covered_personalized_skill_ids"].add(sk_id)

            # Build sorted candidate courses list for this student
            student_candidate_courses: List[Dict[str, Any]] = []
            for c_id in sorted(candidate_courses_dict.keys()):
                c_data = candidate_courses_dict[c_id]
                sorted_covered_skills = sorted(list(c_data["covered_personalized_skill_ids"]))
                student_candidate_courses.append({
                    "course_id": c_id,
                    "course_name": c_data["course_name"],
                    "covered_personalized_skill_ids": sorted_covered_skills,
                    "covered_personalized_skill_count": len(sorted_covered_skills)
                })
                # Register global usage
                course_usage_map[c_id].append(stu_id)
                global_candidate_courses_set.add(c_id)

            # Identify uncovered personalized skills
            uncovered_skills = sorted([
                sk_id for sk_id in personalized_skill_ids
                if sk_id not in covered_skill_ids_for_student
            ])
            total_uncovered_personalized_skills += len(uncovered_skills)

            summary = {
                "total_personalized_skills": len(personalized_skill_ids),
                "candidate_course_count": len(student_candidate_courses),
                "covered_personalized_skill_count": len(covered_skill_ids_for_student),
                "uncovered_personalized_skill_count": len(uncovered_skills)
            }

            students_output.append({
                "student_id": stu_id,
                "role": {
                    "role_id": role_id,
                    "role_name": role_name
                },
                "personalized_skill_ids": personalized_skill_ids,
                "candidate_courses": student_candidate_courses,
                "uncovered_personalized_skills": uncovered_skills,
                "summary": summary
            })

        # Sort students by student_id ASC
        students_output.sort(key=lambda s: s["student_id"])

        # Build global course usage: only include courses that are candidate for >= 1 student, sorted course_id ASC
        global_course_usage: List[Dict[str, Any]] = []
        for c_id in sorted(self.valid_course_ids):
            student_list = sorted(course_usage_map[c_id])
            if student_list:
                global_course_usage.append({
                    "course_id": c_id,
                    "course_name": self.courses_by_id[c_id]["course_name"],
                    "candidate_for_students": student_list
                })

        output = {
            "metadata": {
                "phase": "7E",
                "pipeline": "course_selection_candidates",
                "personalized_recommendation_input": str(self.rec_path).replace("\\", "/"),
                "course_mapping_input": str(self.map_path).replace("\\", "/"),
                "course_catalog_input": str(self.course_path).replace("\\", "/"),
                "taxonomy_input": str(self.tax_path).replace("\\", "/"),
                "taxonomy_version": self.taxonomy_version,
                "total_students": len(students_output),
                "total_personalized_skills": total_personalized_skills,
                "total_candidate_courses": len(global_candidate_courses_set),
                "total_uncovered_personalized_skills": total_uncovered_personalized_skills,
                "scope_note": "Deterministic identification of candidate courses covering personalized skill recommendations without ranking, scoring, or learning path generation."
            },
            "students": students_output,
            "global_course_usage": global_course_usage,
            "errors": errors
        }

        return output

def select_course_candidates(
    recommendation_path: Optional[Path] = None,
    mapping_path: Optional[Path] = None,
    course_path: Optional[Path] = None,
    taxonomy_path: Optional[Path] = None,
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    selector = CourseCandidateSelector(
        recommendation_path=recommendation_path,
        mapping_path=mapping_path,
        course_path=course_path,
        taxonomy_path=taxonomy_path
    )
    result = selector.select_candidates()

    out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result
