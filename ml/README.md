# SkillMesh — ML Layer (`ml/`)

This directory contains the ML/NLP processing engine and data assets for SkillMesh (developed by the WorkNexus team, SIH26134).

## Architecture & Responsibilities
- **ML Layer Boundary**: Owns skill taxonomy, canonical ID resolution, extraction confidence scoring, batch extraction artifact generation, demand aggregation, curriculum skill gap analysis, trust-weighted employer feedback intelligence, multi-signal evidence aggregation, and generic rule-based skill recommendations.
- **Backend Boundary**: Core backend (FastAPI/SQLAlchemy) manages database persistence, authentication, course entities, and business trust weighting. All communication strictly adheres to the frozen JSON contracts in `Pdfs/ML_BACKEND_CONTRACT.md`.

---

## Directory Structure

```text
ml/
├── api/
│   ├── __init__.py                   # Public MLService and exception exports
│   ├── models.py                     # Service boundary data models and exception hierarchy
│   ├── service.py                    # Unified MLService facade for backend integration
│   └── test_service.py               # 39-point unit test suite for Phase 8 integration
├── context/
│   ├── __init__.py                   # Public ContextAwareRecommendationEngine export
│   ├── contextual_recommender.py     # Deterministic context-aware recommendation engine
│   ├── contextual_recommendations.json # Phase 6B output artifact with role-contextual recommendations
│   ├── run_contextual_recommendations.py # CLI runner for contextual recommendations
│   └── test_contextual_recommender.py # 24-point unit test suite for Phase 6B
├── course_mapping/
│   ├── __init__.py                   # Public PersonalizedCourseMapper export
│   ├── course_mapper.py              # Pure deterministic skill-to-course mapping engine
│   ├── personalized_course_mapping.json # Phase 7D output artifact with course mappings
│   ├── run_course_mapping.py         # CLI runner for course mapping generation
│   └── test_course_mapper.py         # 30-point unit test suite for Phase 7D
├── course_selection/
│   ├── __init__.py                   # Public CourseCandidateSelector export
│   ├── course_selector.py            # Deterministic course-selection candidate engine
│   ├── course_selection_candidates.json # Phase 7E output artifact with student candidate courses
│   ├── run_course_selection.py       # CLI runner for course candidate selection
│   └── test_course_selector.py       # 34-point unit test suite for Phase 7E
├── data/
│   ├── skills.json                   # Canonical skill taxonomy (68 skills across 5 domains)
│   ├── sample_courses.json           # 5 sample courses (Course 42 missing SK_CAN for demo)
│   ├── sample_employer_feedback.json # 5 synthetic employer feedback entries
│   ├── sample_job_postings.json      # 20 synthetic job postings
│   ├── sample_role_contexts.json     # 5 synthetic target role contexts
│   ├── sample_student_profiles.json  # 5 synthetic student profiles with multi-source evidence
│   └── sample_student_role_assignments.json # 5 synthetic student-to-role assignment mappings
├── dedup/
│   └── deduplicator.py               # Conservative multi-signal deduplication layer
├── demand/
│   ├── __init__.py                   # Public DemandAggregator export
│   ├── demand_aggregator.py          # Core job-based demand, source, category & co-occurrence logic
│   ├── demand_analysis.json          # Phase 3 output artifact with complete demand metrics
│   ├── run_demand_analysis.py        # CLI runner to execute aggregation and print reports
│   └── test_demand_aggregator.py     # 12-point unit test suite for Phase 3
├── employer/
│   ├── __init__.py                   # Public EmployerFeedbackAnalyzer export
│   ├── feedback_analyzer.py          # Core employer feedback extraction & trust weighting engine
│   ├── employer_feedback_analysis.json # Phase 5A output artifact with skill & course employer signals
│   ├── run_feedback_analysis.py      # CLI runner for employer feedback intelligence
│   └── test_feedback_analyzer.py     # 16-point unit test suite for Phase 5A
├── evidence/
│   ├── __init__.py                   # Public MultiSignalEvidenceAggregator export
│   ├── evidence_aggregator.py        # Multi-signal composition & categorical relationship engine
│   ├── multi_signal_evidence.json    # Phase 5B output artifact with dual-signal evidence records
│   ├── run_evidence_analysis.py      # CLI runner for multi-signal evidence generation
│   └── test_evidence_aggregator.py   # 16-point unit test suite for Phase 5B
├── extract/
│   ├── __init__.py                   # Public extract_skills(text) entrypoint
│   ├── extractor.py                  # Token-aligned boundary-safe regex & conservative fuzzy extractor
│   ├── batch_extractor.py            # Phase 2 batch extraction processor & pipeline runner
│   ├── extracted_job_skills.json     # Phase 2 output batch artifact with provenance
│   ├── test_extractor.py             # Phase 1 unit and false-positive regression tests
│   ├── test_batch_extractor.py       # Phase 2 batch processor unit test suite
│   ├── phase1_validation_report.json # Real-data extraction quality audit on 295 jobs
│   └── taxonomy_coverage_report.json # Audit of 274 unmatched raw vocabulary tokens
├── gap/
│   ├── __init__.py                   # Public SkillGapAnalyzer export
│   ├── gap_analyzer.py               # Core curriculum vs industry demand gap analysis engine
│   ├── skill_gap_analysis.json       # Phase 4 output artifact with course & global gap metrics
│   ├── run_gap_analysis.py           # CLI runner for skill gap calculation and reporting
│   └── test_gap_analyzer.py          # 15-point unit test suite for Phase 4
├── gap_student/
│   ├── __init__.py                   # Public StudentSkillGapAnalyzer export
│   ├── student_gap_analyzer.py       # Deterministic student-to-role skill gap comparison engine
│   ├── student_skill_gaps.json       # Phase 7B output artifact with student skill gap records
│   ├── run_student_gap_analysis.py   # CLI runner for student skill gap analysis
│   └── test_student_gap_analyzer.py  # 28-point unit test suite for Phase 7B
├── ingestion/
│   ├── loaders.py                    # Streaming loaders for LinkedIn India, Naukri, Parquet
│   ├── normalizer.py                 # Text, company, title & location normalizers
│   ├── run_ingestion_demo.py         # Real data ingestion demo runner
│   └── schema.py                     # JobRecord and DeduplicatedJobRecord dataclasses
├── personalized/
│   ├── __init__.py                   # Public PersonalizedSkillRecommendationEngine export
│   ├── personalized_recommender.py   # Deterministic personalized skill recommendation engine
│   ├── student_skill_recommendations.json # Phase 7C output artifact with personalized recommendations
│   ├── run_personalized_recommendations.py # CLI runner for personalized recommendations
│   └── test_personalized_recommender.py # 32-point unit test suite for Phase 7C
├── recommend/
│   ├── __init__.py                   # Public GenericSkillRecommendationEngine export
│   ├── recommendation_engine.py      # Transparent rule-based skill recommendation engine
│   ├── skill_recommendations.json    # Phase 6A output artifact with explainable recommendations
│   ├── run_recommendations.py        # CLI runner for generic skill recommendations
│   └── test_recommendation_engine.py # 20-point unit test suite for Phase 6A
├── student/
│   ├── __init__.py                   # Public StudentProfileEngine export
│   ├── student_profile.py            # Deterministic student skill profile normalization engine
│   ├── student_skill_profiles.json   # Phase 7A output artifact with normalized student profiles
│   ├── run_student_profiles.py       # CLI runner for student skill profile processing
│   └── test_student_profile.py       # 24-point unit test suite for Phase 7A
├── PHASE_3_5_AUDIT_REPORT.md         # Full Phase 3.5 ML pipeline audit & regression report
├── README.md                         # Architecture & data documentation
└── _phase0_check.py                  # Phase 0 taxonomy validation script
```

