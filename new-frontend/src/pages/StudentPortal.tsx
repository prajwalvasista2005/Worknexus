import React, { useState, useEffect, useCallback, useRef } from 'react';
import { PortalLayout } from '../components/layout/PortalLayout';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { rolesApi } from '../api/roles';
import { mlApi } from '../api/ml';
import { studentsApi } from '../api/students';
import { skillsApi } from '../api/skills';
import { coursesApi } from '../api/courses';
import {
  Role,
  StudentGap,
  CourseCandidate,
  SkillEvidence,
  Skill,
  UserSkill,
  Course,
  CourseSkill,
} from '../types';
import { CircularProgress } from '../components/ui/CircularProgress';
import { EmptyState } from '../components/ui/EmptyState';
import { CardSkeleton, Skeleton } from '../components/ui/Skeleton';
import { Alert } from '../components/ui/Alert';
import { formatPercentage, formatDate, normalizeExternalUrl } from '../utils/formatters';
import {
  Target,
  BookOpen,
  Award,
  CheckCircle,
  AlertTriangle,
  Github,
  PlusCircle,
  ExternalLink,
  ChevronRight,
  Sparkles,
  BarChart3,
  Calendar,
  Send,
  Loader2,
  RefreshCw,
  Trash2,
  Compass,
  Lightbulb,
  X,
  Clock,
  FileText,
} from 'lucide-react';

/**
 * Normalizes raw student gap API responses and evidence submission responses into
 * a standardized StudentGap structure, providing full fallback for acquired_skills / skills_acquired
 * and match_score / overall_match_score.
 */
export function normalizeStudentGap(raw: unknown): StudentGap | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const obj = raw as Record<string, unknown>;

  // Handle nested recalculated_gap or gap_analysis objects if present
  const source =
    (obj.recalculated_gap && typeof obj.recalculated_gap === 'object'
      ? (obj.recalculated_gap as Record<string, unknown>)
      : null) ||
    (obj.gap_analysis && typeof obj.gap_analysis === 'object'
      ? (obj.gap_analysis as Record<string, unknown>)
      : null) ||
    obj;

  // 1. Acquired / Verified Competencies
  let acquired: unknown[] = [];
  if (Array.isArray(source.acquired_skills) && source.acquired_skills.length > 0) {
    acquired = source.acquired_skills;
  } else if (Array.isArray(source.skills_acquired) && source.skills_acquired.length > 0) {
    acquired = source.skills_acquired;
  } else if (Array.isArray(source.acquired) && source.acquired.length > 0) {
    acquired = source.acquired;
  } else if (Array.isArray(source.present_skills) && source.present_skills.length > 0) {
    acquired = source.present_skills;
  } else if (Array.isArray(obj.acquired_skills) && obj.acquired_skills.length > 0) {
    acquired = obj.acquired_skills;
  } else if (Array.isArray(obj.skills_acquired) && obj.skills_acquired.length > 0) {
    acquired = obj.skills_acquired;
  } else if (Array.isArray(source.skill_gaps) && source.skill_gaps.length > 0) {
    acquired = (source.skill_gaps as Array<Record<string, unknown>>)
      .filter((sg) => sg.student_status === 'present' || sg.status === 'present' || Boolean(sg.student_has_skill))
      .map((sg) => ({
        id: (sg.skill_id || sg.id) as string,
        skill_id: (sg.skill_id || sg.id) as string,
        name: (sg.skill_name || sg.name || sg.skill_id || 'Skill') as string,
        skill_name: (sg.skill_name || sg.name || sg.skill_id || 'Skill') as string,
        level: (sg.level || sg.strength || 'intermediate') as string,
        strength: (sg.strength || 'intermediate') as string,
        score: 1.0,
      }));
  }

  // 2. Missing Skills / Gaps
  let missing: unknown[] = [];
  if (Array.isArray(source.missing_skills) && source.missing_skills.length > 0) {
    missing = source.missing_skills;
  } else if (Array.isArray(source.skills_missing) && source.skills_missing.length > 0) {
    missing = source.skills_missing;
  } else if (Array.isArray(source.missing) && source.missing.length > 0) {
    missing = source.missing;
  } else if (Array.isArray(obj.missing_skills) && obj.missing_skills.length > 0) {
    missing = obj.missing_skills;
  } else if (Array.isArray(obj.skills_missing) && obj.skills_missing.length > 0) {
    missing = obj.skills_missing;
  } else if (Array.isArray(source.skill_gaps) && source.skill_gaps.length > 0) {
    missing = (source.skill_gaps as Array<Record<string, unknown>>)
      .filter((sg) => sg.student_status === 'missing' || sg.status === 'missing' || (!sg.student_has_skill && sg.student_has_skill !== undefined))
      .map((sg) => ({
        id: (sg.skill_id || sg.id) as string,
        skill_id: (sg.skill_id || sg.id) as string,
        name: (sg.skill_name || sg.name || sg.skill_id || 'Skill') as string,
        skill_name: (sg.skill_name || sg.name || sg.skill_id || 'Skill') as string,
        priority: (sg.priority || 'High') as string,
        importance: (sg.importance || 1.0) as number,
      }));
  }

  // 3. Match Score / Overall Match Score
  const summaryObj = (source.summary || obj.summary) as Record<string, unknown> | undefined;
  const rawScore =
    source.overall_match_score !== undefined && source.overall_match_score !== null
      ? source.overall_match_score
      : source.match_score !== undefined && source.match_score !== null
      ? source.match_score
      : obj.overall_match_score !== undefined && obj.overall_match_score !== null
      ? obj.overall_match_score
      : obj.match_score !== undefined && obj.match_score !== null
      ? obj.match_score
      : source.score !== undefined && source.score !== null
      ? source.score
      : summaryObj?.overall_match_score !== undefined && summaryObj.overall_match_score !== null
      ? summaryObj.overall_match_score
      : summaryObj?.match_score !== undefined && summaryObj.match_score !== null
      ? summaryObj.match_score
      : null;

  let matchScore: number;
  if (rawScore !== null) {
    const parsed = typeof rawScore === 'string' ? parseFloat(rawScore) : Number(rawScore);
    matchScore = Number.isFinite(parsed) ? parsed : 0;
  } else {
    const total = acquired.length + missing.length;
    matchScore = total > 0 ? Number((acquired.length / total).toFixed(2)) : 0;
  }

  // 4. Gap Percentage / Gap Score
  const rawGap =
    source.gap_percentage !== undefined && source.gap_percentage !== null
      ? source.gap_percentage
      : source.gap_score !== undefined && source.gap_score !== null
      ? source.gap_score
      : obj.gap_percentage !== undefined && obj.gap_percentage !== null
      ? obj.gap_percentage
      : obj.gap_score !== undefined && obj.gap_score !== null
      ? obj.gap_score
      : source.gap_pct !== undefined && source.gap_pct !== null
      ? source.gap_pct
      : summaryObj?.gap_percentage !== undefined && summaryObj.gap_percentage !== null
      ? summaryObj.gap_percentage
      : null;

  let gapPercentage: number;
  if (rawGap !== null) {
    const parsed = typeof rawGap === 'string' ? parseFloat(rawGap) : Number(rawGap);
    gapPercentage = Number.isFinite(parsed) ? parsed : 0;
  } else {
    const normalizedMatch = matchScore <= 1 && matchScore > 0 ? matchScore * 100 : matchScore;
    gapPercentage = Math.max(0, Math.min(100, Number((100 - normalizedMatch).toFixed(1))));
  }

  return {
    ...obj,
    ...source,
    student_id: (source.student_id || obj.student_id) as string | number | undefined,
    role_id: (source.role_id || obj.role_id) as string | number | undefined,
    role_name: (source.role_name || obj.role_name) as string | undefined,
    overall_match_score: matchScore,
    match_score: matchScore,
    score: matchScore,
    gap_percentage: gapPercentage,
    gap_score: gapPercentage,
    gap_pct: gapPercentage,
    acquired_skills: acquired as StudentGap['acquired_skills'],
    skills_acquired: acquired as StudentGap['skills_acquired'],
    missing_skills: missing as StudentGap['missing_skills'],
    skills_missing: missing as StudentGap['skills_missing'],
    skill_importance: (source.skill_importance || obj.skill_importance) as StudentGap['skill_importance'],
  };
}

