import { apiClient } from './client';
import {
  Job,
  JobSubmission,
  JobPosting,
  JobPostingCreate,
  JobSkill,
  JobSkillCreate,
} from '../types';

export const jobsApi = {
  /**
   * Submit job demand requisition with ML skill extraction
   * POST /api/v1/jobs/
   */
  async submitJob(jobData: JobSubmission): Promise<Job> {
    return apiClient.post<Job>('/api/v1/jobs/', jobData);
  },

  /**
   * List submitted jobs
   * GET /api/v1/jobs/
   */
  async getJobs(): Promise<Job[]> {
    return apiClient.get<Job[]>('/api/v1/jobs/');
  },

  /**
   * Get single job by ID
   * GET /api/v1/jobs/{job_id}
   */
  async getJob(jobId: number | string): Promise<Job> {
    return apiClient.get<Job>(`/api/v1/jobs/${jobId}`);
  },

  /**
   * Delete a job posting from jobs router
   * DELETE /api/v1/jobs/{job_id}
   */
  async deleteJob(jobId: number | string): Promise<{ message: string }> {
    try {
      return await apiClient.delete<{ message: string }>(`/api/v1/jobs/${jobId}`);
    } catch {
      return await apiClient.delete<{ message: string }>(`/api/v1/job-postings/${jobId}`);
    }
  },

  // -------------------------------------------------------------
  // JOB POSTINGS CRUD
  // -------------------------------------------------------------

  /**
   * List all canonical job postings
   * GET /api/v1/job-postings
   */
  async getJobPostings(skip = 0, limit = 100): Promise<JobPosting[]> {
    return apiClient.get<JobPosting[]>(`/api/v1/job-postings?skip=${skip}&limit=${limit}`);
  },

  /**
   * Get single job posting by ID
   * GET /api/v1/job-postings/{job_id}
   */
  async getJobPosting(jobId: number | string): Promise<JobPosting> {
    return apiClient.get<JobPosting>(`/api/v1/job-postings/${jobId}`);
  },

  /**
   * Create a job posting
   * POST /api/v1/job-postings
   */
  async createJobPosting(data: JobPostingCreate): Promise<JobPosting> {
    return apiClient.post<JobPosting>('/api/v1/job-postings', data);
  },

  /**
   * Delete a job posting
   * DELETE /api/v1/job-postings/{job_id}
   */
  async deleteJobPosting(jobId: number | string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/v1/job-postings/${jobId}`);
  },

  // -------------------------------------------------------------
  // JOB SKILLS MAPPINGS
  // -------------------------------------------------------------

  /**
   * List job skill mappings
   * GET /api/v1/job-skills
   */
  async getJobSkills(jobId?: number, skillId?: string): Promise<JobSkill[]> {
    const query = new URLSearchParams();
    if (jobId) query.append('job_id', String(jobId));
    if (skillId) query.append('skill_id', skillId);
    const qs = query.toString();
    return apiClient.get<JobSkill[]>(`/api/v1/job-skills${qs ? `?${qs}` : ''}`);
  },

  /**
   * Get specific job skill mapping by ID
   * GET /api/v1/job-skills/{job_skill_id}
   */
  async getJobSkill(id: number | string): Promise<JobSkill> {
    return apiClient.get<JobSkill>(`/api/v1/job-skills/${id}`);
  },

  /**
   * Map skill to a job posting
   * POST /api/v1/job-skills
   */
  async mapJobSkill(data: JobSkillCreate): Promise<JobSkill> {
    return apiClient.post<JobSkill>('/api/v1/job-skills', data);
  },

  /**
   * Remove skill mapping from a job posting
   * DELETE /api/v1/job-skills/{job_skill_id}
   */
  async deleteJobSkill(id: number | string): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/api/v1/job-skills/${id}`);
  },
};