---

## Pipeline Phases Overview

### Phase 0: Taxonomy & Benchmark Setup
- Canonical taxonomy defined in `ml/data/skills.json` with 68 canonical skills across 5 sectors.
- Sample courses, feedback, and job postings created for benchmark verification.

### Phase 0.5: Real Data Ingestion & Conservative Deduplication
- Streams real datasets (`archive3.zip`, `archive1.zip`, `train-00000-of-00001.parquet`) without permanent disk extraction or full RAM loading.
- Converts raw records to normalized internal `JobRecord` dataclasses.
- Conservatively merges duplicate vacancies based on company, seniority, title, and high text similarity ($\ge 75\%$), retaining complete source provenance.
- Ingestion of 300 sample records yields **295 unique deduplicated jobs**.

### Phase 1: Skill Extraction & Canonical Normalization
- Public interface: `from ml.extract import extract_skills`.
- Input: Plain text (`title + " " + description`). `explicit_skills` is never used as an extraction input.
- Output contract: Strictly `[{"skill_id": "...", "confidence_score": 0.xx}]`.
- Deterministic fixed confidence tiers:
  - Exact Canonical Name: `0.99`
  - Exact Alias: `0.96`
  - Normalized Phrase: `0.90`
  - Conservative Fuzzy: `0.80` (with strict single-word length guards and multi-word token alignment).

