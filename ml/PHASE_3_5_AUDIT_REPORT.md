# WorkNexus / SkillMesh — Phase 3.5 ML Pipeline Audit Report

**Date**: September 20, 2026  
**Auditor**: Antigravity Agent (ML Layer Engineer)  
**Branch**: `ml-dev`  
**Repository Scope**: `C:\Users\Nehal Jois\Documents\SIH\ml`  
**Data Reference Scope**: `C:\Users\Nehal Jois\Documents\SIH\Data`  
**Contract Reference**: `C:\Users\Nehal Jois\Documents\SIH\Pdfs\ML_BACKEND_CONTRACT.md`  

---

## 1. Executive Summary

This end-to-end audit independently verifies the entire ML processing pipeline across **Phase 0.5 (Ingestion & Deduplication)**, **Phase 1 (Skill Extraction & Normalization)**, **Phase 2 (Batch Artifact Processing)**, and **Phase 3 (Skill Demand Aggregation & Trends)**.

The pipeline was inspected for regressions, silent data loss, schema violations, provenance preservation, aggregation accuracy, taxonomy integrity, duplicate handling, determinism, data immutability, and architecture/phase boundaries.

### Core Pipeline Status Summary
| Metric | Phase 0.5 Baseline | Phase 1 Extractor | Phase 2 Batch Artifact | Phase 3 Demand Output | Independent Audit Verification |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Evaluated Jobs** | 295 | 295 | 295 | 295 | **295 (Match)** |
| **Jobs with $\ge 1$ Skill** | N/A | 211 | 211 | 211 | **211 (Match)** |
| **Zero-Skill Jobs Preserved**| N/A | 84 | 84 | 84 | **84 (Match)** |
| **Total Skill Mentions** | N/A | 536 | 536 | 536 | **536 (Match)** |
| **Active Canonical Skills** | N/A | 30 | 30 | 30 | **30 (Match)** |
| **Duplicate Jobs Removed** | 5 | N/A | N/A | N/A | **5 (Match)** |
| **Determinism Across 3 Runs**| 100% | 100% | 100% | 100% | **100% Byte-for-Byte Identical** |

**AUDIT CONCLUSION**: All cross-phase chains, schemas, and determinism constraints are 100% mathematically and architecturally validated.

---

## 2. Repository Structure Audit

All files within `ml/` were cataloged and inspected:
```text
ml/
├── data/
│   ├── skills.json                         (68 canonical skills, frozen)
│   ├── sample_courses.json                 (5 synthetic benchmark courses)
│   ├── sample_employer_feedback.json       (5 synthetic employer feedbacks)
│   └── sample_job_postings.json            (20 synthetic job postings)
├── dedup/
│   └── deduplicator.py                     (Conservative multi-signal deduplicator)
├── demand/
│   ├── __init__.py                         (DemandAggregator export)
│   ├── demand_aggregator.py                (Job-based demand, source, category, co-occurrence)
│   ├── demand_analysis.json                (Phase 3 output demand artifact)
│   ├── run_demand_analysis.py              (CLI runner for demand generation)
│   └── test_demand_aggregator.py           (12-point unit test suite)
├── extract/
│   ├── __init__.py                         (extract_skills entrypoint)
│   ├── extractor.py                        (Boundary-safe regex + conservative fuzzy extractor)
│   ├── batch_extractor.py                  (Phase 2 batch processor)
│   ├── extracted_job_skills.json           (Phase 2 batch output artifact)
│   ├── test_extractor.py                   (Phase 1 unit and false-positive regression suite)
│   ├── test_batch_extractor.py             (Phase 2 unit test suite)
│   ├── run_phase1_validation.py            (Phase 1C real-data audit runner)
│   ├── phase1_validation_report.json       (Audit report on 295 jobs)
│   ├── run_taxonomy_coverage_audit.py      (Phase 1D taxonomy coverage scanner)
│   └── taxonomy_coverage_report.json       (Audit report on 274 unmatched raw tokens)
├── ingestion/
│   ├── loaders.py                          (Streaming loaders for LinkedIn, Naukri, Parquet)
│   ├── normalizer.py                       (Text, company, title & location normalizers)
│   ├── schema.py                           (JobRecord & DeduplicatedJobRecord schemas)
│   ├── run_ingestion_demo.py               (Ingestion pipeline runner)
│   └── test_ingestion.py                   (Phase 0.5 test suite)
├── _phase0_check.py                        (Phase 0 taxonomy validation script)
└── README.md                               (Architecture and user guide)
```
- **Unexpected / Suspicious files**: None found.
- **Duplicate implementations**: None found.
- **Temporary / Debug files**: Clean. (Standard Python `__pycache__` directories exist for compiled bytecode).

