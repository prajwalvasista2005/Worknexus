import { apiClient } from './client';
import {
  CourseCandidate,
  CourseGap,
  DemandData,
  EvidenceSummary,
  SkillExtractionResponse,
  StudentGap,
} from '../types';

export const mlApi = {
  /**
   * Extract canonical skills from free-form text using ML entity extractor
   * POST /api/v1/ml/extract-skills
   */
  async extractSkills(text: string): Promise<SkillExtractionResponse> {
    return apiClient.post<SkillExtractionResponse>('/api/v1/ml/extract-skills', { text });
  },

  /**
   * Fetch top labour-market skill demand rankings
   * GET /api/v1/ml/demand?top_n=12
   */
  async getDemandData(topN = 12, mode = 'live'): Promise<DemandData[]> {
    const res = await apiClient.get<any>(`/api/v1/ml/demand?top_n=${topN}&mode=${mode}`);
    if (Array.isArray(res)) return res;
    if (res && Array.isArray(res.top_skills)) return res.top_skills;
    if (res && Array.isArray(res.demands)) return res.demands;
    return [];
  },

  /**
   * Retrieve curriculum skill gap intelligence across all courses
   * GET /api/v1/ml/course-gaps
   */
  async getAllCourseGaps(mode = 'live'): Promise<any> {
    return apiClient.get<any>(`/api/v1/ml/course-gaps?mode=${mode}`);
  },

  /**
   * Analyze curriculum alignment and market gaps for a specific course
   * GET /api/v1/ml/course-gaps/{course_id}
   */
  async getCourseGaps(courseId: string | number, mode = 'live'): Promise<CourseGap> {
    return apiClient.get<CourseGap>(`/api/v1/ml/course-gaps/${courseId}?mode=${mode}`);
  },

  /**
   * Retrieve multi-signal evidence intelligence dataset
   * GET /api/v1/ml/evidence
   */
  async getEvidence(mode = 'live'): Promise<any> {
    return apiClient.get<any>(`/api/v1/ml/evidence?mode=${mode}`);
  },

  /**
   * Fetch detailed evidence breakdown for a specific skill
   * GET /api/v1/ml/evidence-summary/{skill_id}
   */
  async getEvidenceSummary(skillId: string, mode = 'live'): Promise<EvidenceSummary> {
    return apiClient.get<EvidenceSummary>(
      `/api/v1/ml/evidence-summary/${encodeURIComponent(skillId)}?mode=${mode}`
    );
  },

  /**
   * Retrieve generic labour market skill recommendations
   * GET /api/v1/ml/recommendations
   */
  async getRecommendations(mode = 'live', threshold?: number): Promise<any> {
    const qs = threshold !== undefined ? `&threshold=${threshold}` : '';
    return apiClient.get<any>(`/api/v1/ml/recommendations?mode=${mode}${qs}`);
  },

  /**
   * Retrieve role contextual skill recommendations
   * GET /api/v1/ml/roles/{role_id}
   */
  async getRoleContext(roleId: string, mode = 'live'): Promise<any> {
    return apiClient.get<any>(`/api/v1/ml/roles/${encodeURIComponent(roleId)}?mode=${mode}`);
  },

  /**
   * Retrieve student ML skill profile
   * GET /api/v1/ml/students/{student_id}/profile
   */
  async getStudentProfile(studentId: string | number, mode = 'live'): Promise<any> {
    return apiClient.get<any>(`/api/v1/ml/students/${studentId}/profile?mode=${mode}`);
  },

  /**
   * Calculate student readiness gap for a specific target role
   * GET /api/v1/ml/students/{student_id}/gap/{role_id}
   */
  async getStudentGap(
    studentId: string | number,
    roleId: string | number,
    mode = 'live'
  ): Promise<StudentGap> {
    return apiClient.get<StudentGap>(`/api/v1/ml/students/${studentId}/gap/${roleId}?mode=${mode}`);
  },

  /**
   * Retrieve personalized skill recommendations bridging student's role gap
   * GET /api/v1/ml/students/{student_id}/recommendations/{role_id}
   */
  async getStudentRecommendations(
    studentId: string | number,
    roleId: string | number,
    mode = 'live'
  ): Promise<any> {
    return apiClient.get<any>(
      `/api/v1/ml/students/${studentId}/recommendations/${roleId}?mode=${mode}`
    );
  },

  /**
   * Recommend candidate courses bridging the student's role gap
   * GET /api/v1/ml/students/{student_id}/course-candidates/{role_id}
   */
  async getCourseCandidates(
    studentId: string | number,
    roleId: string | number,
    mode = 'live'
  ): Promise<CourseCandidate[]> {
    const res = await apiClient.get<any>(
      `/api/v1/ml/students/${studentId}/course-candidates/${roleId}?mode=${mode}`
    );
    if (Array.isArray(res)) return res;
    if (res && Array.isArray(res.candidate_courses)) return res.candidate_courses;
    return [];
  },
};