### Phase 2: Batch Job Skill Extraction
- Runs batch extraction over all deduplicated `JobRecord`s produced by Phase 0.5.
- Generates the reusable ML batch artifact: [`ml/extract/extracted_job_skills.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/extract/extracted_job_skills.json).
- **Provenance Retained**: `job_id`, `source`, `source_record_id`, `title`, and `skills`.
- **Zero-Skill Jobs**: Retained in the artifact with `"skills": []` (no silent record loss).
- **Validation**: Every extracted skill is verified against `skills.json` with no duplicate IDs per job.
- **Baseline Results**:
  - Total input jobs: `295`
  - Jobs with skills: `211 (71.5%)`
  - Zero-skill jobs: `84 (28.5%)`
  - Total skill mentions: `536`
  - Unique canonical skills detected: `30`

### Phase 3: Skill Demand Aggregation & Trends
- Consumes ONLY the Phase 2 batch artifact (`ml/extract/extracted_job_skills.json`) and canonical taxonomy (`ml/data/skills.json`).
- Produces the demand artifact: [`ml/demand/demand_analysis.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/demand/demand_analysis.json).
- **Job-Based Demand Metric**: Demand is measured by the number and fraction of unique job postings requiring a skill ($job\_count / total\_jobs$), avoiding frequency inflation from multiple mentions.
- **Source-Normalized Analysis**: Computes per-source share to account for dataset size variations across `linkedin_india`, `naukri`, and `parquet`.
- **Category Coverage**: Aggregates unique jobs and skill distribution per taxonomy category.
- **Skill Co-occurrence**: Identifies frequent skill pairs appearing in the same job postings (e.g. Python + SQL in 15.59% of jobs).
- **Temporal Safety**: Explicitly reports `"status": "not_available"` for time trends as posting dates are not tracked in the batch artifact.

### Phase 4: Skill Gap Analysis
- Consumes authoritative Phase 3 demand (`ml/demand/demand_analysis.json`), course data (`ml/data/sample_courses.json`), and taxonomy (`ml/data/skills.json`).
- Produces the gap artifact: [`ml/gap/skill_gap_analysis.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/gap/skill_gap_analysis.json).
- **Observed Demand Universe**: Restricts the comparison universe to the 30 active skills with observed job demand (total observed demand = 536 job-skill requirements).
- **Core Metrics**:
  - `demand_coverage_ratio = covered_demand / total_observed_demand`
  - `skill_coverage_ratio = covered_demand_skills / observed_demand_skills`
- **Factual Classifications**: Explicitly distinguishes between `covered_skills` (in curriculum & in demand), `missing_skills` (in demand & absent from curriculum), and `course_skills_without_observed_demand` (in curriculum & absent from current job corpus).
- **Sector/Category Breakdown**: Computes category-level coverage and demand metrics for each course.
- **Global Skill Gap View**: Quantifies how many courses cover vs miss each demanded skill across the curriculum portfolio.

### Phase 5A: Employer Feedback Intelligence
- Consumes employer feedback (`ml/data/sample_employer_feedback.json`) and taxonomy (`ml/data/skills.json`).
- Produces the employer signal artifact: [`ml/employer/employer_feedback_analysis.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/employer/employer_feedback_analysis.json).
- **Extraction Rule**: Skills are extracted strictly from `feedback_text` (or `comment`) using `extract_skills()`.
- **Trust Weighting**: Computes $\text{weighted\_signal} = \text{confidence\_score} \times \text{trust\_weight}$.
- **Counting Integrity**: Explicitly distinguishes between `feedback_count` (number of records mentioning a skill) and `unique_employer_count` (number of distinct employers).
- **Course Associations**: Groups feedback by `course_id` (e.g. Course 42 received 4 feedbacks from 4 employers, identifying strong `SK_CAN` signals).

