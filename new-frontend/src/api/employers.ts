import { apiClient } from './client';
import { EmployerFeedback, EmployerFeedbackCreate, EmployerProfile, EmployerProfileCreate } from '../types';

export const employersApi = {
  /**
   * Submit structured employer curriculum & skill feedback
   * POST /api/v1/employers/feedback
   */
  async submitFeedback(
    feedback: EmployerFeedbackCreate | (Partial<EmployerFeedback> & Record<string, unknown>)
  ): Promise<EmployerFeedback> {
    return apiClient.post<EmployerFeedback>('/api/v1/employers/feedback', feedback);
  },

  /**
   * Retrieve list of submitted employer feedbacks
   * GET /api/v1/employers/feedback
   */
  async getFeedback(): Promise<EmployerFeedback[]> {
    return apiClient.get<EmployerFeedback[]>('/api/v1/employers/feedback');
  },

  /**
   * Retrieve current authenticated employer profile
   * GET /api/v1/employers/profile
   */
  async getProfile(): Promise<EmployerProfile> {
    return apiClient.get<EmployerProfile>('/api/v1/employers/profile');
  },

  /**
   * Create or update current authenticated employer profile
   * POST /api/v1/employers/profile
   */
  async createOrUpdateProfile(profile: EmployerProfileCreate): Promise<EmployerProfile> {
    return apiClient.post<EmployerProfile>('/api/v1/employers/profile', profile);
  },

  /**
   * Retrieve employer profile by user ID
   * GET /api/v1/employers/{user_id}/profile
   */
  async getProfileByUserId(userId: number | string): Promise<EmployerProfile> {
    return apiClient.get<EmployerProfile>(`/api/v1/employers/${userId}/profile`);
  },
};