---

## 3. Phase 0.5 Ingestion & Deduplication Audit

- **Input Volume**: 300 raw sampled records (100 LinkedIn India, 100 Naukri, 100 Parquet).
- **Deduplicated Output**: 295 unique canonical records.
- **Duplicates Removed**: Exactly 5 confirmed duplicates merged across clusters.
- **Source Breakdown**:
  - `linkedin_india`: 99 unique jobs
  - `naukri`: 99 unique jobs
  - `parquet`: 97 unique jobs
- **Safety Cases Verified**:
  - **Case A (Exact duplicates)**: Merged with reason logged.
  - **Case B (Seniority distinction)**: `Senior ML Engineer` vs `ML Engineer` at the same company with identical skills is **strictly preserved** as 2 separate vacancies.
  - **Case C (Company distinction)**: Same title at different companies is strictly preserved.
  - **Case D (Multi-signal agreement)**: High text similarity ($\ge 75\%$) with title agreement at the same company merged safely.
- **Raw Data Immutability**: All loaders stream via `zipfile` and `pyarrow.parquet.ParquetFile.iter_batches()` without modifying raw files or writing temporary unzipped data.

---

## 4. Phase 1 Extractor Audit

- **Contract Schema**: Guaranteed `[{"skill_id": "...", "confidence_score": 0.xx}]`.
- **Confidence Tiers**: Fixed deterministic tiers strictly enforced:
  - Exact Canonical Name: `0.99`
  - Exact Alias: `0.96`
  - Normalized Phrase: `0.90`
  - Conservative Fuzzy: `0.80`
- **False-Positive Regression Checks**:
  1. `"contractor role for software engineer"` $\to$ **Blocked** (`SK_RELAYS` not extracted).
  2. `"transform data pipelines using python"` $\to$ **Blocked** (`SK_TRANSFORMER` not extracted; only `SK_PYTHON` extracted).
  3. `"set up blockchain nodes and validators"` $\to$ **Blocked** (`SK_NODEJS` not extracted).
  4. `"lead backend engineer with cluster management expertise"` $\to$ **Blocked** (`SK_CRM_RETAIL` not extracted).
  5. `"the employee plays a vital role in our security architecture"` $\to$ **Blocked** (`SK_VITAL_SIGNS` not extracted).
  6. `"first and second level technical support"` $\to$ **Blocked** (`SK_FIRST_AID` not extracted).
- **Extraction Input**: Constructed strictly from `title + " " + description`. `explicit_skills` is never used as an extraction input.

---

## 5. Phase 1 Real-Data Regression & Source Distribution Analysis

### Audit of Source Counts Difference
The audit investigated the difference between earlier pre-Phase 1D numbers and the final Phase 1D/2/3 numbers:

| Source | Phase 1C (Pre-Fuzzy Fix) Jobs with Skills / Mentions | Phase 1D / Phase 2 / Phase 3 Final Jobs with Skills / Mentions | Delta & Exact Root Cause |
| :--- | :---: | :---: | :--- |
| **`linkedin_india`** | 80 jobs / 206 mentions | **78 jobs / 198 mentions** | **-2 jobs, -8 mentions**: Removal of 8 false-positive `contractor` $\to$ `SK_RELAYS` matches (2 jobs had only this false match). |
| **`naukri`** | 69 jobs / 126 mentions | **69 jobs / 126 mentions** | **0 delta**: Clean dataset with zero false positives. |
| **`parquet`** | 66 jobs / 219 mentions | **64 jobs / 212 mentions** | **-2 jobs, -7 mentions**: Removal of 7 false-positive `transform` $\to$ `SK_TRANSFORMER` matches (2 jobs had only this false match). |
| **Total** | 215 jobs / 551 mentions (32 IDs) | **211 jobs / 536 mentions (30 IDs)** | **-4 jobs, -15 mentions, -2 false IDs**: Mathematical proof that the change was 100% due to approved false-positive elimination. |