### Phase 5B: Multi-Signal Skill Evidence Aggregation
- Consumes authoritative Phase 3 job demand (`ml/demand/demand_analysis.json`) and Phase 5A employer signals (`ml/employer/employer_feedback_analysis.json`).
- Produces the multi-signal evidence artifact: [`ml/evidence/multi_signal_evidence.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/evidence/multi_signal_evidence.json).
- **Union Skill Universe**: 35 total canonical skills ($30 \text{ job demand} \cup 9 \text{ employer feedback}$).
  - `both`: 4 skills (`SK_AIRFLOW`, `SK_BMS`, `SK_PYTHON`, `SK_SQL`)
  - `job_only`: 26 skills (`SK_AWS`, `SK_JAVASCRIPT`, `SK_REST_API`, `SK_GIT`, etc.)
  - `employer_feedback_only`: 5 skills (`SK_BATTERY_CELL`, `SK_CAN`, `SK_DIAG`, `SK_HIGH_VOLTAGE`, `SK_THERMAL`)
- **Strict Non-Combination Principle**: Preserves job demand measurements and employer feedback measurements separately without arbitrary mathematical weighting or universal score collapse.
- **Null Semantics**: Uses `null` (not 0) for unobserved signals to avoid misleading zero measurements.
- **Evidence Matrix**: Generates a compact tabular matrix indicating evidence presence across sources.

### Phase 6A: Generic Skill Recommendation Engine
- Consumes multi-signal evidence (`ml/evidence/multi_signal_evidence.json`), course gap context (`ml/gap/skill_gap_analysis.json`), and taxonomy (`ml/data/skills.json`).
- Produces the recommendation artifact: [`ml/recommend/skill_recommendations.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/recommend/skill_recommendations.json).
- **Explicit Rule-Based Logic**:
  - `market_demand`: `job_demand.observed == true and job_count > 0`
  - `employer_validation`: `employer_validation.observed == true and unique_employer_count > 0`
  - `course_coverage`: Skill taught by $\ge 1$ course in Phase 4.
  - `multi_source_evidence`: `evidence_relationship == "both"`.
- **Recommendation Conditions**:
  - Condition 1: `market_demand == true and employer_validation == true`
  - Condition 2: `market_demand == true and course_coverage == false`
  - Condition 3: `employer_validation == true and market_demand == false`
- **Structured Reason IDs**: Generates machine-readable, factual reasons (`"observed_market_demand"`, `"employer_validated"`, `"observed_in_both_sources"`, `"course_coverage_gap"`, `"employer_only_signal"`).
- **No Universal Score / No Ranking**: Sorts strictly by `skill_id ASC`. Preserves original measurements without black-box scores.

#### Phase 6A Documented Limitations
1. The recommendation universe is limited to skills observed in the current Phase 5B evidence universe (35 skills).
2. The current job corpus contains only 295 deduplicated job postings.
3. Employer validation currently contains only 5 feedback records across 5 employers.
4. Employer-only skills represent emerging or specialized evidence that is absent from the current job corpus sample.
5. Absence from the current sample does NOT mean a skill is unimportant.
6. Phase 6A does not forecast future industry demand.
7. Phase 6A does not personalize recommendations to individual students or roles.
8. Phase 6A does not recommend courses or modify curriculum entities.

