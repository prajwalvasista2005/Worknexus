import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict

DEFAULT_DEMAND_PATH = Path(__file__).resolve().parent.parent / "demand" / "demand_analysis.json"
DEFAULT_COURSES_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_courses.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "skill_gap_analysis.json"

class SkillGapAnalyzer:
    """
    Deterministic skill gap analyzer comparing course curriculum coverage
    against observed industry skill demand from Phase 3.
    """

    def __init__(
        self,
        demand_artifact_path: Optional[Path] = None,
        courses_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.demand_path = demand_artifact_path or DEFAULT_DEMAND_PATH
        self.courses_path = courses_path or DEFAULT_COURSES_PATH
        self.taxonomy_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.demand_path.exists():
            raise FileNotFoundError(f"Missing demand artifact at {self.demand_path}")
        if not self.courses_path.exists():
            raise FileNotFoundError(f"Missing courses dataset at {self.courses_path}")
        if not self.taxonomy_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.taxonomy_path}")

        with open(self.demand_path, "r", encoding="utf-8") as f:
            self.demand_data: Dict[str, Any] = json.load(f)

        with open(self.courses_path, "r", encoding="utf-8") as f:
            self.courses_data: List[Dict[str, Any]] = json.load(f)

        with open(self.taxonomy_path, "r", encoding="utf-8") as f:
            self.taxonomy_data: List[Dict[str, Any]] = json.load(f)

        self._index_taxonomy_and_demand()

    def _index_taxonomy_and_demand(self):
        self.skills_by_id: Dict[str, Dict[str, Any]] = {}
        for s in self.taxonomy_data:
            s_id = s["id"]
            self.skills_by_id[s_id] = {
                "id": s_id,
                "name": s["name"],
                "category": s["category"]
            }
        self.valid_categories = sorted(list({s["category"] for s in self.taxonomy_data}))

        # Index demand skills
        self.demand_skills_map: Dict[str, Dict[str, Any]] = {}
        for s in self.demand_data.get("skills", []):
            s_id = s["skill_id"]
            if s_id not in self.skills_by_id:
                raise ValueError(f"Demand artifact skill '{s_id}' not found in taxonomy.")
            self.demand_skills_map[s_id] = s

        self.observed_demand_skill_ids = sorted(list(self.demand_skills_map.keys()))
        self.total_observed_demand = sum(s["job_count"] for s in self.demand_skills_map.values())

    def analyze(self) -> Dict[str, Any]:
        total_courses = len(self.courses_data)
        if total_courses == 0:
            raise ValueError("Courses dataset contains 0 courses.")

        courses_output: List[Dict[str, Any]] = []
        unmapped_course_skills: List[Dict[str, Any]] = []
        
        # Track global skill coverage: skill_id -> list of course_ids covering it
        global_skill_course_coverage: Dict[str, Set[Any]] = defaultdict(set)

        for course in self.courses_data:
            course_id = course.get("course_id")
            course_name = course.get("name") or course.get("course_name") or f"Course {course_id}"
            course_role = course.get("role") or ""
            raw_skill_ids = course.get("skill_ids") or course.get("skills") or []
            coverage_meta = course.get("coverage", {})

            valid_course_skills: List[str] = []
            for raw_sid in raw_skill_ids:
                if raw_sid in self.skills_by_id:
                    valid_course_skills.append(raw_sid)
                else:
                    unmapped_course_skills.append({
                        "course_id": course_id,
                        "course_name": course_name,
                        "unmapped_skill": raw_sid
                    })

            course_skill_set = set(valid_course_skills)
            demanded_skill_set = set(self.observed_demand_skill_ids)

            covered_ids = course_skill_set & demanded_skill_set
            missing_ids = demanded_skill_set - course_skill_set
            out_of_demand_ids = course_skill_set - demanded_skill_set

            # Update global tracker
            for sid in covered_ids:
                global_skill_course_coverage[sid].add(course_id)

            # 1. Covered Skills List
            covered_skills_list: List[Dict[str, Any]] = []
            for sid in sorted(list(covered_ids)):
                d_meta = self.demand_skills_map[sid]
                entry = {
                    "skill_id": sid,
                    "skill_name": self.skills_by_id[sid]["name"],
                    "category": self.skills_by_id[sid]["category"],
                    "job_count": d_meta["job_count"],
                    "demand_percentage": d_meta["demand_percentage"],
                    "source_coverage_count": d_meta["source_coverage_count"],
                    "sources_present": d_meta.get("sources_present", [])
                }
                if sid in coverage_meta:
                    entry["course_coverage_percentage"] = coverage_meta[sid]
                covered_skills_list.append(entry)

            # Sort covered skills by skill_id ASC
            covered_skills_list.sort(key=lambda x: x["skill_id"])

            # 2. Missing Skills List
            missing_skills_list: List[Dict[str, Any]] = []
            for sid in missing_ids:
                d_meta = self.demand_skills_map[sid]
                missing_skills_list.append({
                    "skill_id": sid,
                    "skill_name": self.skills_by_id[sid]["name"],
                    "category": self.skills_by_id[sid]["category"],
                    "job_count": d_meta["job_count"],
                    "demand_percentage": d_meta["demand_percentage"],
                    "source_coverage_count": d_meta["source_coverage_count"],
                    "sources_present": d_meta.get("sources_present", [])
                })

            # Sort missing skills by job_count DESC, skill_id ASC
            missing_skills_list.sort(key=lambda x: (-x["job_count"], x["skill_id"]))

            # 3. Course Skills Outside Observed Demand
            out_of_demand_list: List[Dict[str, Any]] = []
            for sid in sorted(list(out_of_demand_ids)):
                entry = {
                    "skill_id": sid,
                    "skill_name": self.skills_by_id[sid]["name"],
                    "category": self.skills_by_id[sid]["category"]
                }
                if sid in coverage_meta:
                    entry["course_coverage_percentage"] = coverage_meta[sid]
                out_of_demand_list.append(entry)

            out_of_demand_list.sort(key=lambda x: x["skill_id"])

            # 4. Aggregated Course Demand Metrics
            covered_demand = sum(self.demand_skills_map[sid]["job_count"] for sid in covered_ids)
            missing_demand = sum(self.demand_skills_map[sid]["job_count"] for sid in missing_ids)

            demand_cov_ratio = (
                covered_demand / self.total_observed_demand
                if self.total_observed_demand > 0
                else 0.0
            )

            skill_cov_ratio = (
                len(covered_ids) / len(demanded_skill_set)
                if len(demanded_skill_set) > 0
                else 0.0
            )

            # 5. Category-Level Analysis for Course
            category_analysis_list: List[Dict[str, Any]] = []
            for cat in self.valid_categories:
                cat_demanded_ids = {
                    sid for sid in demanded_skill_set
                    if self.skills_by_id[sid]["category"] == cat
                }
                if not cat_demanded_ids:
                    continue

                cat_covered_ids = cat_demanded_ids & course_skill_set
                cat_missing_ids = cat_demanded_ids - course_skill_set

                cat_total_demand = sum(self.demand_skills_map[sid]["job_count"] for sid in cat_demanded_ids)
                cat_cov_demand = sum(self.demand_skills_map[sid]["job_count"] for sid in cat_covered_ids)
                cat_miss_demand = cat_total_demand - cat_cov_demand

                cat_demand_cov_ratio = (
                    cat_cov_demand / cat_total_demand
                    if cat_total_demand > 0
                    else 0.0
                )

                cat_skill_cov_ratio = (
                    len(cat_covered_ids) / len(cat_demanded_ids)
                    if len(cat_demanded_ids) > 0
                    else 0.0
                )

                category_analysis_list.append({
                    "category": cat,
                    "demanded_skill_count": len(cat_demanded_ids),
                    "covered_skill_count": len(cat_covered_ids),
                    "missing_skill_count": len(cat_missing_ids),
                    "category_total_demand": cat_total_demand,
                    "category_covered_demand": cat_cov_demand,
                    "category_missing_demand": cat_miss_demand,
                    "category_demand_coverage_ratio": round(cat_demand_cov_ratio, 4),
                    "category_skill_coverage_ratio": round(cat_skill_cov_ratio, 4)
                })

            category_analysis_list.sort(key=lambda x: x["category"])

            courses_output.append({
                "course_id": course_id,
                "course_name": course_name,
                "role": course_role,
                "course_skills": sorted(valid_course_skills),
                "observed_demand_skill_count": len(demanded_skill_set),
                "covered_demand_skill_count": len(covered_ids),
                "missing_demand_skill_count": len(missing_ids),
                "skill_coverage_ratio": round(skill_cov_ratio, 4),
                "total_observed_demand": self.total_observed_demand,
                "covered_demand": covered_demand,
                "missing_demand": missing_demand,
                "demand_coverage_ratio": round(demand_cov_ratio, 4),
                "covered_skills": covered_skills_list,
                "missing_skills": missing_skills_list,
                "course_skills_without_observed_demand": out_of_demand_list,
                "category_analysis": category_analysis_list
            })

        # Deterministic sort: course_id ASC
        courses_output.sort(key=lambda x: x["course_id"])

        # 6. Global Skill Gap Summary
        global_skill_gap_list: List[Dict[str, Any]] = []
        for sid in self.observed_demand_skill_ids:
            d_meta = self.demand_skills_map[sid]
            courses_cov_count = len(global_skill_course_coverage.get(sid, set()))
            courses_miss_count = total_courses - courses_cov_count
            cov_ratio = courses_cov_count / total_courses if total_courses > 0 else 0.0

            global_skill_gap_list.append({
                "skill_id": sid,
                "skill_name": self.skills_by_id[sid]["name"],
                "category": self.skills_by_id[sid]["category"],
                "job_count": d_meta["job_count"],
                "demand_percentage": d_meta["demand_percentage"],
                "source_coverage_count": d_meta["source_coverage_count"],
                "courses_covering": courses_cov_count,
                "courses_missing": courses_miss_count,
                "course_coverage_ratio": round(cov_ratio, 4)
            })

        # Sort global skill gap: job_count DESC, skill_id ASC
        global_skill_gap_list.sort(key=lambda x: (-x["job_count"], x["skill_id"]))

        artifact = {
            "metadata": {
                "phase": "4",
                "pipeline": "skill_gap_analysis",
                "demand_input": str(self.demand_path.as_posix()),
                "course_input": str(self.courses_path.as_posix()),
                "taxonomy_version": self.demand_data.get("metadata", {}).get("taxonomy_version", "1"),
                "total_courses": total_courses,
                "observed_demand_skills": len(self.observed_demand_skill_ids),
                "total_observed_demand": self.total_observed_demand,
                "scope_note": "Observed curriculum skill gap metrics calculated against Phase 3 industry demand artifact."
            },
            "courses": courses_output,
            "global_skill_gap": global_skill_gap_list,
            "unmapped_course_skills": unmapped_course_skills
        }
        return artifact

    def run_and_save(self, output_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
        out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
        artifact = self.analyze()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        return artifact, out_file
