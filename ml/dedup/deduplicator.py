from typing import List, Dict, Any, Tuple, Optional
from ml.ingestion.schema import JobRecord, DeduplicatedJobRecord
from ml.ingestion.normalizer import (
    normalize_company,
    normalize_title,
    normalize_location,
    jaccard_similarity,
    tokenize_and_clean
)

# Key seniority and level tokens that indicate distinct vacancies
SENIORITY_TOKENS = {
    "senior", "sr", "junior", "jr", "lead", "principal", "staff",
    "associate", "director", "manager", "head", "intern", "trainee",
    "entry", "mid", "vp", "chief"
}

class ConservativeDeduplicator:
    """
    Conservative multi-signal duplicate detection for job postings.
    Ensures that different seniority levels, different companies, and distinct
    vacancies sharing common skills are strictly preserved as separate records.
    """

    def __init__(self, text_similarity_threshold: float = 0.75, title_similarity_threshold: float = 0.85):
        self.text_similarity_threshold = text_similarity_threshold
        self.title_similarity_threshold = title_similarity_threshold

    def are_potential_duplicates(
        self,
        rec_a: JobRecord,
        rec_b: JobRecord
    ) -> Tuple[bool, str]:
        """
        Evaluates whether two job postings represent the exact same vacancy.
        Returns (is_duplicate: bool, reason: str).
        """
        # Step 1: Company Comparison (Must match)
        comp_a = normalize_company(rec_a.company)
        comp_b = normalize_company(rec_b.company)

        if not comp_a or not comp_b:
            return False, "Missing company name in one or both records"

        if comp_a != comp_b and comp_a not in comp_b and comp_b not in comp_a:
            return False, f"Different companies: '{rec_a.company}' vs '{rec_b.company}'"

        # Step 2: Seniority / Level Distinction Check
        tokens_a = tokenize_and_clean(rec_a.title)
        tokens_b = tokenize_and_clean(rec_b.title)

        seniority_a = tokens_a & SENIORITY_TOKENS
        seniority_b = tokens_b & SENIORITY_TOKENS

        if seniority_a != seniority_b:
            return False, f"Different seniority levels: {seniority_a} vs {seniority_b} ('{rec_a.title}' vs '{rec_b.title}')"

        # Step 3: Title Comparison (Strict)
        title_a = normalize_title(rec_a.title, strip_seniority=False)
        title_b = normalize_title(rec_b.title, strip_seniority=False)

        if not title_a or not title_b:
            return False, "Missing job title in one or both records"

        title_sim = jaccard_similarity(title_a, title_b)
        if title_a != title_b and title_sim < self.title_similarity_threshold:
            return False, f"Different titles (similarity {title_sim:.2f}): '{rec_a.title}' vs '{rec_b.title}'"

        # Step 4: Location Compatibility
        loc_a = normalize_location(rec_a.location)
        loc_b = normalize_location(rec_b.location)

        if loc_a and loc_b and loc_a != "remote" and loc_b != "remote":
            if loc_a != loc_b and loc_a not in loc_b and loc_b not in loc_a:
                return False, f"Incompatible locations: '{rec_a.location}' vs '{rec_b.location}'"

        # Step 5: Description & Strong Evidence Check
        desc_a = rec_a.description or ""
        desc_b = rec_b.description or ""

        # Exact duplicate identical descriptions
        if desc_a and desc_b:
            if desc_a.strip().lower() == desc_b.strip().lower():
                return True, f"Identical job description and title at '{rec_a.company}'"

            desc_sim = jaccard_similarity(desc_a, desc_b)
            if desc_sim >= self.text_similarity_threshold:
                return True, f"High text similarity ({desc_sim:.2f}) and matching title at '{rec_a.company}'"
            else:
                return False, f"Descriptions differ significantly (similarity {desc_sim:.2f}) despite title match"

        # If descriptions are missing on both, only merge if title, company, and location match exactly
        if not desc_a and not desc_b:
            if title_a == title_b and loc_a == loc_b:
                return True, f"Exact match on title, company, and location with no descriptions"

        return False, "Insufficient corroborating evidence to confirm duplicate vacancy"

    def deduplicate(
        self,
        records: List[JobRecord]
    ) -> Tuple[List[DeduplicatedJobRecord], List[Dict[str, Any]]]:
        """
        Clusters and merges duplicate job postings while preserving full source provenance.
        Returns:
            (retained_records, duplicate_decision_log)
        """
        clusters: List[List[JobRecord]] = []
        decision_log: List[Dict[str, Any]] = []

        for record in records:
            matched_cluster = None

            for cluster in clusters:
                is_dup, reason = self.are_potential_duplicates(cluster[0], record)
                if is_dup:
                    matched_cluster = cluster
                    decision_log.append({
                        "decision": "MERGED",
                        "reason": reason,
                        "primary_source": cluster[0].source,
                        "primary_id": cluster[0].source_record_id,
                        "primary_title": cluster[0].title,
                        "primary_company": cluster[0].company,
                        "duplicate_source": record.source,
                        "duplicate_id": record.source_record_id,
                        "duplicate_title": record.title,
                        "duplicate_company": record.company
                    })
                    break

            if matched_cluster is not None:
                matched_cluster.append(record)
            else:
                clusters.append([record])

        deduped_records: List[DeduplicatedJobRecord] = []
        for cluster in clusters:
            primary = cluster[0]

            longest_desc = max(cluster, key=lambda r: len(r.description or "")).description
            best_title = max(cluster, key=lambda r: len(r.title or "")).title
            best_company = primary.company
            best_location = next((r.location for r in cluster if r.location), "")
            best_work_type = next((r.work_type for r in cluster if r.work_type), None)
            best_posted = next((r.posted_at for r in cluster if r.posted_at), None)

            all_skills: List[str] = []
            seen_skills = set()
            for r in cluster:
                for s in r.explicit_skills:
                    s_clean = s.strip()
                    if s_clean.lower() not in seen_skills:
                        seen_skills.add(s_clean.lower())
                        all_skills.append(s_clean)

            sources_list = [
                {"source": r.source, "source_record_id": r.source_record_id}
                for r in cluster
            ]

            deduped_records.append(
                DeduplicatedJobRecord(
                    canonical_id=f"{primary.source}_{primary.source_record_id}",
                    title=best_title,
                    description=longest_desc,
                    company=best_company,
                    location=best_location,
                    posted_at=best_posted,
                    work_type=best_work_type,
                    explicit_skills=all_skills,
                    source_records=sources_list,
                    raw_metadata={"cluster_size": len(cluster)}
                )
            )

        return deduped_records, decision_log