### Phase 6B: Context-Aware Skill Recommendation Engine
- Consumes explicit synthetic target-role contexts (`ml/data/sample_role_contexts.json`), Phase 6A generic recommendations (`ml/recommend/skill_recommendations.json`), Phase 5B evidence (`ml/evidence/multi_signal_evidence.json`), and taxonomy (`ml/data/skills.json`).
- Produces the context-aware recommendation artifact: [`ml/context/contextual_recommendations.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/context/contextual_recommendations.json).
- **Explicit Role Grounding**: Filters generic skill recommendations strictly against explicit target role mappings without synthesizing arbitrary role-fit scores, percentage matching, or rankings.
- **Three-Tier Role Skill Context Representation**:
  - `recommended`: Skill mapped to role and recommended by Phase 6A evidence (reason: `"explicit_role_skill_mapping"`).
  - `not_recommended`: Skill mapped to role but not recommended by Phase 6A evidence (e.g. `SK_SPARK`, `SK_GIT`, `SK_DOCKER`; reason: `"role_mapping_without_generic_recommendation"`).
  - `not_available`: Skill mapped to role in taxonomy but not present in Phase 6A / Phase 5B evidence universe (e.g. `SK_PLC`, `SK_PATIENT_CARE`; reason: `"role_skill_not_in_phase6a_universe"`).
- **Target Roles Evaluated (5 Synthetic Roles)**:
  - `ROLE_DATA_ENGINEER`: 5 target skills (4 recommended, 1 not recommended)
  - `ROLE_EV_TECHNICIAN`: 6 target skills (6 recommended, 0 not recommended)
  - `ROLE_FULL_STACK_DEV`: 6 target skills (4 recommended, 2 not recommended)
  - `ROLE_HEALTHCARE_ASST`: 5 target skills (1 recommended, 4 unavailable)
  - `ROLE_INDUSTRIAL_AUTO`: 4 target skills (1 recommended, 3 unavailable)
- **Total Mappings**: 26 total role-skill mappings across 5 roles $\to$ 16 contextual recommendations, 3 not recommended, 7 unavailable.
- **Determinism & Explainability**: Output is strictly sorted by `role_id ASC` and `skill_id ASC`. Full evidence and course context are preserved transparently.

#### Phase 6B Documented Limitations
1. Role-skill mappings are synthetic demonstration profiles defined in `sample_role_contexts.json`.
2. Phase 6B does not invent role-skill associations dynamically (no LLMs, ML embeddings, or heuristics).
3. Phase 6B does not compute role-fit or readiness scores.
4. Unavailable skills reflect skills in the canonical taxonomy that had 0 job demand in the 295-job corpus and 0 employer feedback mentions.
5. Phase 6B does not personalize recommendations to individual students or learners.
6. Phase 6B does not generate learning paths or sequence courses.

### Phase 7A: Student Skill Profile Engine
- Consumes controlled synthetic student profiles (`ml/data/sample_student_profiles.json`) and canonical taxonomy (`ml/data/skills.json`).
- Produces the student profile artifact: [`ml/student/student_skill_profiles.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/student/student_skill_profiles.json).
- **Skill Provenance & Categorical Evidence**: Validates claimed and verified skills against canonical taxonomy IDs and tracks exact evidence source (`"self_reported"`, `"course_completed"`, `"project"`, `"certification"`, `"assessment"`) with categorical strength (`"basic"`, `"intermediate"`, `"advanced"`).
- **Multiple Evidence Sources**: Supports multiple distinct evidence records per skill (e.g. `SK_PYTHON` supported by both `project` and `certification`) without collapsing or discarding provenance.
- **Categorical Integrity (No Numerical Proficiency Scoring)**: Avoids converting categorical evidence into arbitrary numerical proficiency percentages, mastery scores, or ranking heuristics.
- **Deterministic Derivation**: Derives skill names, taxonomy categories, and student-level `categories_present` directly from `skills.json` without manual redundancy.
- **Target Independence**: Operates strictly on current skills and evidence without consuming target roles, job demand, or recommendation engines.

#### Phase 7A Documented Limitations
1. Student profiles are synthetic benchmark datasets for controlled development and testing (`sample_student_profiles.json`).
2. Self-reported evidence is not equivalent to independently verified assessment evidence.
3. Evidence strength is categorical and is not converted into a numerical proficiency score.
4. Phase 7A does not infer proficiency or expertise levels.
5. Phase 7A does not compare students against one another.
6. Phase 7A does not identify skill gaps (deferred to Phase 7B).
7. Phase 7A does not recommend skills or courses.
8. Phase 7A does not personalize learning paths.

