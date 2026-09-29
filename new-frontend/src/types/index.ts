/**
 * WorkNexus (SkillMesh) Type Definitions
 * Enterprise labour-market intelligence and workforce curriculum-alignment platform.
 */

export type UserRole = 'student' | 'employer' | 'institute' | 'trainer' | 'admin';

export interface User {
  id: string | number;
  email: string;
  full_name?: string;
  name?: string;
  role: UserRole | string;
  is_active?: boolean;
  created_at?: string;
  target_role_id?: string | number | null;
  target_career?: string | null;
}

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  user?: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  role: string;
}

export interface Role {
  id: string;
  name: string;
  title?: string;
  description?: string;
  category?: string;
  required_skills?: string[];
  is_active?: boolean;
  demand_level?: string;
  salary_range?: string;
  total_openings?: number;
  created_at?: string;
}

export interface TargetRoleCreate {
  id: string;
  name: string;
  description?: string;
  skill_ids: string[];
}

export interface StudentProfile {
  id: string | number;
  user_id?: string | number;
  full_name?: string;
  email?: string;
  target_role_id?: string | null;
  target_role_name?: string | null;
  skills?: string[];
  education?: string;
  evidence_records?: SkillEvidence[];
  created_at?: string;
}

export interface StudentProfileCreate {
  user_id: number;
  target_role_id?: string | null;
}

