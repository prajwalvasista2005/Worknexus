import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

DEFAULT_ROLE_CONTEXT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_role_contexts.json"
DEFAULT_RECOMMENDATION_PATH = Path(__file__).resolve().parent.parent / "recommend" / "skill_recommendations.json"
DEFAULT_EVIDENCE_PATH = Path(__file__).resolve().parent.parent / "evidence" / "multi_signal_evidence.json"
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"
DEFAULT_OUTPUT_ARTIFACT_PATH = Path(__file__).resolve().parent / "contextual_recommendations.json"

class ContextAwareRecommendationEngine:
    """
    Deterministic context-aware skill recommendation engine.
    Filters and grounds Phase 6A generic skill recommendations within
    explicit target role/job contexts without synthesizing arbitrary role-fit scores.
    """

    def __init__(
        self,
        role_context_path: Optional[Path] = None,
        recommendation_path: Optional[Path] = None,
        evidence_path: Optional[Path] = None,
        taxonomy_path: Optional[Path] = None
    ):
        self.role_path = role_context_path or DEFAULT_ROLE_CONTEXT_PATH
        self.rec_path = recommendation_path or DEFAULT_RECOMMENDATION_PATH
        self.ev_path = evidence_path or DEFAULT_EVIDENCE_PATH
        self.tax_path = taxonomy_path or DEFAULT_TAXONOMY_PATH

        if not self.role_path.exists():
            raise FileNotFoundError(f"Missing role contexts dataset at {self.role_path}")
        if not self.rec_path.exists():
            raise FileNotFoundError(f"Missing Phase 6A recommendation artifact at {self.rec_path}")
        if not self.ev_path.exists():
            raise FileNotFoundError(f"Missing Phase 5B evidence artifact at {self.ev_path}")
        if not self.tax_path.exists():
            raise FileNotFoundError(f"Missing taxonomy dataset at {self.tax_path}")

        with open(self.role_path, "r", encoding="utf-8") as f:
            self.role_data: List[Dict[str, Any]] = json.load(f)

        with open(self.rec_path, "r", encoding="utf-8") as f:
            self.rec_data: Dict[str, Any] = json.load(f)

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

        # Index Phase 6A recommendations
        self.rec_skills_map: Dict[str, Dict[str, Any]] = {}
        for r in self.rec_data.get("recommendations", []):
            s_id = r["skill_id"]
            self.rec_skills_map[s_id] = r

        # Index Phase 5B evidence
        self.ev_skills_map: Dict[str, Dict[str, Any]] = {}
        for e in self.ev_data.get("skills", []):
            s_id = e["skill_id"]
            self.ev_skills_map[s_id] = e

    def recommend(self) -> Dict[str, Any]:
        total_roles = len(self.role_data)
        roles_output: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        total_mappings_count = 0
        total_contextual_rec_count = 0
        total_context_records_count = 0

        seen_role_ids: Set[str] = set()

        for role in self.role_data:
            role_id = role.get("role_id")
            role_name = role.get("role_name") or f"Role {role_id}"
            target_skill_ids = role.get("target_skill_ids", [])

            if not role_id or role_id in seen_role_ids:
                errors.append({
                    "role_id": role_id,
                    "error": f"Duplicate or missing role_id: '{role_id}'"
                })
                continue
            seen_role_ids.add(role_id)

            if len(target_skill_ids) != len(set(target_skill_ids)):
                errors.append({
                    "role_id": role_id,
                    "error": f"Duplicate target_skill_ids in role {role_id}"
                })

            role_skill_context: List[Dict[str, Any]] = []
            contextual_recommendations: List[Dict[str, Any]] = []

            rec_target_count = 0
            not_rec_target_count = 0
            unavail_target_count = 0

            for s_id in sorted(list(set(target_skill_ids))):
                total_mappings_count += 1
                total_context_records_count += 1

                if s_id not in self.valid_skill_ids:
                    errors.append({
                        "role_id": role_id,
                        "skill_id": s_id,
                        "error": f"Target skill '{s_id}' not found in canonical taxonomy."
                    })
                    continue

                s_name = self.skills_by_id[s_id]["name"]
                s_cat = self.skills_by_id[s_id]["category"]

                # Check if skill exists in Phase 6A recommendations
                if s_id in self.rec_skills_map:
                    rec_entry = self.rec_skills_map[s_id]
                    gen_status = rec_entry.get("recommendation", {}).get("status", "not_recommended")
                    gen_reasons = rec_entry.get("recommendation", {}).get("reason_ids", [])
                    evidence_block = rec_entry.get("evidence", {})
                    course_ctx = rec_entry.get("course_context", {})

                    if gen_status == "recommended":
                        rec_target_count += 1
                        total_contextual_rec_count += 1
                        context_reason = {
                            "reason_id": "explicit_role_skill_mapping",
                            "source": str(self.role_path.name)
                        }

                        # Add to contextual recommendations
                        contextual_recommendations.append({
                            "role_id": role_id,
                            "role_name": role_name,
                            "skill_id": s_id,
                            "skill_name": s_name,
                            "category": s_cat,
                            "role_relevant": True,
                            "generic_recommendation": {
                                "status": "recommended",
                                "reason_ids": gen_reasons
                            },
                            "context_reason": context_reason,
                            "evidence": evidence_block,
                            "course_context": course_ctx
                        })
                    else:
                        not_rec_target_count += 1
                        context_reason = {
                            "reason_id": "role_mapping_without_generic_recommendation",
                            "source": str(self.role_path.name)
                        }
                else:
                    # Skill not in Phase 6A universe (e.g. taxonomy skill not in 5B evidence)
                    gen_status = "not_available"
                    unavail_target_count += 1
                    context_reason = {
                        "reason_id": "role_skill_not_in_phase6a_universe",
                        "source": str(self.role_path.name)
                    }

                role_skill_context.append({
                    "skill_id": s_id,
                    "skill_name": s_name,
                    "category": s_cat,
                    "role_relevant": True,
                    "generic_recommendation_status": gen_status,
                    "context_reason": context_reason
                })

            # Sort role_skill_context & contextual_recommendations by skill_id ASC
            role_skill_context.sort(key=lambda x: x["skill_id"])
            contextual_recommendations.sort(key=lambda x: x["skill_id"])

            roles_output.append({
                "role_id": role_id,
                "role_name": role_name,
                "target_skill_count": len(set(target_skill_ids)),
                "recommended_target_skill_count": rec_target_count,
                "not_recommended_target_skill_count": not_rec_target_count,
                "unavailable_target_skill_count": unavail_target_count,
                "role_skill_context": role_skill_context,
                "contextual_recommendations": contextual_recommendations
            })

        # Sort roles by role_id ASC
        roles_output.sort(key=lambda x: x["role_id"])

        artifact = {
            "metadata": {
                "phase": "6B",
                "pipeline": "context_aware_skill_recommendation",
                "role_context_input": str(self.role_path.as_posix()),
                "recommendation_input": str(self.rec_path.as_posix()),
                "evidence_input": str(self.ev_path.as_posix()),
                "taxonomy_version": self.taxonomy_version,
                "total_roles": total_roles,
                "total_role_skill_mappings": total_mappings_count,
                "total_contextual_recommendations": total_contextual_rec_count,
                "total_role_skill_context_records": total_context_records_count,
                "scope_note": "Context-aware skill recommendations derived from explicit synthetic role mappings and Phase 6A generic recommendation evidence."
            },
            "roles": roles_output,
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