### Phase 7B: Student Skill Gap Analysis
- Consumes normalized student skill profiles (`ml/student/student_skill_profiles.json`), Phase 6B contextual recommendations (`ml/context/contextual_recommendations.json`), student-to-role assignments (`ml/data/sample_student_role_assignments.json`), and taxonomy (`ml/data/skills.json`).
- Produces the student skill gap artifact: [`ml/gap_student/student_skill_gaps.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/gap_student/student_skill_gaps.json).
- **Exact Canonical Skill ID Matching**: Compares student skills strictly using canonical `skill_id` (no fuzzy matching, title matching, or category heuristics).
- **Three-Tier Gap & Evidence Representation**:
  - `present`: Skill exists in student profile and is required by target role. Preserves full student evidence records.
  - `missing`: Skill is required by target role but absent from student profile.
  - `unavailable`: Identifies role skills where Phase 6B contextual evidence is `not_available` (e.g. `SK_CPR_BLS`, `SK_FIRST_AID`, `SK_PANEL_WIRING`), preserving this evidence distinction independently from student possession.
- **Strict Absence of Scores / Percentages**: Completely forbids `gap_score`, `role_match_score`, `readiness_score`, or percentage fit calculations.
- **Full Provenance & Context Retention**: Retains Phase 6B generic/contextual recommendation status (`recommended`, `not_recommended`, `not_available`) and student multi-source evidence lists.

#### Phase 7B Documented Limitations
1. Student-role assignments are synthetic benchmark mappings (`sample_student_role_assignments.json`).
2. Role-skill mappings are synthetic benchmark mappings (`sample_role_contexts.json`).
3. Current evidence is limited to the existing project artifacts.
4. A missing skill means the skill is absent from the student's declared profile; it does not mean the student cannot perform it.
5. A present skill does not imply sufficient proficiency.
6. Phase 7B does not rank gaps or assign priority weights.
7. Phase 7B does not recommend courses or identify learning solutions.
8. Phase 7B does not generate learning paths.
9. Phase 7B does not predict career outcomes or employability.

### Phase 7C: Personalized Skill Recommendation Engine
- Consumes validated student skill gaps (`ml/gap_student/student_skill_gaps.json`), generic recommendations (`ml/recommend/skill_recommendations.json`), contextual role contexts (`ml/context/contextual_recommendations.json`), multi-signal evidence (`ml/evidence/multi_signal_evidence.json`), and taxonomy (`ml/data/skills.json`).
- Produces the personalized recommendation artifact: [`ml/personalized/student_skill_recommendations.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/personalized/student_skill_recommendations.json).
- **Core Recommendation Condition**: A skill is recommended if and only if `student_status == "missing"` AND `role_requires_skill == true` AND `generic_recommendation_status == "recommended"`.
- **Three-Tier Personalized Classification**:
  - `already_present`: Skill is already present in student profile. Not recommended. (Reason: `"already_present"`).
  - `recommended`: Skill is missing, required by target role, and backed by Phase 6A generic recommendation evidence. (Reasons: `"student_skill_gap"`, `"role_requirement"`, `"generic_evidence_recommended"`, plus specific evidence reasons: `"market_demand_evidence"`, `"employer_validation_evidence"`, `"multi_source_evidence"`, `"course_coverage_gap"`).
  - `not_recommended`: Skill is missing but Phase 6A generic recommendation status is `not_recommended` OR Phase 6B contextual evidence is `not_available` (e.g. `SK_SPARK`, `SK_GIT`, `SK_PANEL_WIRING`). (Reasons: `"student_skill_gap"`, `"role_requirement"`, optional `"contextual_evidence_unavailable"`).
- **Complete Role Skill Representation**: All role skills are retained in `skill_recommendations` for full auditability.
- **Zero Black-Box Scores / Zero Ranking**: Preserves underlying multi-signal evidence without computing proficiency percentages, priority scores, or readiness percentages.

#### Phase 7C Documented Limitations
1. Student profiles and student-role assignments are synthetic benchmark datasets.
2. Role-skill mappings are synthetic benchmark mappings.
3. The evidence universe is limited to current project datasets.
4. A recommendation indicates an evidence-backed skill development candidate, not guaranteed career success.
5. Presence of a skill does not prove sufficient proficiency.
6. Absence of employer evidence does not prove lack of employer demand.
7. Phase 7C does not recommend courses or training entities (deferred to Phase 7D).
8. Phase 7C does not generate learning paths or sequencing.
9. Phase 7C does not forecast future job demand.