---

## 6. Phase 2 Batch Artifact Audit

- **Artifact File**: `ml/extract/extracted_job_skills.json`
- **Integrity Checks**:
  - Total records: 295 (0 skipped, 0 failed).
  - Unique `job_id` count: 295 (no duplicates).
  - Preserved metadata: `job_id`, `source`, `source_record_id`, `title`, `skills`.
  - Zero-skill jobs: 84 records preserved with `"skills": []` (no silent record loss).
  - All 536 extracted skill entries contain only `skill_id` and `confidence_score`.
  - All skill IDs exist in `skills.json`.
  - No job contains duplicate skill IDs.

---

## 7. Phase 3 Demand Aggregation Audit

Independent mathematical recalculation directly from `extracted_job_skills.json` matched `demand_analysis.json` exactly:

### Top In-Demand Skills Recalculation
| Skill ID | Skill Name | Canonical Category | Independent Count | Artifact Count | Demand Share | Avg Confidence |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `SK_SQL` | SQL Database Management | IT / Data | **99** | **99** | **33.56%** | 0.96 |
| `SK_PYTHON` | Python Programming | IT / Data | **98** | **98** | **33.22%** | 0.96 |
| `SK_AWS` | AWS Cloud Services | IT / Data | **51** | **51** | **17.29%** | 0.96 |
| `SK_JAVASCRIPT`| JavaScript Programming | IT / Data | **37** | **37** | **12.54%** | 0.96 |
| `SK_REST_API` | RESTful API Design | IT / Data | **31** | **31** | **10.51%** | 0.94 |
| `SK_GIT` | Git Version Control | IT / Data | **30** | **30** | **10.17%** | 0.96 |
| `SK_DATA_VIZ` | Data Visualization | IT / Data | **21** | **21** | **7.12%** | 0.96 |
| `SK_LINUX` | Linux System Administration | IT / Data | **21** | **21** | **7.12%** | 0.96 |
| `SK_SPARK` | Apache Spark Big Data | IT / Data | **21** | **21** | **7.12%** | 0.96 |
| `SK_DOCKER` | Docker Containerization | IT / Data | **17** | **17** | **5.76%** | 0.96 |

### Metric Verification
- **Denominator**: Total jobs evaluated = 295 ($211 \text{ jobs with skills} + 84 \text{ zero-skill jobs}$).
- **Source Normalization**: Computed accurately per source (`linkedin_india`, `naukri`, `parquet`).
- **Co-occurrence**: Pair counts match independent set intersection (e.g. Python + SQL in 46 jobs / 15.59%).
- **Temporal Safety**: Reports `"status": "not_available"` with explicit rationale (no artificial dates fabricated).

---

## 8. Cross-Phase Consistency

The end-to-end provenance chain was tested and validated:
$$\text{Phase 0.5 } (295 \text{ records}) \xrightarrow{\text{1:1 ID match}} \text{Phase 2 } (295 \text{ records}) \xrightarrow{\text{1:1 aggregation}} \text{Phase 3 } (295 \text{ jobs})$$
- Phase 0.5 `canonical_id` sequence matches Phase 2 `job_id` sequence identically.
- Zero silent record loss.
- Zero orphaned skill mentions.

---

## 9. Taxonomy Integrity

- File: `ml/data/skills.json`
- **Total Canonical Skills**: 68.
- **Unique Skill IDs**: 68 (no duplicate IDs).
- **Unique Skill Names**: 68 (no duplicate canonical names).
- **Sectors Covered**: EV / Automotive, IT / Data, Electrician / Electronics, Healthcare Support, Retail / Sales.
- **Aliases**: Valid string arrays with no cyclic mappings.

---

## 10. Data Immutability Audit