export interface SkillEvidenceMetadata {
  repo?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface SkillEvidence {
  id?: string | number;
  student_profile_id?: number;
  student_id?: string | number;
  user_id?: string | number;
  skill_id: string;
  evidence_type: 'github_pr' | 'portfolio_project' | 'certification' | 'assessment' | 'coursework' | string;
  strength: number | string;
  metadata: SkillEvidenceMetadata;
  created_at?: string;
  verified?: boolean;
}

export interface SkillEvidenceSubmission {
  skill_id: string;
  evidence_type: string;
  strength: number | string;
  metadata: {
    repo?: string;
    timestamp?: string;
    [key: string]: unknown;
  };
}

export interface Skill {
  id: string | number;
  skill_id?: string;
  name: string;
  category?: string;
  description?: string;
  is_active?: boolean;
  created_at?: string;
  demand_score?: number;
}

export interface SkillCreate {
  skill_id: string;
  name: string;
  category: string;
  description?: string;
}

export interface SkillUpdate {
  name?: string;
  category?: string;
  description?: string;
  is_active?: boolean;
}

export interface UserSkill {
  id: number;
  user_id: number;
  skill_id: number;
  skill_name?: string;
  skill_code?: string;
  category?: string;
  proficiency_level: string; // beginner, intermediate, advanced, expert
  source: string; // self_reported, assessment, course_completion, resume_extraction
  created_at: string;
}

export interface UserSkillCreate {
  skill_id: number;
  proficiency_level: string;
  source?: string;
}

export interface UserSkillUpdate {
  proficiency_level?: string;
  source?: string;
}

export interface Course {
  id: number | string;
  course_id?: string;
  course_code?: string;
  name?: string;
  course_title?: string;
  title?: string;
  department?: string;
  provider?: string;
  semester?: string | null;
  duration?: string;
  duration_weeks?: number;
  description?: string | null;
  is_active?: boolean;
  level?: string;
  credits?: number;
  syllabus?: string[];
  created_at?: string;
}

export interface CourseCreate {
  course_id: string;
  course_code?: string;
  name: string;
  department: string;
  description?: string;
  semester?: string;
  is_active?: boolean;
}

export interface CourseUpdate {
  name?: string;
  department?: string;
  description?: string;
  semester?: string;
  is_active?: boolean;
}

export interface CourseSkill {
  id: number;
  course_id: number;
  skill_id: number;
  skill_name?: string;
  skill_code?: string;
  coverage_pct?: number;
  created_at: string;
}

export interface CourseSkillCreate {
  course_id: number;
  skill_id: number;
}

export interface JobPosting {
  id: number;
  title: string;
  company_name: string;
  description: string;
  location?: string | null;
  source?: string | null;
  posted_date?: string | null;
  created_at: string;
}

export interface JobPostingCreate {
  title: string;
  company_name: string;
  description: string;
  location?: string;
  source?: string;
}

export interface JobSkill {
  id: number;
  job_id: number;
  skill_id: string;
  created_at: string;
}

export interface JobSkillCreate {
  job_id: number;
  skill_id: string;
}

export interface StudentGap {
  student_id?: string | number;
  role_id?: string | number;
  role_name?: string;
  overall_match_score?: number;
  match_score?: number;
  gap_percentage?: number;
  gap_score?: number;
  acquired_skills: string[] | Array<{ id?: string; name: string; level?: number | string; strength?: string }>;
  missing_skills: string[] | Array<{ id?: string; name: string; priority?: string; weight?: number; importance?: number }>;
  skill_importance?: Record<string, number> | Array<{ skill: string; importance: number }>;
}

export interface CourseCandidate {
  course_id: string | number;
  course_name?: string;
  title?: string;
  provider?: string;
  skill_coverage_score: number;
  skills_covered: string[];
  covered_personalized_skills?: string[];
  description?: string;
  duration?: string;
  enrollment_url?: string;
}

export interface JobSubmission {
  company_name: string;
  contact_information?: string;
  industry?: string;
  job_title: string;
  location?: string;
  required_skills?: string | string[];
  missing_candidate_skills?: string | string[];
  comments?: string;
}

export interface Job {
  id?: string | number;
  job_id?: string | number;
  title?: string;
  company?: string;
  company_name?: string;
  position?: string;
  job_title?: string;
  location?: string;
  industry?: string;
  description?: string;
  extracted_skills?: Array<{ skill_id: string; confidence_score: number }> | string[];
  skills?: string[];
  confidence_scores?: Record<string, number>;
  created_at?: string;
}

export interface EmployerFeedback {
  id?: number | string;
  employer_id?: number;
  job_title?: string;
  feedback_text?: string;
  comments?: string;
  course_id?: number;
  rating?: number;
  signals?: Array<{ skill_id: string; confidence_score: number; weighted_signal: number }>;
  detected_signals?: Array<{ skill_id: string; confidence_score: number; weighted_signal: number }>;
  hiring_difficulty?: string;
  missing_skills_trend?: string[];
  created_at?: string;
}

export interface EmployerFeedbackCreate {
  comments: string;
  course_id?: number;
  rating?: number;
}

export interface EmployerProfile {
  id: number;
  company_name: string;
  trust_weight: number;
  user_id?: number | null;
  created_at?: string;
}

export interface EmployerProfileCreate {
  company_name: string;
  trust_weight?: number;
}

export interface Recommendation {
  id?: string | number;
  title?: string;
  module?: string;
  action: string;
  rationale?: string;
  target_skills?: string[];
  impact_level?: 'High' | 'Medium' | 'Low' | string;
}

export interface CourseGap {
  course_id: string | number;
  course_title?: string;
  curriculum_gap_score: number;
  market_coverage_percentage: number;
  missing_skills: string[] | Array<{ name: string; market_demand?: number; skill_id?: string }>;
  weak_skills: string[] | Array<{ name: string; current_coverage?: number; skill_id?: string }>;
  recommendations: Recommendation[] | string[];
}

export interface DemandData {
  rank?: number;
  skill_ranking?: number;
  skill_id: string;
  skill_name?: string;
  demand_score: number;
  market_growth_rate?: number | null;
  active_postings_count?: number | null;
  sample_roles?: string[];
}

export interface EvidenceSummary {
  skill_id: string;
  total_artifacts?: number;
  total_evidence_artifacts?: number;
  advanced_count: number;
  intermediate_count: number;
  basic_count: number;
  confidence_distribution?: {
    advanced: number;
    intermediate: number;
    basic: number;
  };
  primary_evidence_types?: string[];
  employer_signal_weight: number;
  top_repositories?: string[];
  last_analyzed?: string;
}

export interface SkillExtractionItem {
  skill_id: string;
  confidence_score: number;
}

export interface SkillExtractionResponse {
  skills: SkillExtractionItem[];
}

export interface ApiFastApiErrorDetail {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
}

export interface ApiErrorResponse {
  detail?: string | ApiFastApiErrorDetail[];
  message?: string;
}
