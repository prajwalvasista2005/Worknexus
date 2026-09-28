import { apiClient } from './client';
import { Role, TargetRoleCreate } from '../types';

export const rolesApi = {
  /**
   * Load available target career roles
   * GET /api/v1/roles/
   */
  async getRoles(): Promise<Role[]> {
    return apiClient.get<Role[]>('/api/v1/roles/');
  },

  /**
   * Retrieve a specific target career role and its required skills
   * GET /api/v1/roles/{role_id}
   */
  async getRole(roleId: string): Promise<Role> {
    return apiClient.get<Role>(`/api/v1/roles/${encodeURIComponent(roleId)}`);
  },

  /**
   * Create a new target career role with required skills (Admin only)
   * POST /api/v1/roles/
   */
  async createRole(roleData: TargetRoleCreate): Promise<Role> {
    return apiClient.post<Role>('/api/v1/roles/', roleData);
  },
};
