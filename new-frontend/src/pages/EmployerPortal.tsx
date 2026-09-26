import React, { useState, useEffect, useCallback } from 'react';
import { PortalLayout } from '../components/layout/PortalLayout';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { jobsApi } from '../api/jobs';
import { employersApi } from '../api/employers';
import { Job, JobSubmission, EmployerFeedback } from '../types';
import { formatPercentage, formatDate } from '../utils/formatters';
import {
  Building2,
  Briefcase,
  MapPin,
  Mail,
  Tag,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Send,
  MessageSquarePlus,
  Sparkles,
  Layers,
  FileCheck,
  Trash2,
  History,
  ListFilter,
  CheckCircle,
} from 'lucide-react';

export const EmployerPortal: React.FC = () => {
  const { user } = useAuth();
  const { showToast } = useToast();

  // Navigation & Lists State
  const [activeTab, setActiveTab] = useState<'submit' | 'jobs' | 'feedbacks'>('submit');
  const [jobsList, setJobsList] = useState<Job[]>([]);
  const [feedbackList, setFeedbackList] = useState<EmployerFeedback[]>([]);
  const [isLoadingJobsList, setIsLoadingJobsList] = useState(false);
  const [isLoadingFeedbackList, setIsLoadingFeedbackList] = useState(false);

  // Job Submission Form State
  const [companyName, setCompanyName] = useState('');
  const [contactInfo, setContactInfo] = useState(user?.email || '');
  const [industry, setIndustry] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [location, setLocation] = useState('');
  const [requiredSkills, setRequiredSkills] = useState('');
  const [missingSkills, setMissingSkills] = useState('');
  const [comments, setComments] = useState('');

  const [isSubmittingJob, setIsSubmittingJob] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);
  const [submittedJobResult, setSubmittedJobResult] = useState<Job | null>(null);

  // Feedback Form State
  const [feedbackJobTitle, setFeedbackJobTitle] = useState('');
  const [feedbackComments, setFeedbackComments] = useState('');
  const [hiringDifficulty, setHiringDifficulty] = useState('Moderate');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  // Handle Job Demand Submission
  const handleJobSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName || !jobTitle || !location || !requiredSkills) {
      showToast('Please fill in all mandatory job requisition fields.', 'warning');
      return;
    }

    setIsSubmittingJob(true);
    setJobError(null);

    // Split comma-separated skills into array or formatted string
    const reqSkillsArr = requiredSkills
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const missSkillsArr = missingSkills
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const payload: JobSubmission = {
      company_name: companyName,
      contact_information: contactInfo,
      industry: industry || 'Technology',
      job_title: jobTitle,
      location,
      required_skills: reqSkillsArr,
      missing_candidate_skills: missSkillsArr,
      comments,
    };

    try {
      const response = await jobsApi.submitJob(payload);
      setSubmittedJobResult(response);
      showToast('Job demand successfully submitted and extracted by ML!', 'success');
      await fetchJobsList();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit job demand requisition.';
      setJobError(msg);
      showToast(msg, 'error');
    } finally {
      setIsSubmittingJob(false);
    }
  };

  // Handle Employer Feedback Submission
  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackComments) {
      showToast('Please write your curriculum feedback or observations.', 'warning');
      return;
    }

    setIsSubmittingFeedback(true);
    setFeedbackError(null);
    setFeedbackSuccess(false);

    try {
      await employersApi.submitFeedback({
        job_title: feedbackJobTitle || jobTitle || 'General',
        comments: feedbackComments,
        feedback_text: feedbackComments,
        hiring_difficulty: hiringDifficulty,
      });

      setFeedbackSuccess(true);
      showToast('Employer feedback registered with curriculum models.', 'success');
      setFeedbackComments('');
      await fetchFeedbackList();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to register employer feedback.';
      setFeedbackError(msg);
      showToast(msg, 'error');
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const fetchJobsList = useCallback(async () => {
    setIsLoadingJobsList(true);
    try {
      const data = await jobsApi.getJobs();
      setJobsList(data || []);
    } catch {
      // optional
    } finally {
      setIsLoadingJobsList(false);
    }
  }, []);

  const fetchFeedbackList = useCallback(async () => {
    setIsLoadingFeedbackList(true);
    try {
      const data = await employersApi.getFeedback();
      setFeedbackList(data || []);
    } catch {
      // optional
    } finally {
      setIsLoadingFeedbackList(false);
    }
  }, []);

  useEffect(() => {
    fetchJobsList();
    fetchFeedbackList();
  }, [fetchJobsList, fetchFeedbackList]);

  const handleDeleteJob = async (jobId: string | number) => {
    try {
      await jobsApi.deleteJob(jobId);
      showToast('Job demand requisition deleted.', 'info');
      await fetchJobsList();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete job.';
      showToast(msg, 'error');
    }
  };

  return (
    <PortalLayout activeRole="Employer">
      <div className="space-y-8">
        {/* Header Banner */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">
                Employer Talent Requisition & Signal Hub
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                Labour Demand & Curriculum Feedback
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Broadcast current enterprise skill requirements directly to workforce education institutes.
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
          <button
            type="button"
            onClick={() => setActiveTab('submit')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
              activeTab === 'submit'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50'
            }`}
          >
            Submit Demand & Feedback
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('jobs');
              fetchJobsList();
            }}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'jobs'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50'
            }`}
          >
            <span>Active Requisitions</span>
            <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded-full font-bold">
              {jobsList.length}
            </span>
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('feedbacks');
              fetchFeedbackList();
            }}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'feedbacks'
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50'
            }`}
          >
            <span>Feedback History</span>
            <span className="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded-full font-bold">
              {feedbackList.length}
            </span>
          </button>
        </div>

        {activeTab === 'submit' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Main Job Demand Submission Form */}
          <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100 mb-6">
              <Briefcase className="w-5 h-5 text-indigo-600" />
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  Submit Enterprise Job Demand
                </h2>
                <p className="text-xs text-slate-500">
                  ML models will parse required qualifications and missing talent skills.
                </p>
              </div>
            </div>

            {jobError && (
              <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1 leading-snug">{jobError}</div>
              </div>
            )}

            <form onSubmit={handleJobSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="companyName"
                    className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                  >
                    Company Name *
                  </label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                    <input
                      id="companyName"
                      type="text"
                      required
                      placeholder="e.g. Acme Cloud Corp"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className="block w-full pl-9 pr-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="contactInfo"
                    className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                  >
                    Contact Email / Info *
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                    <input
                      id="contactInfo"
                      type="text"
                      required
                      placeholder="hiring@acme.com"
                      value={contactInfo}
                      onChange={(e) => setContactInfo(e.target.value)}
                      className="block w-full pl-9 pr-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="industry"
                    className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                  >
                    Industry Sector
                  </label>
                  <input
                    id="industry"
                    type="text"
                    placeholder="e.g. Software, Fintech, Healthcare"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="block w-full px-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label
                    htmlFor="jobTitle"
                    className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                  >
                    Job Title / Position *
                  </label>
                  <input
                    id="jobTitle"
                    type="text"
                    required
                    placeholder="e.g. Senior Backend Engineer"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    className="block w-full px-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="location"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                >
                  District / Location *
                </label>
                <div className="relative">
                  <MapPin className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                  <input
                    id="location"
                    type="text"
                    required
                    placeholder="e.g. London Metro / Remote"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="block w-full pl-9 pr-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="requiredSkills"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                >
                  Required Core Skills (comma-separated) *
                </label>
                <div className="relative">
                  <Tag className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                  <input
                    id="requiredSkills"
                    type="text"
                    required
                    placeholder="e.g. Python, Docker, Kubernetes, PostgreSQL"
                    value={requiredSkills}
                    onChange={(e) => setRequiredSkills(e.target.value)}
                    className="block w-full pl-9 pr-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <p className="mt-1 text-[11px] text-slate-400">
                  Enter key technical skills, tools, or frameworks required for candidate screening.
                </p>
              </div>

              <div>
                <label
                  htmlFor="missingSkills"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                >
                  Observed Missing Candidate Skills (comma-separated)
                </label>
                <input
                  id="missingSkills"
                  type="text"
                  placeholder="e.g. System design, Async programming, CI/CD"
                  value={missingSkills}
                  onChange={(e) => setMissingSkills(e.target.value)}
                  className="block w-full px-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                />
                <p className="mt-1 text-[11px] text-slate-400">
                  Specific gaps observed in candidate interviews or recent applicant pools.
                </p>
              </div>

              <div>
                <label
                  htmlFor="comments"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                >
                  Requisition Comments & Curriculum Context
                </label>
                <textarea
                  id="comments"
                  rows={3}
                  placeholder="Provide additional details regarding team stack, projects, or specific requirements..."
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="block w-full px-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmittingJob}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-60 cursor-pointer"
              >
                {isSubmittingJob ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing Requisition & ML Extraction...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Submit Job Demand</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Right Column: Returned Job Extraction & Feedback Form */}
          <div className="lg:col-span-5 space-y-6">
            {/* Real Submission Results Card */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-5 h-5 text-emerald-600" />
                  <h3 className="text-sm font-bold text-slate-900">
                    Latest Submission State
                  </h3>
                </div>
                {submittedJobResult && (
                  <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                    Requisition Verified
                  </span>
                )}
              </div>

              {!submittedJobResult ? (
                <div className="text-center py-8">
                  <Layers className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs font-medium text-slate-600">
                    No active job submission in current session.
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1 max-w-xs mx-auto">
                    Submit the form on the left to view parsed job metadata, extracted skills, and confidence scores.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="p-3.5 bg-emerald-50/60 border border-emerald-200 rounded-xl">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="font-semibold text-emerald-900">
                        {submittedJobResult.position || submittedJobResult.job_title || jobTitle}
                      </span>
                      <span className="font-mono text-emerald-700 text-[11px]">
                        ID: {submittedJobResult.job_id || submittedJobResult.id || 'N/A'}
                      </span>
                    </div>
                    <div className="text-[11px] text-emerald-800">
                      <span>{submittedJobResult.company || submittedJobResult.company_name || companyName}</span>
                      <span aria-hidden="true" className="mx-1.5">·</span>
                      <span>{submittedJobResult.location || location}</span>
                    </div>
                  </div>

                  {/* Extracted Skills */}
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                      Automatically Extracted Skills
                    </span>

                    {submittedJobResult.extracted_skills && submittedJobResult.extracted_skills.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {submittedJobResult.extracted_skills.map((skill, sIdx) => {
                          const skillLabel = (() => {
                            if (typeof skill === 'string') return skill;

                            if (skill && typeof skill === 'object') {
                              const maybeSkill = skill as { skill_id?: unknown; name?: unknown };

                              if (typeof maybeSkill.skill_id === 'string') return maybeSkill.skill_id;
                              if (typeof maybeSkill.name === 'string') return maybeSkill.name;
                            }

                            return 'Unknown skill';
                          })();

                          return (
                            <span
                              key={sIdx}
                              className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-100 px-2.5 py-1 rounded-lg font-medium"
                            >
                              {skillLabel}
                            </span>
                          );
                        })}
                      </div>
                    ) : submittedJobResult.skills && submittedJobResult.skills.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {submittedJobResult.skills.map((skill, sIdx) => {
                          const skillLabel = (() => {
                            if (typeof skill === 'string') return skill;

                            if (skill && typeof skill === 'object') {
                              const maybeSkill = skill as { skill_id?: unknown; name?: unknown };

                              if (typeof maybeSkill.skill_id === 'string') return maybeSkill.skill_id;
                              if (typeof maybeSkill.name === 'string') return maybeSkill.name;
                            }

                            return 'Unknown skill';
                          })();

                          return (
                            <span
                              key={sIdx}
                              className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-100 px-2.5 py-1 rounded-lg font-medium"
                            >
                              {skillLabel}
                            </span>
                          );
                        })}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">
                        No distinct skills returned by NLP extractor.
                      </span>
                    )}
                  </div>

                  {/* Confidence Scores */}
                  {submittedJobResult.confidence_scores &&
                    Object.keys(submittedJobResult.confidence_scores).length > 0 && (
                      <div>
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                          ML Extraction Confidence Scores
                        </span>
                        <div className="space-y-1.5">
                          {Object.entries(submittedJobResult.confidence_scores).map(([sk, conf]) => (
                            <div
                              key={sk}
                              className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-50 border border-slate-100"
                            >
                              <span className="font-medium text-slate-700">{sk}</span>
                              <span className="font-semibold text-slate-900 tabular-nums">
                                {formatPercentage(conf)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              )}
            </div>

            {/* Employer Feedback Form */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-100 mb-4">
                <MessageSquarePlus className="w-5 h-5 text-indigo-600" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Employer Labour Feedback
                  </h3>
                  <p className="text-xs text-slate-500">
                    Direct signal feed into curriculum alignment algorithms.
                  </p>
                </div>
              </div>

              {feedbackSuccess && (
                <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Feedback successfully submitted to workforce databases!</span>
                </div>
              )}

              {feedbackError && (
                <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                  <span>{feedbackError}</span>
                </div>
              )}

              <form onSubmit={handleFeedbackSubmit} className="space-y-3">
                <div>
                  <label
                    htmlFor="feedbackJobTitle"
                    className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                  >
                    Target Position / Domain
                  </label>
                  <input
                    id="feedbackJobTitle"
                    type="text"
                    placeholder={jobTitle || 'e.g. Full Stack Developer'}
                    value={feedbackJobTitle}
                    onChange={(e) => setFeedbackJobTitle(e.target.value)}
                    className="block w-full px-3 py-1.5 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label
                    htmlFor="hiringDifficulty"
                    className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                  >
                    Hiring Difficulty
                  </label>
                  <select
                    id="hiringDifficulty"
                    value={hiringDifficulty}
                    onChange={(e) => setHiringDifficulty(e.target.value)}
                    className="block w-full px-3 py-1.5 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Low">Low - Adequate candidate readiness</option>
                    <option value="Moderate">Moderate - Minor curriculum gaps</option>
                    <option value="Severe">Severe - Critical shortage of required skills</option>
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="feedbackComments"
                    className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
                  >
                    Qualitative Observations *
                  </label>
                  <textarea
                    id="feedbackComments"
                    required
                    rows={3}
                    placeholder="Describe specific curriculum deficits, practical engineering readiness shortcomings, or emerging tools needed..."
                    value={feedbackComments}
                    onChange={(e) => setFeedbackComments(e.target.value)}
                    className="block w-full px-3 py-1.5 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmittingFeedback}
                  className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-60 cursor-pointer"
                >
                  {isSubmittingFeedback ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Sending Signal...</span>
                    </>
                  ) : (
                    <span>Submit Feedback Signal</span>
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
        )}

        {/* Active Requisitions Tab Panel */}
        {activeTab === 'jobs' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-6">
              <div>
                <div className="flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-indigo-600" />
                  <h2 className="text-lg font-bold text-slate-900">
                    Active Employer Requisitions & Extracted Skills
                  </h2>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Requisitions parsed by the NLP ML engine and indexed into the workforce demand database.
                </p>
              </div>
              <button
                type="button"
                onClick={fetchJobsList}
                className="px-3 py-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-semibold bg-indigo-50 border border-indigo-100 rounded-lg hover:bg-indigo-100 transition-colors"
              >
                Refresh Requisitions
              </button>
            </div>

            {isLoadingJobsList ? (
              <div className="space-y-3">
                <div className="h-24 bg-slate-100 animate-pulse rounded-xl" />
                <div className="h-24 bg-slate-100 animate-pulse rounded-xl" />
              </div>
            ) : jobsList.length === 0 ? (
              <div className="text-center py-12">
                <Briefcase className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-700">No active job requisitions found</p>
                <p className="text-xs text-slate-400 mt-1">Submit your first requisition using the form tab above.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {jobsList.map((job, idx) => (
                  <div
                    key={job.id || job.job_id || idx}
                    className="p-5 rounded-xl border border-slate-200 bg-white hover:border-indigo-200 transition-colors flex flex-col md:flex-row md:items-start justify-between gap-4"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-sm font-bold text-slate-900">
                          {job.title || job.job_title || 'Engineering Role'}
                        </h3>
                        <span className="text-[11px] font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full">
                          {job.company || job.company_name || 'Enterprise Partner'}
                        </span>
                        {job.location && (
                          <span className="text-[11px] text-slate-500 flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-slate-400" />
                            {job.location}
                          </span>
                        )}
                      </div>

                      {job.description && (
                        <p className="text-xs text-slate-600 mt-2 line-clamp-2 leading-relaxed">
                          {job.description}
                        </p>
                      )}

                      {/* Extracted Skills */}
                      <div className="mt-3">
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                          ML Extracted Skills:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {job.extracted_skills && job.extracted_skills.length > 0 ? (
                            job.extracted_skills.map((skill, sIdx) => {
                              const sId = typeof skill === 'string' ? skill : skill.skill_id;
                              const conf = typeof skill === 'object' && skill.confidence_score ? skill.confidence_score : null;
                              return (
                                <span
                                  key={sIdx}
                                  className="inline-flex items-center gap-1 text-[11px] font-medium bg-slate-100 text-slate-800 px-2.5 py-0.5 rounded-md"
                                >
                                  <span>{sId}</span>
                                  {conf !== null && (
                                    <span className="text-[10px] font-bold text-indigo-600 tabular-nums">
                                      {Math.round(conf * 100)}%
                                    </span>
                                  )}
                                </span>
                              );
                            })
                          ) : (
                            <span className="text-xs text-slate-400 italic">No skills extracted yet</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {job.id !== undefined && (
                      <button
                        type="button"
                        onClick={() => handleDeleteJob(job.id!)}
                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer self-start"
                        title="Delete Requisition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Feedback History Tab Panel */}
        {activeTab === 'feedbacks' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-6">
              <div>
                <div className="flex items-center gap-2">
                  <History className="w-5 h-5 text-indigo-600" />
                  <h2 className="text-lg font-bold text-slate-900">
                    Employer Qualitative Feedback History
                  </h2>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Audit trail of observations submitted to calibrate curriculum training weights.
                </p>
              </div>
              <button
                type="button"
                onClick={fetchFeedbackList}
                className="px-3 py-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-semibold bg-indigo-50 border border-indigo-100 rounded-lg hover:bg-indigo-100 transition-colors"
              >
                Refresh Feedback
              </button>
            </div>

            {isLoadingFeedbackList ? (
              <div className="space-y-3">
                <div className="h-20 bg-slate-100 animate-pulse rounded-xl" />
                <div className="h-20 bg-slate-100 animate-pulse rounded-xl" />
              </div>
            ) : feedbackList.length === 0 ? (
              <div className="text-center py-12">
                <History className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-700">No feedback entries recorded</p>
                <p className="text-xs text-slate-400 mt-1">Submit feedback observations in the main tab to calibrate curriculum.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {feedbackList.map((fb, idx) => (
                  <div key={fb.id || idx} className="py-4 first:pt-0 last:pb-0">
                    <div className="flex items-center justify-between gap-4 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900">
                          {fb.job_title || 'General Curriculum Observation'}
                        </span>
                        {fb.hiring_difficulty && (
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                            fb.hiring_difficulty === 'Severe'
                              ? 'bg-red-50 text-red-700'
                              : fb.hiring_difficulty === 'Moderate'
                              ? 'bg-amber-50 text-amber-700'
                              : 'bg-emerald-50 text-emerald-700'
                          }`}>
                            Difficulty: {fb.hiring_difficulty}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-400 tabular-nums">
                        {formatDate(fb.created_at)}
                      </span>
                    </div>

                    <p className="text-xs text-slate-700 leading-relaxed">
                      {fb.comments || fb.feedback_text}
                    </p>

                    {(fb.signals || fb.detected_signals) && (fb.signals || fb.detected_signals)!.length > 0 && (
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] text-slate-400 font-medium">Detected Signals:</span>
                        {(fb.signals || fb.detected_signals)!.map((sig, sIdx) => (
                          <span key={sIdx} className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
                            {sig.skill_id} ({Math.round(sig.confidence_score * 100)}%)
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </PortalLayout>
  );
};