export const StudentPortal: React.FC = () => {
  const { user } = useAuth();
  const { showToast } = useToast();

  const studentId = user?.id || '';

  // Data state
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [catalogSkills, setCatalogSkills] = useState<Skill[]>([]);

  const [gapData, setGapData] = useState<StudentGap | null>(null);
  const [courseCandidates, setCourseCandidates] = useState<CourseCandidate[]>([]);
  const [evidenceList, setEvidenceList] = useState<SkillEvidence[]>([]);

  // User Skills (Direct Profile Skills)
  const [mySkills, setMySkills] = useState<UserSkill[]>([]);
  const [isLoadingMySkills, setIsLoadingMySkills] = useState(false);
  const [newSkillCatalogId, setNewSkillCatalogId] = useState<number | string>('');
  const [newSkillProficiency, setNewSkillProficiency] = useState('intermediate');
  const [isAddingUserSkill, setIsAddingUserSkill] = useState(false);

  // Recommendations & Target Role Save
  const [studentRecs, setStudentRecs] = useState<string[]>([]);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
  const [isSavingTargetRole, setIsSavingTargetRole] = useState(false);

  // Loading & error states
  const [isLoadingRoles, setIsLoadingRoles] = useState(true);
  const [isLoadingGap, setIsLoadingGap] = useState(false);
  const [isLoadingCourses, setIsLoadingCourses] = useState(false);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(true);
  const [rolesError, setRolesError] = useState<string | null>(null);
  const [gapError, setGapError] = useState<string | null>(null);
  const [coursesError, setCoursesError] = useState<string | null>(null);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  // Evidence submission form state & ref
  const evidenceFormRef = useRef<HTMLDivElement>(null);
  const [evidenceSkillId, setEvidenceSkillId] = useState('');
  const [evidenceType, setEvidenceType] = useState('project');
  const [evidenceStrength, setEvidenceStrength] = useState<number>(8);
  const [evidenceRepo, setEvidenceRepo] = useState('');
  const [isSubmittingEvidence, setIsSubmittingEvidence] = useState(false);

  // Recommended Course Syllabus modal state
  const [selectedSyllabusCandidate, setSelectedSyllabusCandidate] = useState<CourseCandidate | null>(null);
  const [syllabusDetails, setSyllabusDetails] = useState<Course | null>(null);
  const [syllabusSkills, setSyllabusSkills] = useState<CourseSkill[]>([]);
  const [isLoadingSyllabus, setIsLoadingSyllabus] = useState<boolean>(false);

  // 1. Fetch available career roles
  const fetchRoles = useCallback(async () => {
    setIsLoadingRoles(true);
    setRolesError(null);
    try {
      const data = await rolesApi.getRoles();
      setRoles(data || []);
      if (data && data.length > 0) {
        // Default to first role or previously selected
        setSelectedRole(data[0]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load career roles from backend.';
      setRolesError(msg);
    } finally {
      setIsLoadingRoles(false);
    }
  }, []);

  // 2. Fetch catalog skills for evidence picker
  const fetchSkills = useCallback(async () => {
    try {
      const data = await skillsApi.getSkills();
      setCatalogSkills(data || []);
    } catch {
      // Catalog skills optional; student can still manually enter skill ID
    }
  }, []);

  // 3. Fetch student's submitted evidence
  const fetchEvidence = useCallback(async () => {
    if (!studentId) return;
    setIsLoadingEvidence(true);
    setEvidenceError(null);
    try {
      const data = await studentsApi.getEvidence(studentId);
      setEvidenceList(data || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve evidence records.';
      setEvidenceError(msg);
    } finally {
      setIsLoadingEvidence(false);
    }
  }, [studentId]);

  // Initial load
  useEffect(() => {
    fetchRoles();
    fetchSkills();
    fetchEvidence();
  }, [fetchRoles, fetchSkills, fetchEvidence]);

  // 4. Fetch Role Readiness Gap & Course Candidates when selectedRole changes
  useEffect(() => {
    if (!selectedRole || !studentId) {
      setGapData(null);
      setCourseCandidates([]);
      return;
    }

    const roleId = selectedRole.id;

    // Fetch Gap
    const loadGap = async () => {
      setIsLoadingGap(true);
      setGapError(null);
      try {
        const gap = await mlApi.getStudentGap(studentId, roleId);
        setGapData(normalizeStudentGap(gap));
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'ML gap analysis unavailable for this role.';
        setGapError(msg);
        setGapData(null);
      } finally {
        setIsLoadingGap(false);
      }
    };

    // Fetch Course Candidates
    const loadCourses = async () => {
      setIsLoadingCourses(true);
      setCoursesError(null);
      try {
        const candidates = await mlApi.getCourseCandidates(studentId, roleId);
        setCourseCandidates(candidates || []);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'No course candidates retrieved.';
        setCoursesError(msg);
        setCourseCandidates([]);
      } finally {
        setIsLoadingCourses(false);
      }
    };

    loadGap();
    loadCourses();
  }, [selectedRole, studentId]);

  // Handle Evidence Submission
  const handleSubmitEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!evidenceSkillId || !evidenceRepo) {
      showToast('Please specify a Skill and Repository URL.', 'warning');
      return;
    }

    // Resolve canonical skill ID if user selected or typed a skill name
    let canonicalSkillId = evidenceSkillId.trim();
    const matchedCatalog = catalogSkills.find(
      (s) =>
        s.skill_id?.toLowerCase() === canonicalSkillId.toLowerCase() ||
        s.name?.toLowerCase() === canonicalSkillId.toLowerCase() ||
        String(s.id) === canonicalSkillId
    );
    if (matchedCatalog?.skill_id) {
      canonicalSkillId = matchedCatalog.skill_id;
    } else if (gapData) {
      const allGapSkills = [
        ...(Array.isArray(gapData.missing_skills) ? gapData.missing_skills : []),
        ...(Array.isArray((gapData as any).skills_missing) ? (gapData as any).skills_missing : []),
        ...(Array.isArray(gapData.acquired_skills) ? gapData.acquired_skills : []),
        ...(Array.isArray((gapData as any).skills_acquired) ? (gapData as any).skills_acquired : []),
      ];
      const matchedGap = allGapSkills.find((s: unknown) => {
        const sid = (typeof s === 'object' && s !== null ? (s as any).skill_id || (s as any).id : String(s))?.toLowerCase();
        const sname = (typeof s === 'object' && s !== null ? (s as any).skill_name || (s as any).name : String(s))?.toLowerCase();
        return sid === canonicalSkillId.toLowerCase() || sname === canonicalSkillId.toLowerCase();
      });
      if (matchedGap) {
        canonicalSkillId = typeof matchedGap === 'object' && matchedGap !== null
          ? ((matchedGap as any).skill_id || (matchedGap as any).id || canonicalSkillId)
          : String(matchedGap);
      }
    }

    setIsSubmittingEvidence(true);
    try {
      const submissionResult = await studentsApi.submitEvidence(studentId, {
        skill_id: canonicalSkillId,
        evidence_type: evidenceType,
        strength: Number(evidenceStrength),
        metadata: {
          repo: evidenceRepo,
          timestamp: new Date().toISOString(),
        },
      });

      // Immediate state mapping from evidence submission response:
      // If the submission endpoint returned cascading gap recalculation fields,
      // update gapData immediately so user sees instant match score & acquired competencies update
      const subRecalc =
        (submissionResult as any)?.recalculated_gap ||
        (submissionResult as any)?.gap_analysis ||
        ((submissionResult as any)?.acquired_skills ||
        (submissionResult as any)?.skills_acquired ||
        (submissionResult as any)?.match_score !== undefined ||
        (submissionResult as any)?.overall_match_score !== undefined
          ? submissionResult
          : null);
      if (subRecalc) {
        setGapData((prev) => normalizeStudentGap({ ...(prev || {}), ...subRecalc }));
      }

      showToast('Skill evidence successfully submitted!', 'success');
      setEvidenceRepo('');
      setEvidenceSkillId('');

      // Automated state re-fetch for instant UI synchronization:
      // 1. Refresh verified evidence records list
      await fetchEvidence();

      // 2. Refresh acquired competencies list (direct profile skills)
      await fetchMySkills();

      // 3. Refresh gap analysis, course candidates & recommendations if role is selected
      if (selectedRole) {
        setIsLoadingGap(true);
        try {
          const [updatedGap, updatedCandidates, updatedRecs] = await Promise.all([
            mlApi.getStudentGap(studentId, selectedRole.id),
            mlApi.getCourseCandidates(studentId, selectedRole.id),
            mlApi.getStudentRecommendations(studentId, selectedRole.id).catch(() => null),
          ]);
          setGapData(normalizeStudentGap(updatedGap));
          setCourseCandidates(updatedCandidates || []);
          if (updatedRecs?.recommendations && Array.isArray(updatedRecs.recommendations)) {
            setStudentRecs(updatedRecs.recommendations.map((r: any) => typeof r === 'string' ? r : r.action || r.recommendation || JSON.stringify(r)));
          } else if (Array.isArray(updatedRecs)) {
            setStudentRecs(updatedRecs.map((r: any) => typeof r === 'string' ? r : r.action || r.recommendation || JSON.stringify(r)));
          }
        } catch {
          // Keep existing states if fetch error
        } finally {
          setIsLoadingGap(false);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit evidence.';
      showToast(msg, 'error');
    } finally {
      setIsSubmittingEvidence(false);
    }
  };

  // Handle "Submit Proof" click on individual gap rows: set skill and scroll into view
  const handleInitiateProof = (skill: unknown) => {
    const skKey = getSkillKey(skill);
    const label = getSkillLabel(skill);
    setEvidenceSkillId(skKey);
    showToast(`Selected "${label}" for evidence verification.`, 'info');
    if (evidenceFormRef.current) {
      evidenceFormRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => {
        const repoInput = document.getElementById('evidence-repo');
        if (repoInput) repoInput.focus();
      }, 300);
    }
  };

  // Handle "View Syllabus" click on recommended course cards
  const handleOpenSyllabus = async (candidate: CourseCandidate) => {
    setSelectedSyllabusCandidate(candidate);
    setIsLoadingSyllabus(true);
    setSyllabusDetails(null);
    setSyllabusSkills([]);
    try {
      const courseId = candidate.course_id;
      const [courseRes, skillsRes] = await Promise.allSettled([
        coursesApi.getCourse(courseId),
        coursesApi.getCourseSkills(courseId),
      ]);
      if (courseRes.status === 'fulfilled' && courseRes.value) {
        setSyllabusDetails(courseRes.value);
      }
      if (skillsRes.status === 'fulfilled' && skillsRes.value) {
        setSyllabusSkills(skillsRes.value || []);
      }
    } catch {
      // Fallback to candidate metadata
    } finally {
      setIsLoadingSyllabus(false);
    }
  };

  const handleCloseSyllabus = () => {
    setSelectedSyllabusCandidate(null);
    setSyllabusDetails(null);
    setSyllabusSkills([]);
  };

  // Fetch direct user skills from database
  const fetchMySkills = useCallback(async () => {
    setIsLoadingMySkills(true);
    try {
      const data = await skillsApi.getMySkills();
      setMySkills(data || []);
    } catch {
      // User skills optional
    } finally {
      setIsLoadingMySkills(false);
    }
  }, []);

  useEffect(() => {
    fetchMySkills();
  }, [fetchMySkills]);

  // Handle direct skill addition to profile
  const handleAddUserSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSkillCatalogId) {
      showToast('Please select a skill to add to your profile.', 'warning');
      return;
    }
    setIsAddingUserSkill(true);
    try {
      await skillsApi.addUserSkill({
        skill_id: Number(newSkillCatalogId),
        proficiency_level: newSkillProficiency,
        source: 'self_reported',
      });
      showToast('Skill added to profile!', 'success');
      setNewSkillCatalogId('');
      await fetchMySkills();
      if (selectedRole && studentId) {
        const updatedGap = await mlApi.getStudentGap(studentId, selectedRole.id);
        setGapData(normalizeStudentGap(updatedGap));
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add skill to profile.';
      showToast(msg, 'error');
    } finally {
      setIsAddingUserSkill(false);
    }
  };

  // Handle direct skill deletion from profile
  const handleDeleteUserSkill = async (id: number) => {
    try {
      await skillsApi.deleteUserSkill(id);
      showToast('Skill removed from profile.', 'info');
      await fetchMySkills();
      if (selectedRole && studentId) {
        const updatedGap = await mlApi.getStudentGap(studentId, selectedRole.id);
        setGapData(normalizeStudentGap(updatedGap));
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to remove skill.';
      showToast(msg, 'error');
    }
  };

  // Handle Target Career Role persistence to profile
  const handleSaveTargetRole = async () => {
    if (!selectedRole || !studentId) return;
    setIsSavingTargetRole(true);
    try {
      await studentsApi.saveProfile({
        user_id: Number(studentId),
        target_role_id: selectedRole.id,
      });
      showToast(`Target career "${selectedRole.name || selectedRole.title}" saved to your student profile!`, 'success');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save target role.';
      showToast(msg, 'error');
    } finally {
      setIsSavingTargetRole(false);
    }
  };

  // Load Tailored ML Recommendations
  useEffect(() => {
    if (!selectedRole || !studentId) {
      setStudentRecs([]);
      return;
    }
    setIsLoadingRecs(true);
    mlApi
      .getStudentRecommendations(studentId, selectedRole.id)
      .then((data: any) => {
        if (data?.recommendations && Array.isArray(data.recommendations)) {
          setStudentRecs(data.recommendations.map((r: any) => typeof r === 'string' ? r : r.action || r.recommendation || JSON.stringify(r)));
        } else if (Array.isArray(data)) {
          setStudentRecs(data.map((r: any) => typeof r === 'string' ? r : r.action || r.recommendation || JSON.stringify(r)));
        } else {
          setStudentRecs([]);
        }
      })
      .catch(() => setStudentRecs([]))
      .finally(() => setIsLoadingRecs(false));
  }, [selectedRole, studentId]);

  // Helper to extract canonical skill key/id from string or object
  const getSkillKey = (skill: unknown): string => {
    if (typeof skill === 'string') return skill;
    if (typeof skill === 'object' && skill !== null) {
      const s = skill as { skill_id?: string; id?: string | number; name?: string; skill_name?: string };
      return s.skill_id || (typeof s.id === 'string' ? s.id : undefined) || s.skill_name || s.name || 'Skill';
    }
    return String(skill);
  };

  // Helper to extract human-readable skill name from string or object
  const getSkillLabel = (skill: unknown): string => {
    if (typeof skill === 'string') return skill;
    if (typeof skill === 'object' && skill !== null) {
      const s = skill as { name?: string; skill_name?: string; skill_id?: string; id?: string | number };
      return s.skill_name || s.name || (s.skill_id && !s.skill_id.startsWith('SK_') ? s.skill_id : undefined) || s.skill_id || (typeof s.id === 'string' ? s.id : undefined) || 'Skill';
    }
    return String(skill);
  };

  // Resilient fallback extraction for acquired/verified skills list
  const acquiredList = (
    Array.isArray(gapData?.acquired_skills) && gapData.acquired_skills.length > 0
      ? gapData.acquired_skills
      : Array.isArray((gapData as any)?.skills_acquired) && (gapData as any).skills_acquired.length > 0
      ? (gapData as any).skills_acquired
      : Array.isArray((gapData as any)?.acquired) && (gapData as any).acquired.length > 0
      ? (gapData as any).acquired
      : Array.isArray((gapData as any)?.present_skills) && (gapData as any).present_skills.length > 0
      ? (gapData as any).present_skills
      : []
  );

  // Resilient fallback extraction for missing skills list
  const missingList = (
    Array.isArray(gapData?.missing_skills) && gapData.missing_skills.length > 0
      ? gapData.missing_skills
      : Array.isArray((gapData as any)?.skills_missing) && (gapData as any).skills_missing.length > 0
      ? (gapData as any).skills_missing
      : Array.isArray((gapData as any)?.missing) && (gapData as any).missing.length > 0
      ? (gapData as any).missing
      : []
  );

  // Normalize match score for circular indicator (supporting 0-1 and 0-100 values)
  const rawScore =
    gapData?.overall_match_score !== undefined && gapData.overall_match_score !== null
      ? gapData.overall_match_score
      : gapData?.match_score !== undefined && gapData.match_score !== null
      ? gapData.match_score
      : (gapData as any)?.score !== undefined && (gapData as any)?.score !== null
      ? (gapData as any).score
      : (gapData as any)?.summary?.overall_match_score !== undefined && (gapData as any).summary?.overall_match_score !== null
      ? (gapData as any).summary.overall_match_score
      : (gapData as any)?.summary?.match_score !== undefined && (gapData as any).summary?.match_score !== null
      ? (gapData as any).summary.match_score
      : acquiredList.length + missingList.length > 0
      ? acquiredList.length / (acquiredList.length + missingList.length)
      : 0;

  const overallScore = typeof rawScore === 'string' ? parseFloat(rawScore) || 0 : Number(rawScore) || 0;

  const rawGapPercent =
    gapData?.gap_percentage !== undefined && gapData.gap_percentage !== null
      ? gapData.gap_percentage
      : gapData?.gap_score !== undefined && gapData.gap_score !== null
      ? gapData.gap_score
      : (gapData as any)?.gap_pct !== undefined && (gapData as any)?.gap_pct !== null
      ? (gapData as any).gap_pct
      : (gapData as any)?.summary?.gap_percentage !== undefined && (gapData as any).summary?.gap_percentage !== null
      ? (gapData as any).summary.gap_percentage
      : acquiredList.length + missingList.length > 0
      ? (missingList.length / (acquiredList.length + missingList.length)) * 100
      : null;

  const gapPercent = typeof rawGapPercent === 'string' ? parseFloat(rawGapPercent) : rawGapPercent;

  return (
    <PortalLayout activeRole="Student" targetCareer={selectedRole?.name || selectedRole?.title}>
      <div className="space-y-8">
        {/* Welcome & Target Career Selector Bar */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div>
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">
                Student Career Navigation
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                Welcome back, {user?.full_name || user?.email || 'Student'}
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Align your skills with active industry labour requirements through empirical evidence.
              </p>
            </div>

            {/* Target Career Role Selector */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <label
                htmlFor="role-select"
                className="text-xs font-semibold text-slate-700 whitespace-nowrap flex items-center gap-1.5"
              >
                <Target className="w-4 h-4 text-indigo-600" />
                Target Career Role:
              </label>

              {isLoadingRoles ? (
                <Skeleton className="h-10 w-56" />
              ) : rolesError ? (
                <div className="flex items-center gap-2 text-xs text-red-600">
                  <span>Failed to load roles</span>
                  <button
                    type="button"
                    onClick={fetchRoles}
                    className="underline font-semibold"
                  >
                    Retry
                  </button>
                </div>
              ) : roles.length === 0 ? (
                <div className="text-xs text-slate-400 italic">
                  No target roles returned by backend.
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <select
                    id="role-select"
                    value={selectedRole?.id || ''}
                    onChange={(e) => {
                      const found = roles.find((r) => String(r.id) === e.target.value);
                      if (found) setSelectedRole(found);
                    }}
                    className="px-3.5 py-2 text-sm font-medium text-slate-900 bg-slate-50 border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  >
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name || r.title || `Role #${r.id}`}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleSaveTargetRole}
                    disabled={isSavingTargetRole || !selectedRole}
                    className="px-3 py-2 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors cursor-pointer disabled:opacity-50 whitespace-nowrap"
                    title="Persist this target career in your student profile"
                  >
                    {isSavingTargetRole ? 'Saving...' : 'Set as Goal'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 1: Role Readiness & Skill Gap Analysis */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-indigo-600" />
                Empirical Role Readiness
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Calculated against {selectedRole?.name || selectedRole?.title || 'target role'} industry benchmarks
              </p>
            </div>
            {selectedRole && (
              <button
                type="button"
                onClick={() => {
                  if (selectedRole) {
                    setIsLoadingGap(true);
                    mlApi
                      .getStudentGap(studentId, selectedRole.id)
                      .then((res) => setGapData(normalizeStudentGap(res)))
                      .catch((err) => setGapError(err.message))
                      .finally(() => setIsLoadingGap(false));
                  }
                }}
                disabled={isLoadingGap}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingGap ? 'animate-spin' : ''}`} />
                <span>Refresh ML Gap</span>
              </button>
            )}
          </div>

          {isLoadingGap ? (
            <CardSkeleton rows={4} />
          ) : gapError ? (
            <Alert
              type="error"
              title="Readiness Gap Calculation Error"
              message={gapError}
              onRetry={() => {
                if (selectedRole) {
                  setIsLoadingGap(true);
                  setGapError(null);
                  mlApi
                    .getStudentGap(studentId, selectedRole.id)
                    .then((res) => setGapData(normalizeStudentGap(res)))
                    .catch((e) => setGapError(e.message))
                    .finally(() => setIsLoadingGap(false));
                }
              }}
            />
          ) : !gapData ? (
            <EmptyState
              icon={Target}
              title="No readiness gap analysis available"
              description="Select a target role or verify backend ML service availability."
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Circular Indicator & Summary Card */}
              <div className="lg:col-span-4 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col items-center justify-center">
                <CircularProgress
                  score={overallScore}
                  label="Match Score"
                  sublabel={selectedRole?.name || 'Target Role'}
                />

                <div className="w-full mt-6 pt-5 border-t border-slate-100 grid grid-cols-2 gap-4 text-center">
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Target Role
                    </span>
                    <span className="text-xs font-semibold text-slate-800 truncate block mt-0.5">
                      {selectedRole?.name || selectedRole?.title || 'Selected'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Gap Percentage
                    </span>
                    <span className="text-xs font-semibold text-red-600 tabular-nums block mt-0.5">
                      {gapPercent !== null ? formatPercentage(gapPercent) : '—'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Acquired Skills vs Missing Skills Grid */}
              <div className="lg:col-span-8 space-y-6">
                {/* Acquired Skills */}
                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600" />
                      <h3 className="text-sm font-semibold text-slate-900">
                        Acquired & Verified Competencies
                      </h3>
                    </div>
                    <span className="text-xs font-medium text-slate-500 tabular-nums">
                      {acquiredList.length} skills verified
                    </span>
                  </div>

                  <div className="mt-4">
                    {acquiredList.length === 0 ? (
                      <p className="text-xs text-slate-400 italic py-2">
                        No acquired skills recorded yet. Submit evidence artifacts below to build your verified profile.
                      </p>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {acquiredList.map((skill, index) => {
                          const label = getSkillLabel(skill);
                          const key = getSkillKey(skill) || index;
                          return (
                            <div
                              key={key}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-medium"
                            >
                              <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                              <span>{label}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {/* Missing Skills & Skill Importance */}
                <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <h3 className="text-sm font-semibold text-slate-900">
                        Skill Gaps & Priority Focus Areas
                      </h3>
                    </div>
                    <span className="text-xs font-medium text-slate-500 tabular-nums">
                      {missingList.length} gaps detected
                    </span>
                  </div>

                  <div className="mt-4">
                    {missingList.length === 0 ? (
                      <div className="p-3 rounded-lg bg-emerald-50 text-emerald-800 text-xs">
                        Excellent! No significant skill gaps detected for this role.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {missingList.map((skill, index) => {
                          const label = getSkillLabel(skill);
                          const key = getSkillKey(skill) || index;
                          // Check if importance weight exists
                          let importance: number | null = null;
                          if (gapData.skill_importance) {
                            if (Array.isArray(gapData.skill_importance)) {
                              const match = gapData.skill_importance.find(
                                (item) => item.skill === label || item.skill === String(skill) || item.skill === key
                              );
                              if (match) importance = match.importance;
                            } else if (typeof gapData.skill_importance === 'object') {
                              importance = gapData.skill_importance[label] ?? gapData.skill_importance[key] ?? gapData.skill_importance[String(skill)] ?? null;
                            }
                          }

                          return (
                            <div
                              key={key}
                              className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors"
                            >
                              <div className="flex items-center gap-2.5">
                                <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                                <span className="text-xs font-semibold text-slate-800">
                                  {label}
                                </span>
                              </div>

                              <div className="flex items-center gap-3">
                                {importance !== null && (
                                  <span className="text-[11px] text-slate-500 tabular-nums">
                                    Importance: <strong className="text-slate-800">{formatPercentage(importance)}</strong>
                                  </span>
                                )}
                                <button
                                  type="button"
                                  onClick={() => handleInitiateProof(skill)}
                                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors cursor-pointer"
                                >
                                  Submit Proof
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Tailored AI Career Recommendations */}
        {studentRecs && studentRecs.length > 0 && (
          <div className="bg-indigo-50/50 border border-indigo-100 rounded-2xl p-6 shadow-xs">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="w-5 h-5 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-900">
                Personalized Career Recommendations
              </h2>
            </div>
            <p className="text-xs text-slate-600 mb-4">
              AI-generated action items based on your skill profile and the {selectedRole?.name || selectedRole?.title} target role.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {studentRecs.map((rec, rIdx) => (
                <div key={rIdx} className="p-3 bg-white border border-indigo-100 rounded-xl text-xs text-slate-800 flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold text-[11px] flex items-center justify-center shrink-0 mt-0.5">
                    {rIdx + 1}
                  </span>
                  <span className="leading-relaxed">{rec}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section: Direct Profile Competencies (User Skills CRUD) */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100 mb-6">
            <div>
              <div className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-indigo-600" />
                <h2 className="text-lg font-bold text-slate-900">
                  Profile Skill Inventory
                </h2>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Directly declare and manage your proficiencies in the canonical taxonomy database.
              </p>
            </div>
            <span className="text-xs font-semibold text-slate-700 bg-slate-100 px-3 py-1 rounded-full tabular-nums">
              {mySkills.length} Recorded Skills
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Add Skill Form */}
            <form onSubmit={handleAddUserSkill} className="lg:col-span-5 space-y-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Add Skill to Profile
              </h3>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Catalog Skill
                </label>
                <select
                  value={newSkillCatalogId}
                  onChange={(e) => setNewSkillCatalogId(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">-- Choose Skill from Taxonomy --</option>
                  {catalogSkills.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.category || 'General'})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Proficiency Level
                </label>
                <select
                  value={newSkillProficiency}
                  onChange={(e) => setNewSkillProficiency(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                  <option value="expert">Expert</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isAddingUserSkill || !newSkillCatalogId}
                className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-2xs transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isAddingUserSkill ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PlusCircle className="w-3.5 h-3.5" />}
                <span>Add Skill to Profile</span>
              </button>
            </form>

            {/* List of User Skills */}
            <div className="lg:col-span-7">
              {isLoadingMySkills ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : mySkills.length === 0 ? (
                <EmptyState
                  icon={Compass}
                  title="No profile skills recorded"
                  description="Use the form on the left to add skills from the canonical catalog to your profile."
                />
              ) : (
                <div className="divide-y divide-slate-100 max-h-[300px] overflow-y-auto">
                  {mySkills.map((us) => (
                    <div key={us.id} className="py-2.5 flex items-center justify-between gap-3">
                      <div>
                        <span className="text-xs font-bold text-slate-900">
                          {us.skill_name || `Skill #${us.skill_id}`}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded capitalize">
                            {us.proficiency_level}
                          </span>
                          <span className="text-[10px] text-slate-400 capitalize">
                            Source: {us.source?.replace('_', ' ') || 'self-reported'}
                          </span>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleDeleteUserSkill(us.id)}
                        className="p-1.5 text-slate-400 hover:text-red-600 rounded-md hover:bg-red-50 transition-colors cursor-pointer"
                        title="Delete skill"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 2: Submit Skill Evidence & Evidence List */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Evidence Submission Form */}
          <div ref={evidenceFormRef} id="evidence-form-card" className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs scroll-mt-6">
            <div className="flex items-center gap-2 mb-1">
              <Award className="w-5 h-5 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-900">
                Submit Skill Evidence
              </h2>
            </div>
            <p className="text-xs text-slate-500 mb-5 leading-relaxed">
              Verify your competencies with empirical code repository commits, pull requests, or project portfolios.
            </p>

            <form onSubmit={handleSubmitEvidence} className="space-y-4">
              <div>
                <label
                  htmlFor="evidence-skill"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5"
                >
                  Skill Identifier
                </label>
                {catalogSkills.length > 0 ? (
                  <div className="space-y-2">
                    <select
                      id="evidence-skill"
                      value={evidenceSkillId}
                      onChange={(e) => setEvidenceSkillId(e.target.value)}
                      className="block w-full px-3 py-2 text-xs font-medium text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">-- Choose from Catalog or Missing Skills --</option>
                      {/* Combine missing skills and catalog */}
                      {missingList.map((s, idx) => {
                        const skKey = getSkillKey(s);
                        const label = getSkillLabel(s);
                        return (
                          <option key={`missing-${idx}`} value={skKey}>
                            Gap: {label} ({skKey})
                          </option>
                        );
                      })}
                      {catalogSkills.map((s) => {
                        const skKey = s.skill_id || String(s.id);
                        return (
                          <option key={s.id} value={skKey}>
                            {s.name} ({skKey})
                          </option>
                        );
                      })}
                    </select>
                    <input
                      type="text"
                      placeholder="Or enter custom skill ID (e.g. react, python, docker)"
                      value={evidenceSkillId}
                      onChange={(e) => setEvidenceSkillId(e.target.value)}
                      className="block w-full px-3 py-1.5 text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-md focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                ) : (
                  <input
                    id="evidence-skill"
                    type="text"
                    required
                    placeholder="e.g. fast-api, react, pytorch"
                    value={evidenceSkillId}
                    onChange={(e) => setEvidenceSkillId(e.target.value)}
                    className="block w-full px-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                )}
              </div>

              <div>
                <label
                  htmlFor="evidence-type"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5"
                >
                  Evidence Type
                </label>
                <select
                  id="evidence-type"
                  value={evidenceType}
                  onChange={(e) => setEvidenceType(e.target.value)}
                  className="block w-full px-3 py-2 text-xs font-medium text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="project">Project / GitHub Pull Request</option>
                  <option value="certification">Professional Certification</option>
                  <option value="assessment">Technical Assessment</option>
                  <option value="course_completed">Completed Coursework</option>
                  <option value="self_reported">Self Reported Skill</option>
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label
                    htmlFor="evidence-strength"
                    className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
                  >
                    Strength Indicator (1-10)
                  </label>
                  <span className="text-xs font-bold text-indigo-600 tabular-nums">
                    {evidenceStrength} / 10
                  </span>
                </div>
                <input
                  id="evidence-strength"
                  type="range"
                  min="1"
                  max="10"
                  value={evidenceStrength}
                  onChange={(e) => setEvidenceStrength(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
              </div>

              <div>
                <label
                  htmlFor="evidence-repo"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5"
                >
                  Repository / Project URL
                </label>
                <div className="relative rounded-lg shadow-2xs">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Github className="h-4 w-4" />
                  </div>
                  <input
                    id="evidence-repo"
                    type="url"
                    required
                    placeholder="https://github.com/organization/repo"
                    value={evidenceRepo}
                    onChange={(e) => setEvidenceRepo(e.target.value)}
                    className="block w-full pl-9 pr-3 py-2 text-xs text-slate-900 bg-white border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmittingEvidence}
                className="w-full mt-2 inline-flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-60 cursor-pointer"
              >
                {isSubmittingEvidence ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Submitting to ML Engine...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Submit Evidence Artifact</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Evidence Records List */}
          <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  Recorded Evidence Artifacts
                </h2>
                <p className="text-xs text-slate-500">
                  Previously verified artifacts submitted for student ID: {String(studentId)}
                </p>
              </div>
              <button
                type="button"
                onClick={fetchEvidence}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                Refresh
              </button>
            </div>

            <div className="flex-1 overflow-y-auto max-h-[420px]">
              {isLoadingEvidence ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : evidenceError ? (
                <Alert
                  type="error"
                  message={evidenceError}
                  onRetry={fetchEvidence}
                />
              ) : evidenceList.length === 0 ? (
                <EmptyState
                  icon={Award}
                  title="No verified evidence artifacts recorded yet."
                  description="Use the form on the left to submit your first repository or project proof."
                />
              ) : (
                <div className="divide-y divide-slate-100">
                  {evidenceList.map((item, idx) => (
                    <div key={item.id || idx} className="py-3 first:pt-0 last:pb-0 flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900">
                            {catalogSkills.find((s) => s.skill_id === item.skill_id || String(s.id) === item.skill_id)?.name || item.skill_id}
                          </span>
                          {catalogSkills.find((s) => s.skill_id === item.skill_id || String(s.id) === item.skill_id)?.name && (
                            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                              {item.skill_id}
                            </span>
                          )}
                          <span className="text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                            {item.evidence_type}
                          </span>
                          <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded tabular-nums">
                            Strength {typeof item.strength === 'number' ? `${item.strength}/10` : item.strength}
                          </span>
                        </div>

                        {item.metadata?.repo && (
                          <a
                            href={normalizeExternalUrl(item.metadata.repo)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-1 inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline truncate max-w-sm"
                          >
                            <Github className="w-3.5 h-3.5 shrink-0" />
                            <span className="truncate">{item.metadata.repo}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        )}
                      </div>

                      <div className="text-right shrink-0">
                        <span className="text-[11px] text-slate-400 tabular-nums">
                          {formatDate(item.created_at || item.metadata?.timestamp)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 3: Recommended Courses */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-6">
            <div>
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-indigo-600" />
                <h2 className="text-lg font-bold text-slate-900">
                  Recommended Curriculum Candidates
                </h2>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Targeted learning pathways designed to close your detected {selectedRole?.name || 'role'} gaps
              </p>
            </div>
          </div>

          {isLoadingCourses ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Skeleton className="h-44 rounded-xl" />
              <Skeleton className="h-44 rounded-xl" />
              <Skeleton className="h-44 rounded-xl" />
            </div>
          ) : coursesError ? (
            <Alert
              type="error"
              title="Course Candidates Error"
              message={coursesError}
            />
          ) : courseCandidates.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No curriculum candidates match this role gap yet."
              description="Either your current skillset satisfies the role or no aligned courses are indexed in the catalog."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {courseCandidates.map((candidate, idx) => (
                <div
                  key={candidate.course_id || idx}
                  className="p-5 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 hover:shadow-sm transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="text-[11px] font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                        ID: {candidate.course_id}
                      </span>
                      <span className="text-xs font-bold text-indigo-600 tabular-nums">
                        {formatPercentage(candidate.skill_coverage_score)} Coverage
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-slate-900 mb-1 leading-snug">
                      {candidate.course_name || candidate.title || `Curriculum #${candidate.course_id}`}
                    </h3>

                    {candidate.provider && (
                      <p className="text-xs text-slate-500 mb-3">
                        Provider: <strong className="text-slate-700">{candidate.provider}</strong>
                      </p>
                    )}

                    <div className="mt-3">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                        Skills Covered
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {(candidate.skills_covered && candidate.skills_covered.length > 0
                          ? candidate.skills_covered
                          : candidate.covered_personalized_skills && candidate.covered_personalized_skills.length > 0
                          ? candidate.covered_personalized_skills
                          : []
                        ).length > 0 ? (
                          (candidate.skills_covered && candidate.skills_covered.length > 0
                            ? candidate.skills_covered
                            : candidate.covered_personalized_skills || []
                          ).map((sc, sIdx) => {
                            const scName = catalogSkills.find((s) => s.skill_id === sc || String(s.id) === sc)?.name || sc;
                            return (
                              <span
                                key={sIdx}
                                className="text-[11px] bg-indigo-50 text-indigo-700 border border-indigo-100 px-2 py-0.5 rounded font-medium"
                              >
                                {scName}
                              </span>
                            );
                          })
                        ) : (
                          <span className="text-xs text-slate-400 italic">None listed</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                    <span>{candidate.duration || 'Self-paced'}</span>
                    <button
                      type="button"
                      onClick={() => handleOpenSyllabus(candidate)}
                      className="font-semibold text-indigo-600 hover:text-indigo-800 hover:underline inline-flex items-center gap-1 cursor-pointer bg-transparent border-none p-0 text-xs"
                    >
                      View Syllabus <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Syllabus Breakdown Modal */}
        {selectedSyllabusCandidate && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200"
            onClick={handleCloseSyllabus}
          >
            <div
              className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="flex items-start justify-between p-6 border-b border-slate-100 bg-slate-50/50">
                <div>
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
                      ID: {selectedSyllabusCandidate.course_id}
                    </span>
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-full">
                      {formatPercentage(selectedSyllabusCandidate.skill_coverage_score)} Role Coverage
                    </span>
                    {selectedSyllabusCandidate.duration && (
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" /> {selectedSyllabusCandidate.duration}
                      </span>
                    )}
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 leading-tight">
                    {selectedSyllabusCandidate.course_name || selectedSyllabusCandidate.title || `Curriculum #${selectedSyllabusCandidate.course_id}`}
                  </h3>
                  {selectedSyllabusCandidate.provider && (
                    <p className="text-xs text-slate-500 mt-1">
                      Offered by: <strong className="text-slate-700">{selectedSyllabusCandidate.provider}</strong>
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleCloseSyllabus}
                  className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Close syllabus modal"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-6">
                {isLoadingSyllabus ? (
                  <div className="space-y-4">
                    <Skeleton className="h-20 w-full rounded-xl" />
                    <Skeleton className="h-32 w-full rounded-xl" />
                  </div>
                ) : (
                  <>
                    {/* Course Overview & Syllabus Content */}
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <FileText className="w-4 h-4 text-indigo-600" />
                        Curriculum Overview & Syllabus Modules
                      </h4>
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 leading-relaxed space-y-2">
                        <p>
                          {syllabusDetails?.description ||
                            `Comprehensive curriculum designed to bridge technical industry competencies for the ${selectedRole?.name || 'target'} role. Structured into foundational theory, hands-on lab modules, and applied project deliverables.`}
                        </p>
                        {syllabusDetails?.department && (
                          <p className="text-slate-500 pt-2 border-t border-slate-200/80">
                            Academic Department: <span className="font-semibold text-slate-800">{syllabusDetails.department}</span>
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Explicitly Mapped Competencies */}
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <Award className="w-4 h-4 text-indigo-600" />
                        Explicitly Mapped Competencies ({syllabusSkills.length || (selectedSyllabusCandidate.skills_covered?.length || selectedSyllabusCandidate.covered_personalized_skills?.length || 0)})
                      </h4>
                      {syllabusSkills.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                          {syllabusSkills.map((cs, cIdx) => (
                            <div
                              key={cs.id || cIdx}
                              className="p-2.5 rounded-lg border border-indigo-100 bg-indigo-50/40 flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2">
                                <CheckCircle className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                                <span className="text-xs font-semibold text-slate-900">
                                  {cs.skill_name || cs.skill_id}
                                </span>
                              </div>
                              {cs.coverage_pct !== undefined && (
                                <span className="text-[11px] font-bold text-indigo-700 tabular-nums">
                                  {cs.coverage_pct}%
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {(selectedSyllabusCandidate.skills_covered ||
                            selectedSyllabusCandidate.covered_personalized_skills ||
                            []
                          ).map((sc, sIdx) => {
                            const scName = catalogSkills.find((s) => s.skill_id === sc || String(s.id) === sc)?.name || sc;
                            return (
                              <div
                                key={sIdx}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-100 text-xs font-medium text-indigo-800"
                              >
                                <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                                <span>{scName}</span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Targeted learning pathway for {selectedRole?.name || 'Target Role'}
                </span>
                <button
                  type="button"
                  onClick={handleCloseSyllabus}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PortalLayout>
  );
};