### Phase 7D: Course / Learning-Path Mapping
- Consumes Phase 7C personalized skill recommendations ([`ml/personalized/student_skill_recommendations.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/personalized/student_skill_recommendations.json)) and the course catalog ([`ml/data/sample_courses.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/data/sample_courses.json)).
- Produces the course-mapped artifact: [`ml/course_mapping/personalized_course_mapping.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/course_mapping/personalized_course_mapping.json).
- **Pure Mapping Layer**: Maps personalized recommended skills (`personalized_status == "recommended"`) to available courses via exact canonical `skill_id` matching in `taught_skills`.
- **Transparent Status Representation**:
  - `covered`: At least one catalog course teaches the skill (`course_count >= 1`, matched courses preserved).
  - `not_covered`: Zero catalog courses teach the skill (`course_count == 0`, `matching_courses: []`).
- **Multiple-Course Match Handling**: All matching courses are retained and deterministically sorted by `course_id ASC` (e.g. `SK_SQL` matches Course 101 and Course 102).
- **Global Inverted Index**: Provides a catalog-level mapping of all 68 canonical skills to matching courses for efficient lookup and catalog coverage audits.
- **Zero Ranking / Zero Sequencing**: Absolutely no course quality scores, fit percentages, best course recommendations, or prerequisite sequencing algorithms.

#### Phase 7D Documented Limitations
1. Course catalog is a synthetic benchmark dataset (`sample_courses.json`).
2. Skill-course links rely exclusively on exact canonical `skill_id` matching in course definitions.
3. Phase 7D does not rank courses or evaluate instructional quality.
4. Phase 7D does not optimize learning paths or schedule prerequisite sequences.
5. Presence in a course does not guarantee learner mastery or job placement.
6. `not_covered` indicates an institutional catalog deficit, not lack of industry demand.

### Phase 7E: Course Selection Candidates
- Consumes Phase 7C personalized recommendations ([`ml/personalized/student_skill_recommendations.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/personalized/student_skill_recommendations.json)), Phase 7D course mappings ([`ml/course_mapping/personalized_course_mapping.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/course_mapping/personalized_course_mapping.json)), and the course catalog ([`ml/data/sample_courses.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/data/sample_courses.json)).
- Produces the student candidate courses artifact: [`ml/course_selection/course_selection_candidates.json`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/course_selection/course_selection_candidates.json).
- **Core Principle**: A course is identified as a `candidate_course` for a student if and only if the course contains $\ge 1$ canonical skill that is a personalized recommendation for that student (`personalized_status == "recommended"`).
- **Multi-Skill Course Coverage**: Identifies which personalized recommendations are covered by each candidate course (e.g. Course 42 covers `SK_DIAG` and `SK_THERMAL` for `STU_002`). Unrelated course skills do not count toward personalized student coverage.
- **Multi-Course Skill Coverage**: Retains all candidate courses covering a given recommendation without forcing a single choice (e.g. `SK_SQL` is covered by both Course 101 and Course 102 for `STU_003`; both are retained).
- **Preservation of Uncovered Skills**: Explicitly lists personalized recommendations with 0 candidate courses in `uncovered_personalized_skills` (e.g. `SK_AWS`, `SK_CAN`, `SK_EHR`, `SK_SCADA`).
- **Global Course Intersection**: Provides `global_course_usage` mapping courses to all students for whom they serve as candidates, sorted `course_id ASC` and `student_id ASC`.
- **Zero Ranking / Zero Scores / Zero Sequencing**: Forbids course ranking, fit scores, best course labeling, quality scores, and learning path sequencing.

#### Phase 7E Documented Limitations
1. Course catalog is a synthetic benchmark dataset (`sample_courses.json`).
2. Course skill mappings are synthetic benchmark mappings.
3. Candidate-course status is based solely on explicit canonical skill coverage.
4. Course quality, instructional rigor, and provider reputation are not evaluated.
5. Course suitability for individual learning styles is not evaluated.
6. No course ranking, scoring, or single "best" course selection is performed.
7. No learning path or prerequisite sequence is constructed.
8. No prerequisites or dependencies are inferred.
9. No course completion probability or learner retention is estimated.
10. No employment outcome or career advancement is guaranteed.
11. Real deployment requires validated institutional course catalogs and explicit prerequisite/dependency metadata if sequencing is desired.

### Phase 8: ML Integration Contract & Backend Handoff
- Implements the unified service facade: [`ml/api/service.py`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/api/service.py) (`MLService`).
- **Clean Architectural Separation**:
  - The FastAPI backend imports and calls `MLService` as an in-process local Python library.
  - The ML engine maintains zero dependencies on FastAPI, SQLAlchemy/databases, network HTTP clients, auth/RBAC, and frontend UI code.
- **Service Operations (12 Operations)**:
  - Runtime input: `extract_skills(text)`, `process_job(job)`, `analyze_employer_feedback(feedback)`.
  - Artifact benchmark mode: `get_skill_demand()`, `get_course_skill_gaps()`, `get_skill_evidence()`, `get_skill_recommendations()`, `get_role_skill_context(role_id)`, `get_student_skill_profile(student_id)`, `get_student_skill_gap(student_id, role_id)`, `get_personalized_recommendations(student_id, role_id)`, `get_course_candidates(student_id, role_id)`.