- Directory: `C:\Users\Nehal Jois\Documents\SIH\Data`
- Number of files: 11
- File Modification Verification: All timestamps match original download/creation times (September 12, 2026).
- Zero files created, extracted, modified, or overwritten by the ML pipeline.

---

## 11. Git Safety Audit

- Checked workspace repository status.
- Zero raw datasets, archives, temporary dumps, `.env` credentials, or database connection strings are exposed or improperly tracked.

---

## 12. Dependency Audit

- **Analyzed Files**: 18 Python source files in `ml/`.
- **Standard Library Modules**: `os`, `sys`, `re`, `json`, `io`, `csv`, `time`, `zipfile`, `unittest`, `dataclasses`, `pathlib`, `typing`, `collections`, `difflib`, `tracemalloc`.
- **External Dependencies**: `pyarrow` (used strictly for zero-RAM chunk streaming in `ml/ingestion/loaders.py`).
- **Unnecessary Dependencies**: Zero. No heavy machine learning frameworks (e.g., PyTorch, Transformers, spaCy) are imported.

---

## 13. Architecture & Phase Boundary Audits

- **Backend / Database Boundary**:
  - Zero imports of `fastapi`, `sqlalchemy`, `psycopg2`, `asyncpg`, `backend.app`, or database models.
  - ML operates purely as stateless, deterministic computational modules reading and producing JSON artifacts.
- **Phase Boundary (No Premature Phase 4+ Code)**:
  - Zero implementations of skill gap analysis, course recommendations, trainer recommendations, demand forecasting, or career pathways.

---

## 14. Determinism & Reproducibility

- The full pipeline was executed across **3 consecutive end-to-end iterations**.
- Comparison of generated batch artifacts and demand outputs yielded **100% byte-for-byte identical JSON**.
- No nondeterministic sets or unseeded randomized behavior.

---

## 15. Performance & Resource Benchmarks

Measured on the 300 raw record / 295 deduplicated job evaluation benchmark:
| Pipeline Phase | Execution Time | Peak RAM Delta |
| :--- | :---: | :---: |
| **Phase 0.5 Ingestion & Deduplication** | 981.1 ms (~0.98 s) | 1.09 MB |
| **Phase 1 & 2 Batch Skill Extraction** | 33,894.5 ms (~33.89 s) | 0.23 MB |
| **Phase 3 Demand Aggregation & Trends** | 16.7 ms (~0.02 s) | 0.42 MB |
| **Total Full Pipeline Execution** | **34,892.3 ms (~34.89 s)** | **< 2.0 MB** |

---

## 16. Documentation Consistency

- `ml/README.md` was audited against codebase reality.
- All file paths, public interfaces (`extract_skills`, `DemandAggregator`), test commands, and baseline metrics (295 jobs, 211 with skills, 84 zero-skill, 536 mentions, 30 detected skills) match the current implementation.

---

## 17. End-to-End Rebuild Result

A clean end-to-end execution of:
1. `ml.ingestion.test_ingestion`
2. `ml.extract.test_extractor`
3. `ml.extract.test_batch_extractor`
4. `ml.extract.batch_extractor`
5. `ml.demand.test_demand_aggregator`
6. `ml.demand.run_demand_analysis`

All unit test suites and CLI runners executed with exit code 0.

---

## 18. Issues Discovered & Severity

| Issue # | Description | Severity | Recommended Action |
| :---: | :--- | :---: | :--- |
| **1** | Historical documentation note: Phase 1C recorded 32 detected skill IDs before false-positive removal; Phase 1D/2/3 recorded 30 active canonical skills. | **INFORMATIONAL** | Documented in Section 5 of this audit report. No code change needed; behavior is correct. |
| **2** | Parquet source lacks job location data in raw schema, defaulting `location` to `""`. | **INFORMATIONAL** | Normalizer correctly defaults missing location to empty string. No action needed. |

---

## 19. Final Status

```text
======================================================
AUDIT STATUS: PASS
======================================================
```
All pipeline phases (0.5, 1, 2, 3) are mathematically verified, cross-phase consistent, deterministic, fully tested, and strictly within architectural boundaries. The pipeline is ready for Phase 4.
