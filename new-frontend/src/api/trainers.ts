/**
 * Trainer Intervention API client — Phase 1 Loop D
 *
 * Endpoints
 * ---------
 * POST   /api/v1/trainers/interventions           — create intervention
 * GET    /api/v1/trainers/interventions            — my history
 * GET    /api/v1/trainers/interventions/{student_id} — student history
 */

import { apiClient } from './client';

export interface TrainerInterventionCreate {
  student_id: number;
  skill_id: number;
  intervention_type: string;
  notes?: string;
  proficiency_before?: string;
  proficiency_after?: string;
}

export interface TrainerIntervention {
  id: number;
  trainer_id: number;
  student_id: number;
  skill_id: number;
  skill_name?: string | null;
  skill_code?: string | null;
  intervention_type: string;
  notes?: string | null;
  proficiency_before?: string | null;
  proficiency_after?: string | null;
  is_verified: boolean;
  created_at?: string;
  recalculated_gap?: Record<string, unknown> | null;
}

export const trainerApi = {
  /**
   * Create a new student intervention.
   * POST /api/v1/trainers/interventions
   */
  async createIntervention(
    payload: TrainerInterventionCreate
  ): Promise<TrainerIntervention> {
    return apiClient.post<TrainerIntervention>(
      '/api/v1/trainers/interventions',
      payload
    );
  },

  /**
   * List all interventions created by the authenticated trainer.
   * GET /api/v1/trainers/interventions
   */
  async getMyInterventions(): Promise<TrainerIntervention[]> {
    return apiClient.get<TrainerIntervention[]>('/api/v1/trainers/interventions');
  },

  /**
   * List all interventions received by a specific student.
   * GET /api/v1/trainers/interventions/{student_id}
   */
  async getStudentInterventions(
    studentId: number | string
  ): Promise<TrainerIntervention[]> {
    return apiClient.get<TrainerIntervention[]>(
      `/api/v1/trainers/interventions/${studentId}`
    );
  },
};