- **Handoff Documentation**: Authoritative integration guide available in [`ml/ML_BACKEND_HANDOFF.md`](file:///C:/Users/Nehal%20Jois/Documents/SIH/ml/ML_BACKEND_HANDOFF.md).

### Phase 9A: ML ↔ Backend Integration Foundation
- Implements the in-process Python adapter layer: [`backend/app/services/ml_adapter.py`](file:///C:/Users/Nehal%20Jois/Documents/SIH/backend/app/services/ml_adapter.py) (`MLAdapter`).
- **In-Process Integration**: Bridges FastAPI routes (`/api/v1/ml/extract-skills`, `/api/v1/jobs/`, `/api/v1/employers/feedback`) with `MLService` without intermediate HTTP hops or duplicated algorithms.
- **RBAC & Error Mapping**: Translates ML domain exceptions into clean HTTP status codes (`422`, `404`, `500`) with strict role enforcement (`Employer`, `Admin`, `Student`).
- **Integration Documentation**: Full documentation in [`docs/PHASE_9A_ML_BACKEND_INTEGRATION.md`](file:///C:/Users/Nehal%20Jois/Documents/SIH/docs/PHASE_9A_ML_BACKEND_INTEGRATION.md).

---

## How to Run Tests & Pipelines

```bash
# 1. Verify Phase 0 Taxonomy
python ml/_phase0_check.py

# 2. Run Phase 0.5 Ingestion & Deduplication Tests
python -m ml.ingestion.test_ingestion

# 3. Run Phase 1 Skill Extraction Tests
python -m ml.extract.test_extractor

# 4. Run Phase 2 Batch Extractor Tests
python -m ml.extract.test_batch_extractor

# 5. Execute Phase 2 Batch Processing & Generate Artifact
python -m ml.extract.batch_extractor

# 6. Run Phase 3 Demand Aggregator Tests
python -m unittest ml/demand/test_demand_aggregator.py

# 7. Execute Phase 3 Demand Aggregation & Generate Artifact
python -m ml.demand.run_demand_analysis

# 8. Run Phase 4 Skill Gap Analyzer Tests
python -m unittest ml/gap/test_gap_analyzer.py

# 9. Execute Phase 4 Skill Gap Analysis & Generate Artifact
python -m ml.gap.run_gap_analysis

# 10. Run Phase 5A Employer Feedback Tests
python -m unittest ml/employer/test_feedback_analyzer.py

# 11. Execute Phase 5A Employer Feedback Analysis & Generate Artifact
python -m ml.employer.run_feedback_analysis

# 12. Run Phase 5B Multi-Signal Evidence Tests
python -m unittest ml/evidence/test_evidence_aggregator.py

# 13. Execute Phase 5B Multi-Signal Evidence Aggregation & Generate Artifact
python -m ml.evidence.run_evidence_analysis

# 14. Run Phase 6A Generic Skill Recommendation Tests
python -m unittest ml/recommend/test_recommendation_engine.py

# 15. Execute Phase 6A Generic Skill Recommendations & Generate Artifact
python -m ml.recommend.run_recommendations

# 16. Run Phase 6B Context-Aware Skill Recommendation Tests
python -m unittest ml/context/test_contextual_recommender.py

# 17. Execute Phase 6B Context-Aware Recommendations & Generate Artifact
python -m ml.context.run_contextual_recommendations

# 18. Run Phase 7A Student Skill Profile Tests
python -m unittest ml/student/test_student_profile.py

# 19. Execute Phase 7A Student Skill Profile Normalization & Generate Artifact
python -m ml.student.run_student_profiles

# 20. Run Phase 7B Student Skill Gap Analysis Tests
python -m unittest ml/gap_student/test_student_gap_analyzer.py

# 21. Execute Phase 7B Student Skill Gap Analysis & Generate Artifact
python -m ml.gap_student.run_student_gap_analysis

# 22. Run Phase 7C Personalized Skill Recommendation Tests
python -m unittest ml/personalized/test_personalized_recommender.py

# 23. Execute Phase 7C Personalized Skill Recommendations & Generate Artifact
python -m ml.personalized.run_personalized_recommendations

# 24. Run Phase 7D Course Mapping Tests
python -m unittest ml/course_mapping/test_course_mapper.py

# 25. Execute Phase 7D Course Mapping & Generate Artifact
python -m ml.course_mapping.run_course_mapping

# 26. Run Phase 7E Course Candidate Selection Tests
python -m unittest ml/course_selection/test_course_selector.py

# 27. Execute Phase 7E Course Candidate Selection & Generate Artifact
python -m ml.course_selection.run_course_selection

# 28. Run Phase 8 ML Service Integration Tests
python -m unittest ml/api/test_service.py

# 29. Run Phase 9A Backend Integration Tests (12 tests)
python -m unittest discover -s backend/tests -p "test_*.py"

# Run All ML Test Suites Across All Phases (290 tests)
python -m unittest discover -s ml -p "test_*.py"
```

