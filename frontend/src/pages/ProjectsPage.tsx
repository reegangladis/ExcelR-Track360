import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ProjectListItem, ProjectItem, TrackItem } from '@/types';
import {
  FolderGit2,
  Plus,
  Search,
  Layers,
  Users,
  Target,
  Clock,
  AlertCircle,
  Loader2,
  X,
  ChevronRight,
  Sparkles,
  Trash2,
} from 'lucide-react';

export const ProjectsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Filters State
  const [selectedTier, setSelectedTier] = useState<string>('');
  const [selectedTrack, setSelectedTrack] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 12;

  // Modals State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedProjectForDetail, setSelectedProjectForDetail] = useState<string | null>(null);

  // Queries
  const { data: tracks } = useQuery<TrackItem[]>({
    queryKey: ['tracks'],
    queryFn: () => api.getTracks(),
  });

  const { data: projectData, isLoading: isProjectsLoading } = useQuery({
    queryKey: ['projects', selectedTrack, selectedTier, searchTerm, page],
    queryFn: () =>
      api.getProjects({
        track_id: selectedTrack || undefined,
        tier: selectedTier || undefined,
        search: searchTerm || undefined,
        page,
        page_size: pageSize,
      }),
  });

  const { data: projectDetail, isLoading: isDetailLoading } = useQuery<ProjectItem | null>({
    queryKey: ['projectDetail', selectedProjectForDetail],
    queryFn: () => (selectedProjectForDetail ? api.getProject(selectedProjectForDetail) : null),
    enabled: !!selectedProjectForDetail,
  });

  // Create Project Form State
  const [formData, setFormData] = useState({
    track_id: '',
    code: '',
    title: '',
    description: '',
    tier: 'TIER_1_FOUNDATIONAL',
    complexity: 'MEDIUM',
    min_team_size: 2,
    max_team_size: 5,
    passing_score: 60,
  });

  const [milestoneRows, setMilestoneRows] = useState<
    Array<{ sequence_order: number; title: string; description: string; weight_percentage: number }>
  >([
    { sequence_order: 1, title: 'Milestone 1: Architecture & Data Schema', description: 'Entity models, SRS, and schema design.', weight_percentage: 30 },
    { sequence_order: 2, title: 'Milestone 2: Core Processing & Pipelines', description: 'ETL execution, business logic, and test coverage.', weight_percentage: 40 },
    { sequence_order: 3, title: 'Milestone 3: Deployment & Presentation', description: 'Docker deployment, documentation, and demo walk-through.', weight_percentage: 30 },
  ]);

  const [formError, setFormError] = useState<string | null>(null);

  const totalMilestoneWeight = milestoneRows.reduce((sum, m) => sum + (Number(m.weight_percentage) || 0), 0);
  const isWeightValid = Math.abs(totalMilestoneWeight - 100.0) < 0.01;

  // Create Project Mutation
  const createProjectMutation = useMutation({
    mutationFn: (payload: any) => api.createProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setIsCreateModalOpen(false);
      setFormData({
        track_id: '',
        code: '',
        title: '',
        description: '',
        tier: 'TIER_1_FOUNDATIONAL',
        complexity: 'MEDIUM',
        min_team_size: 2,
        max_team_size: 5,
        passing_score: 60,
      });
      setFormError(null);
    },
    onError: (err: any) => {
      setFormError(err.message || 'Failed to create project specification.');
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formData.track_id) {
      setFormError('Please select a course track.');
      return;
    }
    if (!isWeightValid) {
      setFormError(`Milestone weights must sum to 100.0% (current sum: ${totalMilestoneWeight}%).`);
      return;
    }

    createProjectMutation.mutate({
      ...formData,
      deliverable_specs: [
        { key: 'git_repo', title: 'Source Code Repository', deliverable_type: 'GIT_REPO', is_required: true },
        { key: 'documentation', title: 'Technical Architecture Doc', deliverable_type: 'DOCUMENTATION', is_required: true },
        { key: 'demo', title: 'Deployment / Video Demo', deliverable_type: 'DEMO_URL', is_required: false },
      ],
      rubric_template: [
        { key: 'architecture', title: 'System Architecture & Schema', max_points: 30 },
        { key: 'implementation', title: 'Implementation & Code Quality', max_points: 50 },
        { key: 'presentation', title: 'Presentation & Deployment', max_points: 20 },
      ],
      milestones: milestoneRows,
    });
  };

  const addMilestoneRow = () => {
    const nextSeq = milestoneRows.length + 1;
    setMilestoneRows([
      ...milestoneRows,
      {
        sequence_order: nextSeq,
        title: `Milestone ${nextSeq}: Milestone Deliverable`,
        description: '',
        weight_percentage: 10,
      },
    ]);
  };

  const removeMilestoneRow = (idx: number) => {
    setMilestoneRows(milestoneRows.filter((_, i) => i !== idx));
  };

  const getTierBadge = (tier: string) => {
    switch (tier) {
      case 'TIER_1_FOUNDATIONAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
            Tier 1: Foundational
          </span>
        );
      case 'TIER_2_INTERMEDIATE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-50 text-indigo-800 border border-indigo-200">
            Tier 2: Intermediate
          </span>
        );
      case 'TIER_3_CAPSTONE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-50 text-purple-800 border border-purple-200">
            <Sparkles className="w-3 h-3 text-purple-600" /> Tier 3: Capstone
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700">
            {tier}
          </span>
        );
    }
  };

  const getComplexityBadge = (complexity: string) => {
    switch (complexity) {
      case 'LOW':
        return <span className="text-[11px] font-semibold text-emerald-700">Low</span>;
      case 'MEDIUM':
        return <span className="text-[11px] font-semibold text-blue-700">Medium</span>;
      case 'HIGH':
        return <span className="text-[11px] font-semibold text-amber-700">High</span>;
      case 'CRITICAL':
        return <span className="text-[11px] font-semibold text-rose-700">Critical</span>;
      default:
        return <span className="text-[11px] text-slate-600">{complexity}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <FolderGit2 className="w-7 h-7 text-indigo-600" />
            Enterprise Projects & Milestone Tiers
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative project specification catalogue, sequential milestone weights (Tiers 1–3), and rubric standards.
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          New Project Specification
        </button>
      </div>

      {/* Tier Filter Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6">
          {[
            { key: '', label: 'All Project Tiers' },
            { key: 'TIER_1_FOUNDATIONAL', label: 'Tier 1: Foundational' },
            { key: 'TIER_2_INTERMEDIATE', label: 'Tier 2: Intermediate' },
            { key: 'TIER_3_CAPSTONE', label: 'Tier 3: Capstone' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                setSelectedTier(tab.key);
                setPage(1);
              }}
              className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${
                selectedTier === tab.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              <Layers className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
          {/* Search */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by code or title..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Track Filter */}
          <select
            value={selectedTrack}
            onChange={(e) => {
              setSelectedTrack(e.target.value);
              setPage(1);
            }}
            className="w-full sm:w-60 border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-700 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Specialization Tracks</option>
            {tracks?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.code} - {t.title}
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-slate-500">
          Showing {projectData?.items.length || 0} of {projectData?.total || 0} projects
        </div>
      </div>

      {/* Project Cards Grid */}
      {isProjectsLoading ? (
        <div className="p-16 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
          <span className="text-sm">Loading project catalog specifications...</span>
        </div>
      ) : !projectData?.items || projectData.items.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 space-y-3">
          <FolderGit2 className="w-12 h-12 mx-auto text-slate-300" />
          <h3 className="text-base font-semibold text-slate-700">No Projects Found</h3>
          <p className="text-xs max-w-sm mx-auto">
            No project specifications match the selected tier or search criteria.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projectData.items.map((project: ProjectListItem) => (
            <div
              key={project.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all p-5 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-mono text-xs font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                    {project.code}
                  </span>
                  {getTierBadge(project.tier)}
                </div>

                <h3 className="text-sm font-bold text-slate-900 line-clamp-2 mt-1 mb-2">
                  {project.title}
                </h3>

                {project.track_title && (
                  <p className="text-xs text-slate-500 mb-3 flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="truncate">{project.track_title}</span>
                  </p>
                )}

                <div className="grid grid-cols-2 gap-2 text-xs py-3 border-y border-slate-100 mb-4 bg-slate-50/50 rounded-lg px-2.5">
                  <div className="flex items-center gap-1.5 text-slate-600">
                    <Users className="w-3.5 h-3.5 text-slate-400" />
                    <span>{project.min_team_size}–{project.max_team_size} Members</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-600">
                    <Target className="w-3.5 h-3.5 text-slate-400" />
                    <span>Pass: {project.passing_score}%</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-600">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>{project.milestone_count} Milestones</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-600">
                    <span className="text-slate-400">Level:</span>
                    {getComplexityBadge(project.complexity)}
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedProjectForDetail(project.id)}
                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
              >
                Inspect Milestones & Rubrics
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* PROJECT DETAIL MODAL */}
      {selectedProjectForDetail && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-slate-50">
              <div className="flex items-center gap-2">
                <FolderGit2 className="w-5 h-5 text-indigo-600" />
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    {projectDetail ? `${projectDetail.code} - ${projectDetail.title}` : 'Loading...'}
                  </h2>
                  <p className="text-xs text-slate-500">
                    {projectDetail?.track_title || 'Specialization Project Specification'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedProjectForDetail(null)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {isDetailLoading || !projectDetail ? (
              <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                <span className="text-xs">Fetching project specification details...</span>
              </div>
            ) : (
              <div className="p-6 overflow-y-auto space-y-6">
                {/* Meta Summary */}
                <div className="flex flex-wrap items-center gap-3">
                  {getTierBadge(projectDetail.tier)}
                  <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-full font-medium">
                    Complexity: {projectDetail.complexity}
                  </span>
                  <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-full font-medium">
                    Team Size: {projectDetail.min_team_size} – {projectDetail.max_team_size}
                  </span>
                  <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-full font-medium">
                    Passing Threshold: {projectDetail.passing_score}%
                  </span>
                </div>

                {projectDetail.description && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                      Project Overview & Scope
                    </h4>
                    <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200 leading-relaxed">
                      {projectDetail.description}
                    </p>
                  </div>
                )}

                {/* Milestones Breakdown */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center justify-between">
                    <span>Sequential Milestones Breakdown</span>
                    <span className="text-indigo-600 font-semibold">{projectDetail.milestones.length} Stages</span>
                  </h4>
                  <div className="space-y-3">
                    {projectDetail.milestones.map((m) => (
                      <div
                        key={m.id}
                        className="border border-slate-200 rounded-lg p-3.5 bg-white hover:border-slate-300 transition-colors"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="font-semibold text-xs text-slate-900">
                            #{m.sequence_order} • {m.title}
                          </span>
                          <span className="font-mono text-xs font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                            Weight: {m.weight_percentage}%
                          </span>
                        </div>
                        {m.description && (
                          <p className="text-xs text-slate-500 mt-1">{m.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Rubric Criteria */}
                {projectDetail.rubric_template?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                      Evaluation Rubric Template
                    </h4>
                    <div className="border border-slate-200 rounded-lg divide-y divide-slate-100 text-xs">
                      {projectDetail.rubric_template.map((r) => (
                        <div key={r.key} className="p-3 flex items-center justify-between">
                          <span className="font-medium text-slate-800">{r.title}</span>
                          <span className="font-mono font-semibold text-slate-600">{r.max_points} pts</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* CREATE PROJECT SPECIFICATION MODAL */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-slate-50">
              <div className="flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-600" />
                <h2 className="text-base font-bold text-slate-900">
                  New Project Specification Template
                </h2>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="p-6 overflow-y-auto space-y-4">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="prj_track" className="block text-xs font-semibold text-slate-700 mb-1">
                    Specialization Track *
                  </label>
                  <select
                    id="prj_track"
                    required
                    value={formData.track_id}
                    onChange={(e) => setFormData({ ...formData, track_id: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                  >
                    <option value="">Select track...</option>
                    {tracks?.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.code} - {t.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="prj_code" className="block text-xs font-semibold text-slate-700 mb-1">
                    Project Code *
                  </label>
                  <input
                    id="prj_code"
                    type="text"
                    required
                    placeholder="e.g. PRJ-DA-01"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="prj_title" className="block text-xs font-semibold text-slate-700 mb-1">
                  Project Title *
                </label>
                <input
                  id="prj_title"
                  type="text"
                  required
                  placeholder="e.g. Enterprise Lakehouse Architecture & Analytics Platform"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label htmlFor="prj_tier" className="block text-xs font-semibold text-slate-700 mb-1">
                    Tier Classification *
                  </label>
                  <select
                    id="prj_tier"
                    value={formData.tier}
                    onChange={(e) => setFormData({ ...formData, tier: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                  >
                    <option value="TIER_1_FOUNDATIONAL">Tier 1: Foundational</option>
                    <option value="TIER_2_INTERMEDIATE">Tier 2: Intermediate</option>
                    <option value="TIER_3_CAPSTONE">Tier 3: Capstone</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="prj_complexity" className="block text-xs font-semibold text-slate-700 mb-1">
                    Complexity Level
                  </label>
                  <select
                    id="prj_complexity"
                    value={formData.complexity}
                    onChange={(e) => setFormData({ ...formData, complexity: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="prj_pass" className="block text-xs font-semibold text-slate-700 mb-1">
                    Passing Threshold (%)
                  </label>
                  <input
                    id="prj_pass"
                    type="number"
                    min="1"
                    max="100"
                    value={formData.passing_score}
                    onChange={(e) => setFormData({ ...formData, passing_score: Number(e.target.value) })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="prj_desc" className="block text-xs font-semibold text-slate-700 mb-1">
                  Description & Scope
                </label>
                <textarea
                  id="prj_desc"
                  rows={2}
                  placeholder="Outline objectives, technology stack, and business deliverables..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                />
              </div>

              {/* Dynamic Milestone Builder */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                    Sequential Milestone Stages *
                  </label>
                  <span
                    className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                      isWeightValid
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}
                  >
                    Weight Sum: {totalMilestoneWeight}% (Target: 100%)
                  </span>
                </div>

                <div className="space-y-2 mb-3">
                  {milestoneRows.map((m, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                    >
                      <span className="font-mono font-bold text-slate-500 w-6 text-center">#{m.sequence_order}</span>
                      <input
                        type="text"
                        placeholder="Milestone Title"
                        required
                        value={m.title}
                        onChange={(e) => {
                          const updated = [...milestoneRows];
                          updated[idx].title = e.target.value;
                          setMilestoneRows(updated);
                        }}
                        className="flex-1 border border-slate-300 rounded px-2 py-1 text-xs"
                      />
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          min="1"
                          max="100"
                          required
                          value={m.weight_percentage}
                          onChange={(e) => {
                            const updated = [...milestoneRows];
                            updated[idx].weight_percentage = Number(e.target.value);
                            setMilestoneRows(updated);
                          }}
                          className="w-16 border border-slate-300 rounded px-2 py-1 text-xs text-right font-mono"
                        />
                        <span className="text-slate-400">%</span>
                      </div>
                      {milestoneRows.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeMilestoneRow(idx)}
                          className="p-1 text-slate-400 hover:text-red-600 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={addMilestoneRow}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold text-indigo-600 hover:bg-indigo-50 border border-indigo-200 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Milestone Stage
                </button>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createProjectMutation.isPending || !isWeightValid}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {createProjectMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Save Project Specification
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
