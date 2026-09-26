import { apiClient } from './client';
import { EmployerFeedback, EmployerFeedbackCreate } from '../types';

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
};
