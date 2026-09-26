import { apiClient } from './client';
import {
  SkillEvidence,
  SkillEvidenceSubmission,
  StudentProfile,
  StudentProfileCreate,
} from '../types';

export const studentsApi = {
  /**
   * Fetch submitted skill evidence for a student
   * GET /api/v1/students/{user_id}/evidence
   */
  async getEvidence(userId: string | number): Promise<SkillEvidence[]> {
    return apiClient.get<SkillEvidence[]>(`/api/v1/students/${userId}/evidence`);
  },

  /**
   * Submit new skill evidence for a student
   * POST /api/v1/students/{user_id}/evidence
   */
  async submitEvidence(
    userId: string | number,
    payload: SkillEvidenceSubmission
  ): Promise<SkillEvidence> {
    return apiClient.post<SkillEvidence>(`/api/v1/students/${userId}/evidence`, payload);
  },

  /**
   * Retrieve student profile and associated skill evidence
   * GET /api/v1/students/{user_id}/profile
   */
  async getProfile(userId: string | number): Promise<StudentProfile> {
    return apiClient.get<StudentProfile>(`/api/v1/students/${userId}/profile`);
  },

  /**
   * Create or update student profile target role
   * POST /api/v1/students/profile
   */
  async saveProfile(payload: StudentProfileCreate): Promise<StudentProfile> {
    return apiClient.post<StudentProfile>('/api/v1/students/profile', payload);
  },
};
