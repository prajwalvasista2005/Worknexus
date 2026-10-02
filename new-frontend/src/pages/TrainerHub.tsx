import React, { useState, useEffect, useCallback } from 'react';
import { PortalLayout } from '../components/layout/PortalLayout';
import { useAuth } from '../contexts/AuthContext';
import { mlApi } from '../api/ml';
import { trainerApi, TrainerIntervention } from '../api/trainers';
import { DemandData, EvidenceSummary, SkillExtractionItem } from '../types';
import { TableSkeleton, Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { Alert } from '../components/ui/Alert';
import { formatPercentage, formatNumber } from '../utils/formatters';
import {
  LineChart,
  TrendingUp,
  Activity,
  Award,
  RefreshCw,
  Search,
  Cpu,
  Sparkles,
  Layers,
  Database,
  ArrowRight,
  CheckCircle2,
  Briefcase,
  Send,
} from 'lucide-react';

export const TrainerHub: React.FC = () => {
  const { user } = useAuth();

  // Active Tab state: 'demand' | 'extractor' | 'recommendations' | 'evidence' | 'interventions'
  const [activeTab, setActiveTab] = useState<'demand' | 'extractor' | 'recommendations' | 'evidence' | 'interventions'>('demand');

  // --- Tab 1: Demand & Evidence Summary ---
  const [demandList, setDemandList] = useState<DemandData[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<DemandData | null>(null);
  const [evidenceSummary, setEvidenceSummary] = useState<EvidenceSummary | null>(null);
  const [isLoadingDemand, setIsLoadingDemand] = useState(true);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);
  const [demandError, setDemandError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // --- Tab 2: AI Skill Extractor ---
  const [extractInput, setExtractInput] = useState(
    'Students will design and deploy scalable microservices using Python, FastAPI, Docker containers, and Kubernetes orchestration with PostgreSQL and Redis backends.'
  );
  const [extractedSkills, setExtractedSkills] = useState<SkillExtractionItem[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);

  // --- Tab 3: Curricular Recommendations ---
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
  const [recsError, setRecsError] = useState<string | null>(null);

  // --- Tab 4: Multi-Signal Evidence ---
  const [evidenceData, setEvidenceData] = useState<any | null>(null);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  // --- Tab 5: Trainer Interventions (Phase 1 — Loop D) ---
  const [interventions, setInterventions] = useState<TrainerIntervention[]>([]);
  const [isLoadingInterventions, setIsLoadingInterventions] = useState(false);
  const [interventionsError, setInterventionsError] = useState<string | null>(null);
  const [interventionSuccess, setInterventionSuccess] = useState<string | null>(null);
  const [isSubmittingIntervention, setIsSubmittingIntervention] = useState(false);
  // Form fields
  const [formStudentId, setFormStudentId] = useState('');
  const [formSkillId, setFormSkillId] = useState('');
  const [formInterventionType, setFormInterventionType] = useState('coaching');
  const [formNotes, setFormNotes] = useState('');
  const [formProficiencyBefore, setFormProficiencyBefore] = useState('');
  const [formProficiencyAfter, setFormProficiencyAfter] = useState('');

  // Fetch top 12 skill demand rankings
  const fetchDemand = useCallback(async () => {
    setIsLoadingDemand(true);
    setDemandError(null);
    try {
      const data = await mlApi.getDemandData(12);
      setDemandList(data || []);
      if (data && data.length > 0) {
        setSelectedSkill(data[0]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve market demand data.';
      setDemandError(msg);
    } finally {
      setIsLoadingDemand(false);
    }
  }, []);

  useEffect(() => {
    fetchDemand();
  }, [fetchDemand]);

  // When a skill is selected, fetch evidence summary
  useEffect(() => {
    if (!selectedSkill) {
      setEvidenceSummary(null);
      return;
    }

    const loadSummary = async () => {
      setIsLoadingSummary(true);
      setSummaryError(null);
      try {
        const summary = await mlApi.getEvidenceSummary(selectedSkill.skill_id);
        setEvidenceSummary(summary);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Evidence summary unavailable for this skill.';
        setSummaryError(msg);
        setEvidenceSummary(null);
      } finally {
        setIsLoadingSummary(false);
      }
    };

    loadSummary();
  }, [selectedSkill]);

  // Handle Skill Extraction
  const handleExtractSkills = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!extractInput.trim()) return;

    setIsExtracting(true);
    setExtractError(null);
    try {
      const res = await mlApi.extractSkills(extractInput.trim());
      setExtractedSkills(res.skills || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Skill extraction pipeline failed.';
      setExtractError(msg);
    } finally {
      setIsExtracting(false);
    }
  };

  // Fetch Recommendations
  const fetchRecommendations = useCallback(async () => {
    setIsLoadingRecs(true);
    setRecsError(null);
    try {
      const res = await mlApi.getRecommendations('live');
      const recs = res.recommended_skills || res.recommendations || [];
      setRecommendations(Array.isArray(recs) ? recs : []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch recommendations.';
      setRecsError(msg);
    } finally {
      setIsLoadingRecs(false);
    }
  }, []);

  // Fetch Multi-Signal Evidence
  const fetchEvidence = useCallback(async () => {
    setIsLoadingEvidence(true);
    setEvidenceError(null);
    try {
      const res = await mlApi.getEvidence('live');
      setEvidenceData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch multi-signal evidence.';
      setEvidenceError(msg);
    } finally {
      setIsLoadingEvidence(false);
    }
  }, []);

  // Fetch trainer's own intervention history
  const fetchInterventions = useCallback(async () => {
    setIsLoadingInterventions(true);
    setInterventionsError(null);
    try {
      const data = await trainerApi.getMyInterventions();
      setInterventions(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch intervention history.';
      setInterventionsError(msg);
    } finally {
      setIsLoadingInterventions(false);
    }
  }, []);

  // Submit a new intervention
  const handleSubmitIntervention = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formStudentId.trim() || !formSkillId.trim()) return;

    const studentIdNum = parseInt(formStudentId.trim(), 10);
    const skillIdNum = parseInt(formSkillId.trim(), 10);
    if (isNaN(studentIdNum) || isNaN(skillIdNum)) {
      setInterventionsError('Student ID and Skill ID must be valid integers.');
      return;
    }

    setIsSubmittingIntervention(true);
    setInterventionsError(null);
    setInterventionSuccess(null);

    try {
      const created = await trainerApi.createIntervention({
        student_id: studentIdNum,
        skill_id: skillIdNum,
        intervention_type: formInterventionType,
        notes: formNotes.trim() || undefined,
        proficiency_before: formProficiencyBefore || undefined,
        proficiency_after: formProficiencyAfter || undefined,
      });
      setInterventionSuccess(
        `Intervention #${created.id} created successfully. Readiness recalculated for student ${created.student_id}.`
      );
      // Reset form
      setFormStudentId('');
      setFormSkillId('');
      setFormInterventionType('coaching');
      setFormNotes('');
      setFormProficiencyBefore('');
      setFormProficiencyAfter('');
      // Refresh history
      fetchInterventions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create intervention.';
      setInterventionsError(msg);
    } finally {
      setIsSubmittingIntervention(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'recommendations' && recommendations.length === 0) {
      fetchRecommendations();
    } else if (activeTab === 'evidence' && !evidenceData) {
      fetchEvidence();
    } else if (activeTab === 'interventions' && interventions.length === 0) {
      fetchInterventions();
    }
  }, [activeTab, fetchRecommendations, fetchEvidence, fetchInterventions, recommendations.length, evidenceData, interventions.length]);

  // Filter skills by search query
  const filteredDemand = demandList.filter((item) => {
    const query = searchTerm.toLowerCase();
    const idMatch = (item.skill_id || '').toLowerCase().includes(query);
    const nameMatch = (item.skill_name || '').toLowerCase().includes(query);
    return idMatch || nameMatch;
  });

  return (
    <PortalLayout activeRole="Trainer">
      <div className="space-y-8">
        {/* Header Banner */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">
                Trainer & Workforce Intelligence Hub
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                Labour-Market Skill Demand & Evidence Telemetry
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Real-time tracking of high-velocity technical skills, AI skill extraction sandbox, and verified student proof distributions.
              </p>
            </div>
            {activeTab === 'demand' && (
              <button
                type="button"
                onClick={fetchDemand}
                disabled={isLoadingDemand}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingDemand ? 'animate-spin' : ''}`} />
                <span>Refresh Demand Index</span>
              </button>
            )}
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 mt-6 pt-4 border-t border-slate-100 overflow-x-auto">
            <button
              type="button"
              onClick={() => setActiveTab('demand')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                activeTab === 'demand'
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              <span>Market Demand & Telemetry</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('extractor')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                activeTab === 'extractor'
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Cpu className="w-4 h-4" />
              <span>AI Skill Extractor Sandbox</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('recommendations')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                activeTab === 'recommendations'
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Curricular Recommendations</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('evidence')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                activeTab === 'evidence'
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Multi-Signal Matrix</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('interventions')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                activeTab === 'interventions'
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Briefcase className="w-4 h-4" />
              <span>Assign Intervention</span>
            </button>
          </div>
        </div>

        {/* Tab 1: Market Demand Rankings & Evidence Summary */}
        {activeTab === 'demand' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left Column: Top Demand Rankings */}
            <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100 mb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-indigo-600" />
                    Top Market Skill Rankings
                  </h2>
                  <p className="text-xs text-slate-500">
                    Aggregated demand from active employer requisitions (Top 12)
                  </p>
                </div>

                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Filter skills..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-8 pr-3 py-1.5 text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {isLoadingDemand ? (
                <TableSkeleton rows={8} cols={5} />
              ) : demandError ? (
                <Alert type="error" message={demandError} onRetry={fetchDemand} />
              ) : filteredDemand.length === 0 ? (
                <EmptyState
                  icon={LineChart}
                  title="No market demand data available."
                  description="Demand models have not yet aggregated requisition telemetry for this query."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[11px]">
                        <th className="py-2.5 px-3 font-semibold">Rank</th>
                        <th className="py-2.5 px-3 font-semibold">Skill Identifier</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Demand Score</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Growth Rate</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Postings</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredDemand.map((item, index) => {
                        const rank = item.rank ?? item.skill_ranking ?? index + 1;
                        const isSelected = selectedSkill?.skill_id === item.skill_id;
                        const growthDisplay = formatPercentage(item.market_growth_rate, '—');
                        const postingsDisplay =
                          item.active_postings_count !== null &&
                          item.active_postings_count !== undefined &&
                          !Number.isNaN(Number(item.active_postings_count))
                            ? formatNumber(item.active_postings_count)
                            : '—';

                        return (
                          <tr
                            key={item.skill_id || index}
                            onClick={() => setSelectedSkill(item)}
                            className={`cursor-pointer transition-colors ${
                              isSelected
                                ? 'bg-indigo-50/80 font-medium'
                                : 'hover:bg-slate-50'
                            }`}
                          >
                            <td className="py-3 px-3 tabular-nums font-semibold text-slate-700">
                              #{rank}
                            </td>
                            <td className="py-3 px-3">
                              <div className="font-semibold text-slate-900">
                                {item.skill_name || item.skill_id}
                              </div>
                              {item.skill_name && item.skill_name !== item.skill_id && (
                                <div className="text-[10px] text-slate-400 font-mono">
                                  {item.skill_id}
                                </div>
                              )}
                            </td>
                            <td className="py-3 px-3 text-right tabular-nums font-bold text-indigo-700">
                              {formatNumber(item.demand_score)}
                            </td>
                            <td className="py-3 px-3 text-right tabular-nums font-medium text-slate-700">
                              {growthDisplay}
                            </td>
                            <td className="py-3 px-3 text-right tabular-nums text-slate-600">
                              {postingsDisplay}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Right Column: Selected Skill Evidence Summary */}
            <div className="lg:col-span-5 space-y-6">
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
                  <div className="flex items-center gap-2">
                    <Award className="w-5 h-5 text-indigo-600" />
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">
                        Skill Evidence Telemetry
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        Verified artifact breakdown for target competency
                      </p>
                    </div>
                  </div>

                  {selectedSkill && (
                    <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {selectedSkill.skill_name || selectedSkill.skill_id}
                    </span>
                  )}
                </div>

                {!selectedSkill ? (
                  <div className="text-center py-8 text-xs text-slate-400">
                    Select a skill row from the demand table to view evidence telemetry.
                  </div>
                ) : isLoadingSummary ? (
                  <div className="space-y-4">
                    <Skeleton className="h-20 w-full rounded-xl" />
                    <div className="grid grid-cols-3 gap-3">
                      <Skeleton className="h-16 rounded-xl" />
                      <Skeleton className="h-16 rounded-xl" />
                      <Skeleton className="h-16 rounded-xl" />
                    </div>
                    <Skeleton className="h-24 w-full rounded-xl" />
                  </div>
                ) : summaryError ? (
                  <Alert
                    type="warning"
                    title="Evidence Summary Not Indexed"
                    message={summaryError}
                  />
                ) : !evidenceSummary ? (
                  <EmptyState
                    icon={Activity}
                    title="No evidence artifacts recorded."
                    description="No verified repositories or submissions currently linked to this skill."
                  />
                ) : (
                  <div className="space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                          Total Evidence Artifacts
                        </span>
                        <span className="text-2xl font-bold text-slate-900 tabular-nums block mt-1">
                          {formatNumber(
                            evidenceSummary.total_artifacts ?? evidenceSummary.total_evidence_artifacts ?? 0
                          )}
                        </span>
                        <span className="text-[10px] text-slate-400 mt-0.5 block">
                          Verified PRs, repos & assessments
                        </span>
                      </div>

                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                          Employer Signal Weight
                        </span>
                        <span className="text-2xl font-bold text-indigo-700 tabular-nums block mt-1">
                          {formatPercentage(evidenceSummary.employer_signal_weight)}
                        </span>
                        <span className="text-[10px] text-slate-400 mt-0.5 block">
                          Relevance across active hiring
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-3">
                        Artifact Proficiency Distribution
                      </span>

                      <div className="grid grid-cols-3 gap-3 text-center">
                        <div className="p-3 rounded-xl border border-emerald-200 bg-emerald-50/40">
                          <span className="text-xs font-semibold text-emerald-800 block">
                            Advanced
                          </span>
                          <span className="text-lg font-bold text-emerald-900 tabular-nums block mt-1">
                            {formatNumber(evidenceSummary.advanced_count)}
                          </span>
                          <span className="text-[10px] text-emerald-700 mt-0.5 block">
                            Production grade
                          </span>
                        </div>

                        <div className="p-3 rounded-xl border border-indigo-200 bg-indigo-50/40">
                          <span className="text-xs font-semibold text-indigo-800 block">
                            Intermediate
                          </span>
                          <span className="text-lg font-bold text-indigo-900 tabular-nums block mt-1">
                            {formatNumber(evidenceSummary.intermediate_count)}
                          </span>
                          <span className="text-[10px] text-indigo-700 mt-0.5 block">
                            Proficient projects
                          </span>
                        </div>

                        <div className="p-3 rounded-xl border border-slate-200 bg-slate-50">
                          <span className="text-xs font-semibold text-slate-700 block">
                            Basic
                          </span>
                          <span className="text-lg font-bold text-slate-900 tabular-nums block mt-1">
                            {formatNumber(evidenceSummary.basic_count)}
                          </span>
                          <span className="text-[10px] text-slate-500 mt-0.5 block">
                            Foundational proof
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: AI Skill Extractor Sandbox */}
        {activeTab === 'extractor' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Cpu className="w-5 h-5 text-indigo-600" />
                NLP Skill Extractor Sandbox
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Test the SkillMesh NLP engine by parsing unstructured curricula, job postings, or syllabi into canonical skill codes.
              </p>
            </div>

            <form onSubmit={handleExtractSkills} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Input Free-Form Text
                </label>
                <textarea
                  rows={4}
                  value={extractInput}
                  onChange={(e) => setExtractInput(e.target.value)}
                  placeholder="Paste syllabus modules, course prerequisites, or hiring requirements..."
                  className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-xl p-3 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500 font-mono"
                  required
                />
              </div>

              {extractError && <Alert type="error" message={extractError} />}

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isExtracting || !extractInput.trim()}
                  className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {isExtracting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Extracting Canonical Skills...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Extract Skills (ML Pipeline)</span>
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Extracted Skills Output */}
            <div className="pt-4 border-t border-slate-100">
              <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">
                Detected Canonical Competencies ({extractedSkills.length})
              </h3>

              {extractedSkills.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  Submit text above to parse canonical skill entities.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {extractedSkills.map((item, idx) => {
                    const confidencePct = Math.round((item.confidence_score ?? 1.0) * 100);
                    return (
                      <div
                        key={idx}
                        className="p-3 rounded-xl border border-indigo-100 bg-indigo-50/30 flex items-center justify-between"
                      >
                        <div>
                          <span className="text-xs font-bold text-slate-900 font-mono block">
                            {item.skill_id}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            Confidence: {confidencePct}%
                          </span>
                        </div>
                        <div className="w-12 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-indigo-600 h-1.5 rounded-full"
                            style={{ width: `${confidencePct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Curricular Recommendations */}
        {activeTab === 'recommendations' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-600" />
                  Labour Market Skill Recommendations
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  AI-evaluated high-priority technical skills bridging academic curricula with real employer requisition demand.
                </p>
              </div>
              <button
                type="button"
                onClick={fetchRecommendations}
                disabled={isLoadingRecs}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingRecs ? 'animate-spin' : ''}`} />
                <span>Re-evaluate</span>
              </button>
            </div>

            {isLoadingRecs ? (
              <TableSkeleton rows={6} cols={4} />
            ) : recsError ? (
              <Alert type="error" message={recsError} onRetry={fetchRecommendations} />
            ) : recommendations.length === 0 ? (
              <EmptyState
                icon={Sparkles}
                title="No current recommendations generated."
                description="Curriculum coverage matches current market demand thresholds."
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {recommendations.map((rec: any, idx: number) => {
                  const skillId = rec.skill_id || rec.skill || `SKILL_${idx + 1}`;
                  const score = rec.priority_score ?? rec.score ?? rec.demand_score ?? 85;
                  const reason = rec.reason || rec.recommendation_reason || 'High requisition velocity across active software postings';

                  return (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:border-indigo-300 transition-colors flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-mono font-bold text-indigo-700 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded">
                            {skillId}
                          </span>
                          <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                            Score: {typeof score === 'number' ? score.toFixed(1) : score}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 line-clamp-3 mt-2">{reason}</p>
                      </div>

                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                        <span className="flex items-center gap-1 text-indigo-600 font-medium">
                          <CheckCircle2 className="w-3 h-3" /> Recommended
                        </span>
                        <span>Level: Core</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Multi-Signal Evidence Telemetry */}
        {activeTab === 'evidence' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-indigo-600" />
                  Multi-Signal Evidence Dataset Telemetry
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Synthesized multi-source signals combining live job postings with verified candidate submissions.
                </p>
              </div>
              <button
                type="button"
                onClick={fetchEvidence}
                disabled={isLoadingEvidence}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingEvidence ? 'animate-spin' : ''}`} />
                <span>Refresh Telemetry</span>
              </button>
            </div>

            {isLoadingEvidence ? (
              <TableSkeleton rows={8} cols={4} />
            ) : evidenceError ? (
              <Alert type="error" message={evidenceError} onRetry={fetchEvidence} />
            ) : !evidenceData ? (
              <EmptyState
                icon={Database}
                title="No evidence dataset available."
                description="Evidence aggregations will populate as more candidates submit verified proofs."
              />
            ) : (
              <div className="space-y-6">
                {/* Summary banner */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-100">
                    <span className="text-[11px] font-semibold text-indigo-600 uppercase tracking-wider block">
                      Pipeline Mode
                    </span>
                    <span className="text-lg font-bold text-indigo-900 mt-1 block">
                      {evidenceData.mode || 'Live Dynamic'}
                    </span>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                      Total Tracked Signals
                    </span>
                    <span className="text-lg font-bold text-slate-900 mt-1 block">
                      {evidenceData.total_skills_evaluated ?? (evidenceData.multi_signal_skills?.length || 0)}
                    </span>
                  </div>
                  <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-100">
                    <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider block">
                      Multi-Source Confidence
                    </span>
                    <span className="text-lg font-bold text-emerald-900 mt-1 block">
                      {evidenceData.confidence_threshold ? `${evidenceData.confidence_threshold * 100}%` : 'Authoritative'}
                    </span>
                  </div>
                </div>

                {/* Signals Table */}
                {Array.isArray(evidenceData.multi_signal_skills) && evidenceData.multi_signal_skills.length > 0 && (
                  <div className="overflow-x-auto border border-slate-100 rounded-xl">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[11px]">
                          <th className="py-2.5 px-3 font-semibold">Skill Code</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Job Postings</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Demand Share</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Combined Signal Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {evidenceData.multi_signal_skills.map((s: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="py-3 px-3 font-mono font-semibold text-slate-900">
                              {s.skill_id}
                            </td>
                            <td className="py-3 px-3 text-right tabular-nums text-slate-700">
                              {s.job_count ?? 0}
                            </td>
                            <td className="py-3 px-3 text-right tabular-nums text-slate-700">
                              {formatPercentage(s.demand_share)}
                            </td>
                            <td className="py-3 px-3 text-right tabular-nums font-bold text-indigo-600">
                              {formatPercentage(s.combined_score ?? s.demand_share)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab 5: Assign Intervention — Phase 1 Loop D */}
        {activeTab === 'interventions' && (
          <div className="space-y-8">
            {/* Assignment Form */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
              <div className="border-b border-slate-100 pb-4 mb-6">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-indigo-600" />
                  Assign Student Intervention
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Create a coaching, assessment, or mentoring intervention for a student skill. Triggers automatic readiness recalculation.
                </p>
              </div>

              {interventionsError && (
                <Alert type="error" message={interventionsError} />
              )}
              {interventionSuccess && (
                <div className="mb-4 flex items-start gap-2 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span>{interventionSuccess}</span>
                </div>
              )}

              <form onSubmit={handleSubmitIntervention} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Student ID */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Student ID <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    value={formStudentId}
                    onChange={(e) => setFormStudentId(e.target.value)}
                    placeholder="e.g. 42"
                    required
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                {/* Skill ID */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Skill ID <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    value={formSkillId}
                    onChange={(e) => setFormSkillId(e.target.value)}
                    placeholder="e.g. 7"
                    required
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                {/* Intervention Type */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Intervention Type
                  </label>
                  <select
                    value={formInterventionType}
                    onChange={(e) => setFormInterventionType(e.target.value)}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="coaching">Coaching</option>
                    <option value="assessment">Assessment</option>
                    <option value="workshop">Workshop</option>
                    <option value="mentoring">Mentoring</option>
                    <option value="course_assignment">Course Assignment</option>
                    <option value="feedback">Feedback</option>
                  </select>
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Notes
                  </label>
                  <input
                    type="text"
                    value={formNotes}
                    onChange={(e) => setFormNotes(e.target.value)}
                    placeholder="Optional notes for the student..."
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                {/* Proficiency Before */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Proficiency Before
                  </label>
                  <select
                    value={formProficiencyBefore}
                    onChange={(e) => setFormProficiencyBefore(e.target.value)}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">— Not specified —</option>
                    <option value="basic">Basic</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>

                {/* Proficiency After */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Proficiency After
                  </label>
                  <select
                    value={formProficiencyAfter}
                    onChange={(e) => setFormProficiencyAfter(e.target.value)}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">— Not specified —</option>
                    <option value="basic">Basic</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>

                {/* Submit */}
                <div className="md:col-span-2 flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={isSubmittingIntervention || !formStudentId.trim() || !formSkillId.trim()}
                    className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
                  >
                    {isSubmittingIntervention ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Submitting...</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-3.5 h-3.5" />
                        <span>Assign Intervention</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* Intervention History Table */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-indigo-600" />
                    My Intervention History
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">All interventions you have assigned, newest first.</p>
                </div>
                <button
                  type="button"
                  onClick={fetchInterventions}
                  disabled={isLoadingInterventions}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors cursor-pointer"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingInterventions ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>

              {isLoadingInterventions ? (
                <TableSkeleton rows={5} cols={6} />
              ) : interventionsError && interventions.length === 0 ? (
                <Alert type="error" message={interventionsError} onRetry={fetchInterventions} />
              ) : interventions.length === 0 ? (
                <EmptyState
                  icon={Briefcase}
                  title="No interventions assigned yet."
                  description="Use the form above to assign your first student intervention."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[11px]">
                        <th className="py-2.5 px-3 font-semibold">Date</th>
                        <th className="py-2.5 px-3 font-semibold">Student ID</th>
                        <th className="py-2.5 px-3 font-semibold">Skill</th>
                        <th className="py-2.5 px-3 font-semibold">Type</th>
                        <th className="py-2.5 px-3 font-semibold">Proficiency</th>
                        <th className="py-2.5 px-3 font-semibold text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {interventions.map((iv) => {
                        const dateStr = iv.created_at
                          ? new Date(iv.created_at).toLocaleDateString('en-GB', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric',
                            })
                          : '—';
                        const profChange =
                          iv.proficiency_before && iv.proficiency_after
                            ? `${iv.proficiency_before} → ${iv.proficiency_after}`
                            : iv.proficiency_after || iv.proficiency_before || '—';
                        return (
                          <tr key={iv.id} className="hover:bg-slate-50">
                            <td className="py-3 px-3 tabular-nums text-slate-600">{dateStr}</td>
                            <td className="py-3 px-3 font-semibold text-slate-900">#{iv.student_id}</td>
                            <td className="py-3 px-3">
                              <div className="font-semibold text-slate-900">{iv.skill_name || '—'}</div>
                              {iv.skill_code && (
                                <div className="text-[10px] text-slate-400 font-mono">{iv.skill_code}</div>
                              )}
                            </td>
                            <td className="py-3 px-3">
                              <span className="inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100 capitalize">
                                {iv.intervention_type.replace('_', ' ')}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-slate-600 capitalize">{profChange}</td>
                            <td className="py-3 px-3 text-center">
                              {iv.is_verified ? (
                                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700">
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  Verified
                                </span>
                              ) : (
                                <span className="inline-block text-[10px] font-semibold text-amber-600 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-full">
                                  Pending
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </PortalLayout>
  );
};
