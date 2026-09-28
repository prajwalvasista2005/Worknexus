import React, { useState, useEffect, useCallback } from 'react';
import { PortalLayout } from '../components/layout/PortalLayout';
import { useAuth } from '../contexts/AuthContext';
import { rolesApi } from '../api/roles';
import { skillsApi } from '../api/skills';
import { Role, TargetRoleCreate, Skill, SkillCreate } from '../types';
import { TableSkeleton, Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { Alert } from '../components/ui/Alert';
import { useToast } from '../contexts/ToastContext';
import {
  ShieldCheck,
  Briefcase,
  Layers,
  Plus,
  Trash2,
  RefreshCw,
  Search,
  CheckCircle2,
  X,
  Target,
} from 'lucide-react';

export const AdminPortal: React.FC = () => {
  const { user } = useAuth();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<'roles' | 'skills'>('roles');

  // --- Roles State ---
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [isLoadingRoles, setIsLoadingRoles] = useState(true);
  const [rolesError, setRolesError] = useState<string | null>(null);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [isCreatingRole, setIsCreatingRole] = useState(false);
  const [roleForm, setRoleForm] = useState<{ id: string; name: string; description: string; skill_ids: string }>({
    id: '',
    name: '',
    description: '',
    skill_ids: 'SKILL_PYTHON, SKILL_FASTAPI, SKILL_DOCKER',
  });

  // --- Skills State ---
  const [skills, setSkills] = useState<Skill[]>([]);
  const [isLoadingSkills, setIsLoadingSkills] = useState(true);
  const [skillsError, setSkillsError] = useState<string | null>(null);
  const [skillSearch, setSkillSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showSkillModal, setShowSkillModal] = useState(false);
  const [isCreatingSkill, setIsCreatingSkill] = useState(false);
  const [deletingSkillId, setDeletingSkillId] = useState<string | number | null>(null);
  const [skillForm, setSkillForm] = useState<{ skill_id: string; name: string; category: string; description: string }>({
    skill_id: '',
    name: '',
    category: 'Backend',
    description: '',
  });

  // Fetch Roles
  const fetchRoles = useCallback(async () => {
    setIsLoadingRoles(true);
    setRolesError(null);
    try {
      const data = await rolesApi.getRoles();
      setRoles(data || []);
      if (data && data.length > 0 && !selectedRole) {
        setSelectedRole(data[0]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve target career roles.';
      setRolesError(msg);
    } finally {
      setIsLoadingRoles(false);
    }
  }, [selectedRole]);

  // Fetch Skills
  const fetchSkills = useCallback(async () => {
    setIsLoadingSkills(true);
    setSkillsError(null);
    try {
      const data = await skillsApi.getSkills();
      setSkills(data || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve canonical skills catalog.';
      setSkillsError(msg);
    } finally {
      setIsLoadingSkills(false);
    }
  }, []);

  useEffect(() => {
    fetchRoles();
    fetchSkills();
  }, [fetchRoles, fetchSkills]);

  // Create Role Handler
  const handleCreateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roleForm.id.trim() || !roleForm.name.trim()) return;

    setIsCreatingRole(true);
    try {
      const skillIds = roleForm.skill_ids
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const payload: TargetRoleCreate = {
        id: roleForm.id.trim().toUpperCase(),
        name: roleForm.name.trim(),
        description: roleForm.description.trim(),
        skill_ids: skillIds,
      };

      const created = await rolesApi.createRole(payload);
      showToast('Career target role registered successfully!', 'success');
      setShowRoleModal(false);
      setRoleForm({ id: '', name: '', description: '', skill_ids: '' });
      await fetchRoles();
      setSelectedRole(created);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to register career target role.';
      showToast(msg, 'error');
    } finally {
      setIsCreatingRole(false);
    }
  };

  // Create Skill Handler
  const handleCreateSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!skillForm.skill_id.trim() || !skillForm.name.trim()) return;

    setIsCreatingSkill(true);
    try {
      const payload: SkillCreate = {
        skill_id: skillForm.skill_id.trim().toUpperCase(),
        name: skillForm.name.trim(),
        category: skillForm.category.trim(),
        description: skillForm.description.trim(),
      };

      await skillsApi.createSkill(payload);
      showToast('Canonical skill added to taxonomy!', 'success');
      setShowSkillModal(false);
      setSkillForm({ skill_id: '', name: '', category: 'Backend', description: '' });
      await fetchSkills();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add canonical skill.';
      showToast(msg, 'error');
    } finally {
      setIsCreatingSkill(false);
    }
  };

  // Delete Skill Handler
  const handleDeleteSkill = async (skillId: number | string) => {
    if (!confirm('Are you sure you want to remove this skill from the canonical taxonomy?')) {
      return;
    }

    setDeletingSkillId(skillId);
    try {
      await skillsApi.deleteSkill(skillId);
      showToast('Skill successfully deleted from catalog.', 'success');
      setSkills((prev) => prev.filter((s) => s.id !== skillId && s.skill_id !== skillId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete skill.';
      showToast(msg, 'error');
    } finally {
      setDeletingSkillId(null);
    }
  };

  // Filter skills
  const categories = Array.from(new Set(skills.map((s) => s.category).filter(Boolean))) as string[];
  const filteredSkills = skills.filter((s) => {
    const matchesSearch =
      (s.name || '').toLowerCase().includes(skillSearch.toLowerCase()) ||
      (s.skill_id || '').toLowerCase().includes(skillSearch.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || s.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <PortalLayout activeRole="Admin">
      <div className="space-y-8">
        {/* Header Banner */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4" /> Platform Governance Console
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                Canonical Taxonomy & Role Architecture
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Admin controls for canonical skill taxonomy definitions, target role profiles, and cross-platform taxonomies.
              </p>
            </div>

            <div className="flex items-center gap-2">
              {activeTab === 'roles' ? (
                <button
                  type="button"
                  onClick={() => setShowRoleModal(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-2xs cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create Target Role</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowSkillModal(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-2xs cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>New Canonical Skill</span>
                </button>
              )}
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 mt-6 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setActiveTab('roles')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                activeTab === 'roles'
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Briefcase className="w-4 h-4" />
              <span>Target Career Roles ({roles.length})</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('skills')}
              className={`flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                activeTab === 'skills'
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Canonical Skills Catalog ({skills.length})</span>
            </button>
          </div>
        </div>

        {/* --- Tab 1: Target Career Roles --- */}
        {activeTab === 'roles' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Roles Table */}
            <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col">
              <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Target className="w-5 h-5 text-indigo-600" />
                    Standard Target Roles
                  </h2>
                  <p className="text-xs text-slate-500">
                    Industry benchmark career tracks available for student goal setting
                  </p>
                </div>
                <button
                  type="button"
                  onClick={fetchRoles}
                  disabled={isLoadingRoles}
                  className="p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                  title="Refresh Roles"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingRoles ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {isLoadingRoles ? (
                <TableSkeleton rows={6} cols={3} />
              ) : rolesError ? (
                <Alert type="error" message={rolesError} onRetry={fetchRoles} />
              ) : roles.length === 0 ? (
                <EmptyState
                  icon={Briefcase}
                  title="No target career roles registered."
                  description="Click 'Create Target Role' to register standard roles."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[11px]">
                        <th className="py-2.5 px-3 font-semibold">Role Identifier</th>
                        <th className="py-2.5 px-3 font-semibold">Role Name</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Required Skills</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {roles.map((r) => {
                        const isSelected = selectedRole?.id === r.id;
                        const reqCount = r.required_skills?.length ?? 0;
                        return (
                          <tr
                            key={r.id}
                            onClick={() => setSelectedRole(r)}
                            className={`cursor-pointer transition-colors ${
                              isSelected ? 'bg-indigo-50/80 font-medium' : 'hover:bg-slate-50'
                            }`}
                          >
                            <td className="py-3 px-3 font-mono font-bold text-indigo-700">
                              {r.id}
                            </td>
                            <td className="py-3 px-3">
                              <div className="font-semibold text-slate-900">{r.name}</div>
                              {r.description && (
                                <div className="text-[11px] text-slate-500 truncate max-w-xs">
                                  {r.description}
                                </div>
                              )}
                            </td>
                            <td className="py-3 px-3 text-right tabular-nums text-slate-700 font-semibold">
                              {reqCount} skills
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Selected Role Detail */}
            <div className="lg:col-span-5">
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
                <div className="pb-3 border-b border-slate-100">
                  <h3 className="text-sm font-bold text-slate-900">Target Role Specification</h3>
                  <p className="text-[11px] text-slate-500">
                    Authoritative skill competencies associated with this position
                  </p>
                </div>

                {!selectedRole ? (
                  <div className="text-center py-8 text-xs text-slate-400">
                    Select a role from the left to view skill requirements.
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                        Identifier
                      </span>
                      <span className="text-sm font-mono font-bold text-indigo-700 mt-0.5 block">
                        {selectedRole.id}
                      </span>
                    </div>

                    <div>
                      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                        Role Title
                      </span>
                      <span className="text-base font-bold text-slate-900 mt-0.5 block">
                        {selectedRole.name}
                      </span>
                    </div>

                    {selectedRole.description && (
                      <div>
                        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                          Overview
                        </span>
                        <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                          {selectedRole.description}
                        </p>
                      </div>
                    )}

                    <div>
                      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-2">
                        Required Core Competencies ({selectedRole.required_skills?.length || 0})
                      </span>

                      {!selectedRole.required_skills || selectedRole.required_skills.length === 0 ? (
                        <p className="text-xs text-slate-400">No explicit skill requirements mapped.</p>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          {selectedRole.required_skills.map((skillId, idx) => (
                            <span
                              key={idx}
                              className="px-2.5 py-1 text-xs font-mono font-medium rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-100"
                            >
                              {skillId}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* --- Tab 2: Canonical Skills Catalog --- */}
        {activeTab === 'skills' && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Layers className="w-5 h-5 text-indigo-600" />
                  Canonical Skills Directory
                </h2>
                <p className="text-xs text-slate-500">
                  Authoritative taxonomy of verified engineering and technical skills
                </p>
              </div>

              {/* Search & Filter */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search skills..."
                    value={skillSearch}
                    onChange={(e) => setSkillSearch(e.target.value)}
                    className="pl-8 pr-3 py-1.5 text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="px-2.5 py-1.5 text-xs text-slate-700 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-hidden"
                >
                  <option value="all">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  onClick={fetchSkills}
                  disabled={isLoadingSkills}
                  className="p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                  title="Refresh Skills"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSkills ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {isLoadingSkills ? (
              <TableSkeleton rows={8} cols={4} />
            ) : skillsError ? (
              <Alert type="error" message={skillsError} onRetry={fetchSkills} />
            ) : filteredSkills.length === 0 ? (
              <EmptyState
                icon={Layers}
                title="No skills match your filters."
                description="Try refining your search query or add a new skill to the taxonomy."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[11px]">
                      <th className="py-2.5 px-3 font-semibold">Skill Code</th>
                      <th className="py-2.5 px-3 font-semibold">Skill Name</th>
                      <th className="py-2.5 px-3 font-semibold">Category</th>
                      <th className="py-2.5 px-3 font-semibold">Description</th>
                      <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredSkills.map((s) => {
                      const skillKey = s.id || s.skill_id;
                      const isDeleting = deletingSkillId === skillKey;
                      return (
                        <tr key={String(skillKey)} className="hover:bg-slate-50 transition-colors">
                          <td className="py-3 px-3 font-mono font-semibold text-indigo-700">
                            {s.skill_id || s.id}
                          </td>
                          <td className="py-3 px-3 font-semibold text-slate-900">
                            {s.name}
                          </td>
                          <td className="py-3 px-3">
                            <span className="px-2 py-0.5 text-[11px] font-medium rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                              {s.category || 'General'}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-500 max-w-sm truncate">
                            {s.description || '—'}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              type="button"
                              onClick={() => handleDeleteSkill(s.id)}
                              disabled={isDeleting}
                              className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors disabled:opacity-50 cursor-pointer"
                              title="Delete Skill"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Modal: Create Target Role */}
        {showRoleModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Target className="w-4 h-4 text-indigo-600" /> Create Career Target Role
                </h3>
                <button
                  type="button"
                  onClick={() => setShowRoleModal(false)}
                  className="p-1 text-slate-400 hover:text-slate-600 rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleCreateRole} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Role Identifier (ID)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. ROLE_DEVOPS_ENGINEER"
                    value={roleForm.id}
                    onChange={(e) => setRoleForm({ ...roleForm, id: e.target.value })}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-mono focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Role Display Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. DevOps & Infrastructure Engineer"
                    value={roleForm.name}
                    onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Description
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Overview of core technical responsibilities..."
                    value={roleForm.description}
                    onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Required Skill Codes (comma separated)
                  </label>
                  <input
                    type="text"
                    placeholder="SKILL_DOCKER, SKILL_KUBERNETES, SKILL_AWS"
                    value={roleForm.skill_ids}
                    onChange={(e) => setRoleForm({ ...roleForm, skill_ids: e.target.value })}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-mono focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowRoleModal(false)}
                    className="px-3 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isCreatingRole}
                    className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {isCreatingRole ? 'Registering...' : 'Register Target Role'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Create Canonical Skill */}
        {showSkillModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-indigo-600" /> Add Canonical Skill
                </h3>
                <button
                  type="button"
                  onClick={() => setShowSkillModal(false)}
                  className="p-1 text-slate-400 hover:text-slate-600 rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleCreateSkill} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Canonical Skill Code
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. SKILL_TERRAFORM"
                    value={skillForm.skill_id}
                    onChange={(e) => setSkillForm({ ...skillForm, skill_id: e.target.value })}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-mono focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Skill Display Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Terraform Infrastructure as Code"
                    value={skillForm.name}
                    onChange={(e) => setSkillForm({ ...skillForm, name: e.target.value })}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Category
                  </label>
                  <select
                    value={skillForm.category}
                    onChange={(e) => setSkillForm({ ...skillForm, category: e.target.value })}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Backend">Backend</option>
                    <option value="Frontend">Frontend</option>
                    <option value="Cloud/DevOps">Cloud/DevOps</option>
                    <option value="Data Science">Data Science</option>
                    <option value="Security">Security</option>
                    <option value="System Design">System Design</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Description
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Skill competence summary..."
                    value={skillForm.description}
                    onChange={(e) => setSkillForm({ ...skillForm, description: e.target.value })}
                    className="w-full text-xs text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowSkillModal(false)}
                    className="px-3 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isCreatingSkill}
                    className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {isCreatingSkill ? 'Adding...' : 'Add to Taxonomy'}
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
