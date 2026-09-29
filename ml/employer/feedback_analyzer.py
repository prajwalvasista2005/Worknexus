import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict

from ml.extract import extract_skills

DEFAULT_FEEDBACK_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_employer_feedback.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "employer_feedback_analysis.json"

class EmployerFeedbackAnalyzer:
    """
    Deterministic employer feedback intelligence analyzer that processes
    structured employer feedback, extracts canonical skills using the frozen
    extract_skills engine, and computes explainable trust-weighted employer signals.
    """

    def __init__(
        self,
        feedback_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.feedback_path = feedback_path or DEFAULT_FEEDBACK_PATH
        self.taxonomy_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.feedback_path.exists():
            raise FileNotFoundError(f"Missing employer feedback dataset at {self.feedback_path}")
        if not self.taxonomy_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.taxonomy_path}")

        with open(self.feedback_path, "r", encoding="utf-8") as f:
            self.feedback_data: List[Dict[str, Any]] = json.load(f)

        with open(self.taxonomy_path, "r", encoding="utf-8") as f:
            self.taxonomy_data: List[Dict[str, Any]] = json.load(f)

        self._index_taxonomy()

    def _index_taxonomy(self):
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

    def analyze(self) -> Dict[str, Any]:
        total_records = len(self.feedback_data)
        processed_records: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        # Aggregation structures:
        # skill_id -> list of dicts: {"employer_id": ..., "feedback_id": ..., "weighted_signal": ...}
        skill_signal_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # course_id -> dict with feedback_count, employers set, skill_records dict
        course_signal_records: Dict[Any, Dict[str, Any]] = defaultdict(lambda: {
            "feedback_count": 0,
            "employers": set(),
            "skill_records": defaultdict(list)
        })

        all_employers: Set[Any] = set()
        all_courses: Set[Any] = set()
        records_with_skills_count = 0
        zero_skill_records_count = 0

        for idx, item in enumerate(self.feedback_data, 1):
            feedback_id = str(item.get("feedback_id") or f"fb_{idx}")
            employer_id = item.get("employer_id")
            course_id = item.get("course_id")

            # Trust weight handling
            raw_trust = item.get("trust_weight")
            if raw_trust is not None:
                try:
                    trust_weight = float(raw_trust)
                except (ValueError, TypeError):
                    errors.append({
                        "feedback_id": feedback_id,
                        "error": f"Invalid trust_weight value: {raw_trust}"
                    })
                    continue
            else:
                trust_weight = 1.0  # Default neutral trust if not specified

            # Text selection: comment or feedback_text
            text = item.get("feedback_text") or item.get("comment") or ""
            if not text:
                # Still process as empty/zero-skill record
                text = ""

            all_employers.add(employer_id)
            if course_id is not None:
                all_courses.add(course_id)
                course_signal_records[course_id]["feedback_count"] += 1
                course_signal_records[course_id]["employers"].add(employer_id)

            # Skill extraction using the frozen extract_skills contract
            try:
                raw_extracted = extract_skills(text)
            except Exception as e:
                errors.append({
                    "feedback_id": feedback_id,
                    "error": f"Extraction failure: {str(e)}"
                })
                continue

            # Validate against taxonomy & collapse duplicate skill mentions within one feedback
            validated_skills: List[Dict[str, Any]] = []
            seen_skills_in_fb: Set[str] = set()

            for s in raw_extracted:
                s_id = s["skill_id"]
                conf = float(s["confidence_score"])

                if s_id not in self.valid_skill_ids:
                    errors.append({
                        "feedback_id": feedback_id,
                        "error": f"Extracted skill '{s_id}' not found in taxonomy."
                    })
                    continue

                if s_id not in seen_skills_in_fb:
                    seen_skills_in_fb.add(s_id)
                    weighted_sig = conf * trust_weight

                    validated_skills.append({
                        "skill_id": s_id,
                        "skill_name": self.skills_by_id[s_id]["name"],
                        "category": self.skills_by_id[s_id]["category"],
                        "confidence_score": conf,
                        "trust_weight": trust_weight,
                        "weighted_signal": weighted_sig
                    })

                    signal_entry = {
                        "feedback_id": feedback_id,
                        "employer_id": employer_id,
                        "course_id": course_id,
                        "confidence_score": conf,
                        "trust_weight": trust_weight,
                        "weighted_signal": weighted_sig
                    }
                    skill_signal_records[s_id].append(signal_entry)

                    if course_id is not None:
                        course_signal_records[course_id]["skill_records"][s_id].append(signal_entry)

            # Sort skills inside each feedback record deterministically by skill_id ASC
            validated_skills.sort(key=lambda x: x["skill_id"])

            if validated_skills:
                records_with_skills_count += 1
            else:
                zero_skill_records_count += 1

            rec_output: Dict[str, Any] = {
                "feedback_id": feedback_id,
                "employer_id": employer_id,
                "trust_weight": trust_weight,
                "skills": validated_skills
            }
            if course_id is not None:
                rec_output["course_id"] = course_id

            processed_records.append(rec_output)

        # Deterministic sort for feedback_records by feedback_id ASC
        processed_records.sort(key=lambda x: str(x["feedback_id"]))

        # 1. Global Skill Signals Aggregation
        skill_signals_list: List[Dict[str, Any]] = []
        for s_id in sorted(list(skill_signal_records.keys())):
            signals = skill_signal_records[s_id]
            fb_count = len(signals)
            unique_emp_count = len({sig["employer_id"] for sig in signals})
            sig_sum = sum(sig["weighted_signal"] for sig in signals)
            avg_sig = sig_sum / fb_count if fb_count > 0 else 0.0
            max_sig = max(sig["weighted_signal"] for sig in signals) if signals else 0.0

            skill_signals_list.append({
                "skill_id": s_id,
                "skill_name": self.skills_by_id[s_id]["name"],
                "category": self.skills_by_id[s_id]["category"],
                "feedback_count": fb_count,
                "unique_employer_count": unique_emp_count,
                "weighted_signal_sum": round(sig_sum, 6),
                "average_weighted_signal": round(avg_sig, 6),
                "max_weighted_signal": round(max_sig, 6)
            })

        # Sort skill_signals by skill_id ASC
        skill_signals_list.sort(key=lambda x: x["skill_id"])

        # 2. Course Signals Aggregation
        course_signals_list: List[Dict[str, Any]] = []
        for c_id in sorted(list(course_signal_records.keys()), key=lambda x: (isinstance(x, str), x)):
            c_data = course_signal_records[c_id]
            c_skills_dict = c_data["skill_records"]

            c_skill_summaries: List[Dict[str, Any]] = []
            for s_id in sorted(list(c_skills_dict.keys())):
                sigs = c_skills_dict[s_id]
                c_fb_count = len(sigs)
                c_emp_count = len({sig["employer_id"] for sig in sigs})
                c_sum = sum(sig["weighted_signal"] for sig in sigs)
                c_avg = c_sum / c_fb_count if c_fb_count > 0 else 0.0

                c_skill_summaries.append({
                    "skill_id": s_id,
                    "skill_name": self.skills_by_id[s_id]["name"],
                    "category": self.skills_by_id[s_id]["category"],
                    "feedback_count": c_fb_count,
                    "unique_employer_count": c_emp_count,
                    "weighted_signal_sum": round(c_sum, 6),
                    "average_weighted_signal": round(c_avg, 6)
                })

            c_skill_summaries.sort(key=lambda x: x["skill_id"])

            course_signals_list.append({
                "course_id": c_id,
                "feedback_count": c_data["feedback_count"],
                "employer_count": len(c_data["employers"]),
                "skills_mentioned_count": len(c_skill_summaries),
                "skills_mentioned": [s["skill_id"] for s in c_skill_summaries],
                "skills": c_skill_summaries
            })

        # Sort course_signals by course_id ASC
        course_signals_list.sort(key=lambda x: x["course_id"])

        artifact = {
            "metadata": {
                "phase": "5A",
                "pipeline": "employer_feedback_intelligence",
                "input_file": str(self.feedback_path.as_posix()),
                "taxonomy_version": self.taxonomy_version,
                "total_feedback_records": total_records,
                "processed_feedback_records": len(processed_records),
                "failed_feedback_records": len(errors),
                "feedback_records_with_skills": records_with_skills_count,
                "zero_skill_feedback_records": zero_skill_records_count,
                "unique_employers": len(all_employers),
                "unique_courses": len(all_courses),
                "unique_skills_detected": len(skill_signals_list),
                "scope_note": "Observed employer validation signals computed strictly from feedback comments and trust weights."
            },
            "feedback_records": processed_records,
            "skill_signals": skill_signals_list,
            "course_signals": course_signals_list,
            "errors": errors
        }
        return artifact

    def run_and_save(self, output_path: Optional[Path] = None) -> Tuple[Dict[str, Any], Path]:
        out_file = output_path or DEFAULT_OUTPUT_ARTIFACT_PATH
        artifact = self.analyze()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        return artifact, out_file
