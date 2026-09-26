import { apiClient } from './client';
import { Course, CourseCreate, CourseUpdate, CourseSkill, CourseSkillCreate } from '../types';

export const coursesApi = {
  /**
   * List curriculum courses with optional filtering
   * GET /api/v1/courses/
   */
  async getCourses(params?: { department?: string; is_active?: boolean; skip?: number; limit?: number }): Promise<Course[]> {
    const query = new URLSearchParams();
    if (params?.department) query.append('department', params.department);
    if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    const qs = query.toString();
    return apiClient.get<Course[]>(`/api/v1/courses/${qs ? `?${qs}` : ''}`);
  },

  /**
   * Get single course by internal integer ID
   * GET /api/v1/courses/{id}
   */
  async getCourse(id: number | string): Promise<Course> {
    return apiClient.get<Course>(`/api/v1/courses/${id}`);
  },

  /**
   * Create a new course
   * POST /api/v1/courses/
   */
  async createCourse(courseData: CourseCreate): Promise<Course> {
    const payload = {
      ...courseData,
      course_id: courseData.course_id || courseData.course_code || '',
    };
    return apiClient.post<Course>('/api/v1/courses/', payload);
  },

  /**
   * Update an existing course
   * PUT /api/v1/courses/{id}
   */
  async updateCourse(id: number | string, courseData: CourseUpdate): Promise<Course> {
    return apiClient.put<Course>(`/api/v1/courses/${id}`, courseData);
  },

  /**
   * Delete course by ID
   * DELETE /api/v1/courses/{id}
   */
  async deleteCourse(id: number | string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/v1/courses/${id}`);
  },

  /**
   * Get all skills associated with a course
   * GET /api/v1/courses/{id}/skills
   */
  async getCourseSkills(id: number | string): Promise<CourseSkill[]> {
    return apiClient.get<CourseSkill[]>(`/api/v1/courses/${id}/skills`);
  },

  /**
   * List course-skill mappings
   * GET /api/v1/course-skills/
   */
  async getAllCourseSkills(courseId?: number, skillId?: number): Promise<CourseSkill[]> {
    const query = new URLSearchParams();
    if (courseId) query.append('course_id', String(courseId));
    if (skillId) query.append('skill_id', String(skillId));
    const qs = query.toString();
    return apiClient.get<CourseSkill[]>(`/api/v1/course-skills/${qs ? `?${qs}` : ''}`);
  },

  /**
   * Get course-skill mappings for a specific course
   * GET /api/v1/course-skills/course/{course_id}
   */
  async getCourseSkillsByCourse(courseId: number | string): Promise<CourseSkill[]> {
    return apiClient.get<CourseSkill[]>(`/api/v1/course-skills/course/${courseId}`);
  },

  /**
   * Get specific course-skill mapping by ID
   * GET /api/v1/course-skills/{id}
   */
  async getCourseSkill(id: number | string): Promise<CourseSkill> {
    return apiClient.get<CourseSkill>(`/api/v1/course-skills/${id}`);
  },

  /**
   * Map a skill to a course
   * POST /api/v1/course-skills/
   */
  async addSkillToCourse(mapping: CourseSkillCreate): Promise<CourseSkill> {
    return apiClient.post<CourseSkill>('/api/v1/course-skills/', mapping);
  },

  /**
   * Remove a skill mapping from a course
   * DELETE /api/v1/course-skills/{id}
   */
  async deleteCourseSkill(id: number | string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/v1/course-skills/${id}`);
  },

  /**
   * Directly link a skill to a course
   * POST /api/v1/courses/{id}/skills
   */
  async addSkillDirect(courseId: number | string, skillId: number, relevanceScore = 1.0): Promise<CourseSkill> {
    return apiClient.post<CourseSkill>(`/api/v1/courses/${courseId}/skills`, {
      skill_id: skillId,
      relevance_score: relevanceScore,
    });
  },

  /**
   * Directly unlink a skill from a course
   * DELETE /api/v1/courses/{id}/skills/{skill_id}
   */
  async removeSkillDirect(courseId: number | string, skillId: number | string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/v1/courses/${courseId}/skills/${skillId}`);
  },
};
