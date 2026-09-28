import { apiClient } from './client';
import {
  Skill,
  SkillCreate,
  SkillUpdate,
  UserSkill,
  UserSkillCreate,
  UserSkillUpdate,
} from '../types';

export const skillsApi = {
  /**
   * Retrieve catalog skills with optional category/active filter
   * GET /api/v1/skills/
   */
  async getSkills(category?: string, isActive?: boolean): Promise<Skill[]> {
    const query = new URLSearchParams();
    if (category) query.append('category', category);
    if (isActive !== undefined) query.append('is_active', String(isActive));
    const qs = query.toString();
    return apiClient.get<Skill[]>(`/api/v1/skills/${qs ? `?${qs}` : ''}`);
  },

  /**
   * Get skill by ID or code
   * GET /api/v1/skills/{skill_id}
   */
  async getSkill(skillId: string | number): Promise<Skill> {
    return apiClient.get<Skill>(`/api/v1/skills/${encodeURIComponent(String(skillId))}`);
  },

  /**
   * Create a new skill in the catalog
   * POST /api/v1/skills/
   */
  async createSkill(skillData: SkillCreate): Promise<Skill> {
    return apiClient.post<Skill>('/api/v1/skills/', skillData);
  },

  /**
   * Update skill details
   * PUT /api/v1/skills/{skill_id}
   */
  async updateSkill(skillId: number | string, skillData: SkillUpdate): Promise<Skill> {
    return apiClient.put<Skill>(`/api/v1/skills/${skillId}`, skillData);
  },

  /**
   * Delete skill by ID
   * DELETE /api/v1/skills/{skill_id}
   */
  async deleteSkill(skillId: number | string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/v1/skills/${skillId}`);
  },

  // -------------------------------------------------------------
  // USER SKILLS CRUD
  // -------------------------------------------------------------

  /**
   * Get authenticated student's user skills
   * GET /api/v1/user-skills/me
   */
  async getMySkills(): Promise<UserSkill[]> {
    return apiClient.get<UserSkill[]>('/api/v1/user-skills/me');
  },

  /**
   * List user skills (optionally filter by user_id)
   * GET /api/v1/user-skills/
   */
  async getUserSkills(userId?: number | string): Promise<UserSkill[]> {
    const qs = userId ? `?user_id=${userId}` : '';
    return apiClient.get<UserSkill[]>(`/api/v1/user-skills/${qs}`);
  },

  /**
   * Get specific user skill record by ID
   * GET /api/v1/user-skills/{id}
   */
  async getUserSkill(id: number | string): Promise<UserSkill> {
    return apiClient.get<UserSkill>(`/api/v1/user-skills/${id}`);
  },

  /**
   * Add a skill to the authenticated user's profile
   * POST /api/v1/user-skills/
   */
  async addUserSkill(skillData: UserSkillCreate): Promise<UserSkill> {
    return apiClient.post<UserSkill>('/api/v1/user-skills/', skillData);
  },

  /**
   * Update proficiency level or source of a user skill
   * PUT /api/v1/user-skills/{id}
   */
  async updateUserSkill(id: number | string, data: UserSkillUpdate): Promise<UserSkill> {
    return apiClient.put<UserSkill>(`/api/v1/user-skills/${id}`, data);
  },

  /**
   * Remove a skill from user profile
   * DELETE /api/v1/user-skills/{id}
   */
  async deleteUserSkill(id: number | string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/v1/user-skills/${id}`);
  },
};
