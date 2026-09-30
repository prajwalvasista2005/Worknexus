import React, { useState, useEffect, useCallback } from 'react';
import { PortalLayout } from '../components/layout/PortalLayout';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { coursesApi } from '../api/courses';
import { skillsApi } from '../api/skills';
import { mlApi } from '../api/ml';
import { Course, CourseGap, Recommendation, CourseSkill, Skill } from '../types';
import { CardSkeleton, Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { Alert } from '../components/ui/Alert';
import { formatPercentage } from '../utils/formatters';
import {
  BookOpen,
  PieChart,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  Lightbulb,
  Building,
  Clock,
  Sparkles,
  TrendingDown,
  Layers,
  ChevronRight,
  RefreshCw,
  Plus,
  Trash2,
  X,
  Check,
  Loader2,
} from 'lucide-react';

export const InstitutePortal: React.FC = () => {
  const { user } = useAuth();
  const { showToast } = useToast();

  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [courseGap, setCourseGap] = useState<CourseGap | null>(null);
  const [courseSkills, setCourseSkills] = useState<CourseSkill[]>([]);
  const [catalogSkills, setCatalogSkills] = useState<Skill[]>([]);

  const [isLoadingCourses, setIsLoadingCourses] = useState(true);
  const [isLoadingGap, setIsLoadingGap] = useState(false);
  const [isLoadingCourseSkills, setIsLoadingCourseSkills] = useState(false);
  const [coursesError, setCoursesError] = useState<string | null>(null);
  const [gapError, setGapError] = useState<string | null>(null);

  // Add Course Modal State
  const [isAddCourseModalOpen, setIsAddCourseModalOpen] = useState(false);
  const [newCourseCode, setNewCourseCode] = useState('');
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseDept, setNewCourseDept] = useState('Computer Science');
  const [newCourseDesc, setNewCourseDesc] = useState('');
  const [isCreatingCourse, setIsCreatingCourse] = useState(false);

  // Map Skill State
  const [newSkillToMap, setNewSkillToMap] = useState<string | number>('');
  const [isMappingSkill, setIsMappingSkill] = useState(false);

  // Fetch courses from backend
  const fetchCourses = useCallback(async () => {
    setIsLoadingCourses(true);
    setCoursesError(null);
    try {
      const data = await coursesApi.getCourses();
      setCourses(data || []);
      if (data && data.length > 0) {
        setSelectedCourse(data[0]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve course catalog.';
      setCoursesError(msg);
    } finally {
      setIsLoadingCourses(false);
    }
  }, []);

  useEffect(() => {
    fetchCourses();
  }, [fetchCourses]);

  // When a course is selected, fetch ML course gap analysis
  useEffect(() => {
    if (!selectedCourse) {
      setCourseGap(null);
      return;
    }

    const loadGap = async () => {
      setIsLoadingGap(true);
      setGapError(null);
      try {
        const gap = await mlApi.getCourseGaps(selectedCourse.id);
        setCourseGap(gap);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'No ML gap data available for this course syllabus.';
        setGapError(msg);
        setCourseGap(null);
      } finally {
        setIsLoadingGap(false);
      }
    };

    loadGap();
  }, [selectedCourse]);

  // Fetch catalog skills for mapping selector
  const fetchCatalogSkills = useCallback(async () => {
    try {
      const data = await skillsApi.getSkills();
      setCatalogSkills(data || []);
    } catch {
      // optional
    }
  }, []);

  useEffect(() => {
    fetchCatalogSkills();
  }, [fetchCatalogSkills]);

  // Fetch skills mapped to the currently selected course
  const fetchCourseSkills = useCallback(async () => {
    if (!selectedCourse) {
      setCourseSkills([]);
      return;
    }
    setIsLoadingCourseSkills(true);
    try {
      const data = await coursesApi.getCourseSkills(selectedCourse.id);
      setCourseSkills(data || []);
    } catch {
      setCourseSkills([]);
    } finally {
      setIsLoadingCourseSkills(false);
    }
  }, [selectedCourse]);

  useEffect(() => {
    fetchCourseSkills();
  }, [fetchCourseSkills]);

  // Create new course
  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCourseCode || !newCourseName) {
      showToast('Course code and course title are required.', 'warning');
      return;
    }
    setIsCreatingCourse(true);
    try {
      const created = await coursesApi.createCourse({
        course_id: newCourseCode,
        course_code: newCourseCode,
        name: newCourseName,
        department: newCourseDept,
        description: newCourseDesc,
        is_active: true,
      });
      showToast(`Course "${created.name || created.course_title}" created!`, 'success');
      setIsAddCourseModalOpen(false);
      setNewCourseCode('');
      setNewCourseName('');
      setNewCourseDesc('');
      await fetchCourses();
      setSelectedCourse(created);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create course.';
      showToast(msg, 'error');
    } finally {
      setIsCreatingCourse(false);
    }
  };

  // Delete selected course
  const handleDeleteCourse = async () => {
    if (!selectedCourse) return;
    const cName = selectedCourse.name || selectedCourse.course_title || `Course #${selectedCourse.id}`;
    if (!window.confirm(`Are you sure you want to remove "${cName}" from the curriculum?`)) {
      return;
    }
    try {
      await coursesApi.deleteCourse(selectedCourse.id);
      showToast('Course removed from curriculum.', 'info');
      await fetchCourses();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete course.';
      showToast(msg, 'error');
    }
  };

  // Map a skill to the selected course
  const handleAddCourseSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourse || !newSkillToMap) return;
    setIsMappingSkill(true);
    try {
      await coursesApi.addSkillToCourse({
        course_id: Number(selectedCourse.id),
        skill_id: Number(newSkillToMap),
      });
      showToast('Skill mapped to syllabus!', 'success');
      setNewSkillToMap('');
      await fetchCourseSkills();
      const updatedGap = await mlApi.getCourseGaps(selectedCourse.id);
      setCourseGap(updatedGap);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to map skill to course.';
      showToast(msg, 'error');
    } finally {
      setIsMappingSkill(false);
    }
  };

  // Unmap a skill from the selected course
  const handleDeleteCourseSkill = async (mappingId: number) => {
    try {
      await coursesApi.deleteCourseSkill(mappingId);
      showToast('Skill unmapped from syllabus.', 'info');
      await fetchCourseSkills();
      if (selectedCourse) {
        const updatedGap = await mlApi.getCourseGaps(selectedCourse.id);
        setCourseGap(updatedGap);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to remove skill mapping.';
      showToast(msg, 'error');
    }
  };

  // Helper for recommendation item
  const renderRecommendation = (rec: Recommendation | string, idx: number) => {
    if (typeof rec === 'string') {
      return (
        <div key={idx} className="p-4 rounded-xl border border-indigo-100 bg-indigo-50/40 text-xs text-slate-800 flex items-start gap-3">
          <Lightbulb className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <p className="leading-relaxed">{rec}</p>
        </div>
      );
    }

    const impactColor =
      rec.impact_level === 'High'
        ? 'text-red-700 bg-red-50 border-red-200'
        : rec.impact_level === 'Medium'
        ? 'text-amber-700 bg-amber-50 border-amber-200'
        : 'text-indigo-700 bg-indigo-50 border-indigo-200';

    return (
      <div key={rec.id || idx} className="p-4 rounded-xl border border-slate-200 bg-white hover:border-indigo-200 transition-all shadow-2xs space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-bold text-slate-900">
            {rec.title || `Curriculum Action #${idx + 1}`}
          </span>
          {rec.impact_level && (
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${impactColor}`}>
              {rec.impact_level} Priority
            </span>
          )}
        </div>

        <p className="text-xs text-slate-600 leading-relaxed">
          {rec.action || rec.rationale}
        </p>

        {rec.target_skills && rec.target_skills.length > 0 && (
          <div className="pt-2 flex flex-wrap gap-1">
            {rec.target_skills.map((ts, sIdx) => (
              <span key={sIdx} className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
                {ts}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Helper for skill labels
  const getSkillText = (item: unknown): string => {
    if (typeof item === 'string') return item;
    if (typeof item === 'object' && item !== null) {
      const obj = item as { name?: string };
      return obj.name || 'Skill';
    }
    return String(item);
  };

  return (
    <PortalLayout activeRole="Institute">
      <div className="space-y-8">
        {/* Header */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">
                Academic Curriculum Intelligence & Market Alignment
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                Curriculum Syllabus Evaluation
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Benchmark institutional syllabi against empirical real-time industry vacancy requirements.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1.5 rounded-lg">
                Catalog: {courses.length} courses
              </span>
            </div>
          </div>
        </div>

        {/* Course Catalog Grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-indigo-600" />
              Registered Institutional Courses
            </h2>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsAddCourseModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-2xs transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Course</span>
              </button>
              <button
                type="button"
                onClick={fetchCourses}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 cursor-pointer px-2 py-1.5"
              >
                Refresh Catalog
              </button>
            </div>
          </div>

          {isLoadingCourses ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <Skeleton className="h-44 rounded-xl" />
              <Skeleton className="h-44 rounded-xl" />
              <Skeleton className="h-44 rounded-xl" />
            </div>
          ) : coursesError ? (
            <Alert type="error" message={coursesError} onRetry={fetchCourses} />
          ) : courses.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No courses registered in backend catalog."
              description="Institutional courses added to the system will appear here for alignment evaluation."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {courses.map((course) => {
                const isSelected = selectedCourse?.id === course.id;
                return (
                  <div
                    key={course.id}
                    onClick={() => setSelectedCourse(course)}
                    className={`p-5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? 'bg-indigo-50/40 border-indigo-600 shadow-sm ring-1 ring-indigo-600'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-2xs'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                          {course.course_code || `CRS-${course.id}`}
                        </span>
                        {isSelected && (
                          <span className="text-[11px] font-semibold text-indigo-700 bg-white px-2 py-0.5 rounded shadow-2xs">
                            Active Audit
                          </span>
                        )}
                      </div>

                      <h3 className="text-sm font-bold text-slate-900 mb-1 leading-snug">
                        {course.course_title}
                      </h3>

                      <div className="text-xs text-slate-500 space-y-1 mt-2">
                        {course.provider && (
                          <div className="flex items-center gap-1.5">
                            <Building className="w-3.5 h-3.5 text-slate-400" />
                            <span className="truncate">{course.provider}</span>
                          </div>
                        )}
                        {course.duration && (
                          <div className="flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                            <span>{course.duration}</span>
                          </div>
                        )}
                      </div>

                      <p className="mt-3 text-xs text-slate-600 line-clamp-2 leading-relaxed">
                        {course.description}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-indigo-600">
                      <span>Analyze Alignment</span>
                      <ChevronRight className="w-4 h-4" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Course ML Alignment Analysis */}
        {selectedCourse && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <span className="text-[11px] font-mono text-slate-400 uppercase">
                  {selectedCourse.course_code}
                </span>
                <h3 className="text-lg font-bold text-slate-900">
                  ML Alignment Audit: {selectedCourse.course_title}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleDeleteCourse}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 cursor-pointer"
                  title="Remove Course from Curriculum"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete Course</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsLoadingGap(true);
                    mlApi
                      .getCourseGaps(selectedCourse.id)
                      .then(setCourseGap)
                      .catch((err) => setGapError(err.message))
                      .finally(() => setIsLoadingGap(false));
                  }}
                  disabled={isLoadingGap}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingGap ? 'animate-spin' : ''}`} />
                  <span>Recalculate Gap</span>
                </button>
              </div>
            </div>

            {isLoadingGap ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Skeleton className="h-28 rounded-xl" />
                  <Skeleton className="h-28 rounded-xl" />
                </div>
                <Skeleton className="h-48 rounded-xl" />
              </div>
            ) : gapError ? (
              <Alert
                type="warning"
                title="ML Syllabus Gap Information"
                message={gapError}
              />
            ) : !courseGap ? (
              <EmptyState
                icon={PieChart}
                title="No ML gap data available for this course syllabus."
                description="This course may not yet have processed market comparison embeddings."
              />
            ) : (
              <div className="space-y-6">
                {/* Metric Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/50">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                      Curriculum Gap Score
                    </span>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-slate-900 tabular-nums">
                        {formatPercentage(courseGap.curriculum_gap_score)}
                      </span>
                      <span className="text-xs text-red-600 font-medium">Deficit</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Aggregated deviation from current market requirements
                    </p>
                  </div>

                  <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/50">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                      Market Coverage
                    </span>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-emerald-700 tabular-nums">
                        {formatPercentage(courseGap.market_coverage_percentage)}
                      </span>
                      <span className="text-xs text-emerald-600 font-medium">Coverage</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Percentage of active labour market skills addressed
                    </p>
                  </div>

                  <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 sm:col-span-2 lg:col-span-1">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                      Curriculum Health
                    </span>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-sm font-bold text-indigo-700">
                        {courseGap.curriculum_gap_score > 0.4 ? 'Revision Needed' : 'Well Aligned'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Based on dynamic hiring frequency in target regions
                    </p>
                  </div>
                </div>

                {/* Missing & Weak Skills Columns */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Missing Skills */}
                  <div className="p-5 rounded-xl border border-red-200 bg-red-50/20">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertCircle className="w-4 h-4 text-red-600" />
                      <h4 className="text-xs font-bold text-red-900 uppercase tracking-wider">
                        Missing Critical Skills
                      </h4>
                    </div>
                    <p className="text-xs text-slate-500 mb-3">
                      Skills required in market requisitions but completely absent in syllabus:
                    </p>

                    {!courseGap.missing_skills || courseGap.missing_skills.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No missing skills detected.</p>
                    ) : (
                      <div className="flex flex-wrap gap-1.5">
                        {courseGap.missing_skills.map((skill, sIdx) => (
                          <span
                            key={sIdx}
                            className="text-xs bg-red-50 border border-red-200 text-red-700 px-2.5 py-1 rounded-lg font-medium"
                          >
                            {getSkillText(skill)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Weak Skills */}
                  <div className="p-5 rounded-xl border border-amber-200 bg-amber-50/20">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                        Weakly Covered Skills
                      </h4>
                    </div>
                    <p className="text-xs text-slate-500 mb-3">
                      Skills mentioned in syllabus but lacking depth compared to enterprise expectations:
                    </p>

                    {!courseGap.weak_skills || courseGap.weak_skills.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No weak skills detected.</p>
                    ) : (
                      <div className="flex flex-wrap gap-1.5">
                        {courseGap.weak_skills.map((skill, sIdx) => (
                          <span
                            key={sIdx}
                            className="text-xs bg-amber-50 border border-amber-200 text-amber-700 px-2.5 py-1 rounded-lg font-medium"
                          >
                            {getSkillText(skill)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* ML Recommendations */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                    <h4 className="text-sm font-bold text-slate-900">
                      ML-Generated Curricular Recommendations
                    </h4>
                  </div>

                  {!courseGap.recommendations || courseGap.recommendations.length === 0 ? (
                    <p className="text-xs text-slate-400 italic p-4 bg-slate-50 rounded-xl">
                      No automated curricular recommendations generated for this syllabus.
                    </p>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {courseGap.recommendations.map((rec, rIdx) =>
                        renderRecommendation(rec, rIdx)
                      )}
                    </div>
                  )}
                </div>

                {/* Course Syllabus Skills Mappings */}
                <div className="pt-5 border-t border-slate-100">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        <Layers className="w-4 h-4 text-indigo-600" />
                        Syllabus Skill Mappings ({courseSkills.length})
                      </h4>
                      <p className="text-xs text-slate-500">
                        Explicit skills mapped to this course syllabus in the curriculum database.
                      </p>
                    </div>
                  </div>

                  {/* Add Skill to Course Form */}
                  <form onSubmit={handleAddCourseSkill} className="mb-4 flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <select
                      value={newSkillToMap}
                      onChange={(e) => setNewSkillToMap(e.target.value)}
                      className="flex-1 px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">-- Select Skill from Taxonomy to Map to Syllabus --</option>
                      {catalogSkills.map((sk) => (
                        <option key={sk.id} value={sk.id}>
                          {sk.name} ({sk.category || 'General'})
                        </option>
                      ))}
                    </select>
                    <button
                      type="submit"
                      disabled={isMappingSkill || !newSkillToMap}
                      className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-2xs transition-colors disabled:opacity-50 cursor-pointer whitespace-nowrap"
                    >
                      {isMappingSkill ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                      <span>Map Skill</span>
                    </button>
                  </form>

                  {/* Mapped Skills List */}
                  {isLoadingCourseSkills ? (
                    <Skeleton className="h-12 w-full" />
                  ) : courseSkills.length === 0 ? (
                    <p className="text-xs text-slate-400 italic p-3 bg-slate-50 rounded-lg">
                      No explicit skills mapped to this course yet. Use the dropdown above to add skills.
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {courseSkills.map((cs) => {
                        const matchedSkill = catalogSkills.find(
                          (s) => Number(s.id) === Number(cs.skill_id) || s.skill_id === cs.skill_code
                        );
                        const label =
                          cs.skill_name ||
                          cs.name ||
                          cs.skill?.name ||
                          matchedSkill?.name ||
                          cs.skill_code ||
                          `Skill #${cs.skill_id}`;
                        return (
                          <div
                            key={cs.id}
                            className="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 text-slate-800 rounded-lg text-xs"
                          >
                            <span className="font-semibold">{label}</span>
                            <button
                              type="button"
                              onClick={() => handleDeleteCourseSkill(cs.id)}
                              className="text-slate-400 hover:text-red-600 transition-colors cursor-pointer"
                              title="Unmap Skill"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Add Course Modal */}
        {isAddCourseModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-indigo-600" />
                  <h3 className="text-base font-bold text-slate-900">Add New Vocational Course</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAddCourseModalOpen(false)}
                  className="text-slate-400 hover:text-slate-600 cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateCourse} className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Course Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CS-401, DS-201"
                    value={newCourseCode}
                    onChange={(e) => setNewCourseCode(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Course Title *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Distributed Systems Engineering"
                    value={newCourseName}
                    onChange={(e) => setNewCourseName(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Department
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Computer Science & AI"
                    value={newCourseDept}
                    onChange={(e) => setNewCourseDept(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Syllabus Description
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Overview of core modules, technologies taught, and curriculum focus..."
                    value={newCourseDesc}
                    onChange={(e) => setNewCourseDesc(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsAddCourseModalOpen(false)}
                    className="px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 bg-slate-100 rounded-lg cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isCreatingCourse}
                    className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                  >
                    {isCreatingCourse ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                    <span>Create Course</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </PortalLayout>
  );
};
