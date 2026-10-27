import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  InternshipListItem,
  TrackItem,
  InternshipCreateRequest,
  InternshipUpdateRequest,
  InternshipCompleteRequest,
  InternshipTerminateRequest,
  CandidateInternshipEligibilityResponse,
} from '@/types';
import {
  Briefcase,
  Plus,
  Search,
  Filter,
  Layers,
  Calendar,
  Building2,
  CheckCircle2,
  Clock,
  AlertTriangle,
  X,
  RefreshCw,
  Award,
  UserCheck,
  AlertCircle,
} from 'lucide-react';

export const InternshipsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Filters State
  const [selectedTrack, setSelectedTrack] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 10;

  // Modals & Drawer State
  const [isInitModalOpen, setIsInitModalOpen] = useState(false);
  const [isEligibilityModalOpen, setIsEligibilityModalOpen] = useState(false);
  const [selectedDetailId, setSelectedDetailId] = useState<string | null>(null);
  const [editingRecord, setEditingRecord] = useState<InternshipListItem | null>(null);
  const [completingRecord, setCompletingRecord] = useState<InternshipListItem | null>(null);
  const [terminatingRecord, setTerminatingRecord] = useState<InternshipListItem | null>(null);

  // Queries
  const { data: tracks } = useQuery<TrackItem[]>({
    queryKey: ['tracks'],
    queryFn: () => api.getTracks(),
  });

  const { data: candidatesData } = useQuery({
    queryKey: ['candidates-for-internship'],
    queryFn: () => api.getCandidates({ page: 1, page_size: 100 }),
  });

  const { data: internshipsData, isLoading } = useQuery({
    queryKey: ['internships', selectedTrack, selectedStatus, searchTerm, page],
    queryFn: () =>
      api.getInternships({
        track_id: selectedTrack || undefined,
        status: selectedStatus || undefined,
        search: searchTerm || undefined,
        page,
        page_size: pageSize,
      }),
  });

  const { data: selectedInternshipDetail, isLoading: isDetailLoading } = useQuery({
    queryKey: ['internship-detail', selectedDetailId],
    queryFn: () => (selectedDetailId ? api.getInternship(selectedDetailId) : null),
    enabled: !!selectedDetailId,
  });

  // Mutations
  const initMutation = useMutation({
    mutationFn: (data: InternshipCreateRequest) => api.initializeInternship(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['internships'] });
      setIsInitModalOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: InternshipUpdateRequest }) =>
      api.updateInternship(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['internships'] });
      queryClient.invalidateQueries({ queryKey: ['internship-detail'] });
      setEditingRecord(null);
    },
  });

  const completeMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: InternshipCompleteRequest }) =>
      api.completeInternship(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['internships'] });
      queryClient.invalidateQueries({ queryKey: ['internship-detail'] });
      setCompletingRecord(null);
    },
  });

  const terminateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: InternshipTerminateRequest }) =>
      api.terminateInternship(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['internships'] });
      queryClient.invalidateQueries({ queryKey: ['internship-detail'] });
      setTerminatingRecord(null);
    },
  });

  const syncDurationMutation = useMutation({
    mutationFn: (id: string) => api.syncInternshipDuration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['internships'] });
      queryClient.invalidateQueries({ queryKey: ['internship-detail'] });
    },
  });

  // Form States
  const [initForm, setInitForm] = useState<InternshipCreateRequest>({
    candidate_id: '',
    track_id: '',
    start_date: new Date().toISOString().split('T')[0],
    expected_end_date: new Date(Date.now() + 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    company_name: 'ExcelR Technology Labs',
    coordinator_notes: '',
  });

  const [editForm, setEditForm] = useState<InternshipUpdateRequest>({
    start_date: '',
    expected_end_date: '',
    company_name: '',
    coordinator_notes: '',
  });

  const [completeForm, setCompleteForm] = useState<InternshipCompleteRequest>({
    actual_completion_date: new Date().toISOString().split('T')[0],
    completion_notes: '',
  });

  const [terminateReason, setTerminateReason] = useState<string>('');
  const [diagCandidateId, setDiagCandidateId] = useState<string>('');
  const [diagResult, setDiagResult] = useState<CandidateInternshipEligibilityResponse | null>(null);
  const [isDiagLoading, setIsDiagLoading] = useState(false);
  const [diagError, setDiagError] = useState<string | null>(null);

  const handleRunDiagnostic = async () => {
    if (!diagCandidateId) return;
    setIsDiagLoading(true);
    setDiagError(null);
    try {
      const res = await api.checkCandidateInternshipEligibility(diagCandidateId);
      setDiagResult(res);
    } catch (err: any) {
      setDiagError(err.message || 'Failed to check eligibility diagnostic.');
      setDiagResult(null);
    } finally {
      setIsDiagLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Active
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
            Completed
          </span>
        );
      case 'TERMINATED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
            Terminated
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  const getDurationTierBadge = (months: number) => {
    let tierText = 'Tier 1 Baseline';
    let colorClass = 'bg-indigo-50 text-indigo-700 border-indigo-200';
    if (months === 6) {
      tierText = 'Tier 2 Intermediate';
      colorClass = 'bg-purple-50 text-purple-700 border-purple-200';
    } else if (months >= 9) {
      tierText = 'Tier 3 Enterprise';
      colorClass = 'bg-amber-50 text-amber-800 border-amber-200';
    }
    return (
      <div className="flex flex-col">
        <span className="text-sm font-bold text-slate-900">{months} Months</span>
        <span className={`inline-block text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${colorClass} mt-0.5 w-fit`}>
          {tierText}
        </span>
      </div>
    );
  };

  const items = internshipsData?.items || [];
  const totalItems = internshipsData?.total || 0;
  const activeCount = items.filter((i) => i.internship_status === 'ACTIVE').length;
  const completedCount = items.filter((i) => i.internship_status === 'COMPLETED').length;

  return (
    <div className="space-y-6">
      {/* Top Banner / Decoupling Note */}
      <div className="bg-gradient-to-r from-brand-900 via-indigo-900 to-slate-900 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 -mt-4 -mr-4 w-64 h-64 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-brand-500/20 text-brand-200 border border-brand-400/30">
                Domain 5 • Phase 11
              </span>
              <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-white/10 text-slate-200">
                BR-INT-01 / BR-INT-02 Decoupled Duration
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Internship Lifecycle & Milestone Progression
            </h1>
            <p className="mt-1 text-sm text-slate-300 max-w-2xl leading-relaxed">
              Operational calendar dates are decoupled from accredited milestone durations.
              Milestone tiers strictly scale by verified project achievements: 1 PRJ = 3 Months, 2 PRJ = 6 Months, 3 PRJ = 9 Months.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              id="btn-diagnostic-check"
              onClick={() => {
                setIsEligibilityModalOpen(true);
                setDiagResult(null);
                setDiagError(null);
              }}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-white/10 hover:bg-white/20 text-white backdrop-blur border border-white/20 transition-all shadow-sm"
            >
              <UserCheck className="w-4 h-4 text-emerald-300" />
              Eligibility Check
            </button>
            <button
              id="btn-initialize-internship"
              onClick={() => setIsInitModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-brand-500 hover:bg-brand-600 text-white transition-all shadow-lg shadow-brand-500/30"
            >
              <Plus className="w-4 h-4" />
              Initialize Internship
            </button>
          </div>
        </div>

        {/* Quick Metric Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/10">
          <div className="bg-white/5 rounded-xl p-3 border border-white/5">
            <span className="text-xs text-slate-400 block font-medium">Total Tracked</span>
            <span className="text-xl font-bold text-white mt-0.5">{totalItems}</span>
          </div>
          <div className="bg-white/5 rounded-xl p-3 border border-white/5">
            <span className="text-xs text-emerald-400 block font-medium">Currently Active</span>
            <span className="text-xl font-bold text-emerald-300 mt-0.5">{activeCount}</span>
          </div>
          <div className="bg-white/5 rounded-xl p-3 border border-white/5">
            <span className="text-xs text-blue-400 block font-medium">Graduated / Completed</span>
            <span className="text-xl font-bold text-blue-300 mt-0.5">{completedCount}</span>
          </div>
          <div className="bg-white/5 rounded-xl p-3 border border-white/5">
            <span className="text-xs text-purple-400 block font-medium">Progression Matrix</span>
            <span className="text-sm font-semibold text-purple-200 mt-1 block">Tier 1 • 2 • 3</span>
          </div>
        </div>
      </div>

      {/* Directory & Controls */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-6">
        <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
          <div className="flex-1 w-full md:w-auto relative">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              id="search-internships-input"
              type="text"
              placeholder="Search by candidate name, company, or tracking code..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                id="filter-track-select"
                value={selectedTrack}
                onChange={(e) => {
                  setSelectedTrack(e.target.value);
                  setPage(1);
                }}
                className="text-sm bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-700 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
              >
                <option value="">All Academic Tracks</option>
                {tracks?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.code} - {t.title}
                  </option>
                ))}
              </select>
            </div>

            <select
              id="filter-status-select"
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(1);
              }}
              className="text-sm bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-700 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="TERMINATED">TERMINATED</option>
            </select>
          </div>
        </div>

        {/* Internship Records Table */}
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50/80 text-slate-600 font-semibold">
              <tr>
                <th className="py-3.5 px-4">Candidate & Track</th>
                <th className="py-3.5 px-4">Calendar Dates (Operational)</th>
                <th className="py-3.5 px-4">Accredited Duration (Policy)</th>
                <th className="py-3.5 px-4">Company Partner</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-brand-600" />
                    Loading internship records...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-500">
                    <Briefcase className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                    <p className="font-semibold text-slate-700">No internship records found</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Initialize an internship or run a diagnostic eligibility check.
                    </p>
                  </td>
                </tr>
              ) : (
                items.map((record) => (
                  <tr
                    key={record.id}
                    data-testid={`internship-row-${record.id}`}
                    className="hover:bg-slate-50/80 transition-colors group"
                  >
                    <td className="py-4 px-4">
                      <div>
                        <span className="font-bold text-slate-900 group-hover:text-brand-600 transition-colors">
                          {record.candidate_name}
                        </span>
                        {record.candidate_number && (
                          <span className="text-xs text-slate-400 block font-mono">
                            {record.candidate_number}
                          </span>
                        )}
                        <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-[11px] font-medium mt-1">
                          {record.track_code}
                        </span>
                      </div>
                    </td>

                    <td className="py-4 px-4">
                      <div className="space-y-1 text-xs">
                        <div className="flex items-center gap-1.5 text-slate-600">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          <span>Start: <strong className="text-slate-800">{record.start_date}</strong></span>
                        </div>
                        {record.expected_end_date && (
                          <div className="flex items-center gap-1.5 text-slate-500">
                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                            <span>Exp End: {record.expected_end_date}</span>
                          </div>
                        )}
                        {record.actual_completion_date && (
                          <div className="flex items-center gap-1.5 text-blue-600 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Completed: {record.actual_completion_date}</span>
                          </div>
                        )}
                      </div>
                    </td>

                    <td className="py-4 px-4">
                      {getDurationTierBadge(record.accredited_duration_months)}
                    </td>

                    <td className="py-4 px-4">
                      <div className="flex items-center gap-1.5 text-slate-700">
                        <Building2 className="w-4 h-4 text-slate-400 shrink-0" />
                        <span className="font-medium text-xs">
                          {record.company_name || 'ExcelR Technology Labs'}
                        </span>
                      </div>
                    </td>

                    <td className="py-4 px-4">{getStatusBadge(record.internship_status)}</td>

                    <td className="py-4 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          id={`btn-view-milestones-${record.id}`}
                          onClick={() => setSelectedDetailId(record.id)}
                          className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors inline-flex items-center gap-1"
                          title="View Milestones & Details"
                        >
                          <Layers className="w-3.5 h-3.5 text-brand-600" />
                          Milestones
                        </button>

                        {record.internship_status === 'ACTIVE' && (
                          <>
                            <button
                              id={`btn-sync-duration-${record.id}`}
                              onClick={() => syncDurationMutation.mutate(record.id)}
                              disabled={syncDurationMutation.isPending}
                              className="p-1.5 rounded-lg text-xs text-slate-500 hover:text-brand-600 hover:bg-brand-50 transition-colors"
                              title="Sync Accredited Duration with Approved Projects"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${syncDurationMutation.isPending ? 'animate-spin' : ''}`} />
                            </button>

                            <button
                              id={`btn-edit-dates-${record.id}`}
                              onClick={() => {
                                setEditingRecord(record);
                                setEditForm({
                                  start_date: record.start_date,
                                  expected_end_date: record.expected_end_date || '',
                                  company_name: record.company_name || '',
                                  coordinator_notes: '',
                                });
                              }}
                              className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 transition-colors"
                            >
                              Edit Dates
                            </button>

                            <button
                              id={`btn-complete-internship-${record.id}`}
                              onClick={() => {
                                setCompletingRecord(record);
                                setCompleteForm({
                                  actual_completion_date: new Date().toISOString().split('T')[0],
                                  completion_notes: '',
                                });
                              }}
                              className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition-colors"
                            >
                              Complete
                            </button>

                            <button
                              id={`btn-terminate-internship-${record.id}`}
                              onClick={() => {
                                setTerminatingRecord(record);
                                setTerminateReason('');
                              }}
                              className="p-1.5 rounded-lg text-xs text-rose-500 hover:bg-rose-50 transition-colors"
                              title="Terminate Internship"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {internshipsData && internshipsData.total_pages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <span className="text-xs text-slate-500">
              Showing page {internshipsData.page} of {internshipsData.total_pages} ({internshipsData.total} items)
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={page >= internshipsData.total_pages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 1. INITIALIZE INTERNSHIP MODAL */}
      {isInitModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 relative">
            <button
              onClick={() => setIsInitModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
                <Briefcase className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Initialize Internship</h3>
                <p className="text-xs text-slate-500">
                  Domain 5: Enrolls candidate with decoupled calendar & baseline accredited duration.
                </p>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                initMutation.mutate(initForm);
              }}
              className="space-y-4"
            >
              <div>
                <label htmlFor="select-init-candidate" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Candidate *
                </label>
                <select
                  id="select-init-candidate"
                  required
                  value={initForm.candidate_id}
                  onChange={(e) => setInitForm({ ...initForm, candidate_id: e.target.value })}
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                >
                  <option value="">Select Candidate</option>
                  {candidatesData?.items?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.first_name} {c.last_name} ({c.candidate_number || c.email})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="select-init-track" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Academic Track *
                </label>
                <select
                  id="select-init-track"
                  required
                  value={initForm.track_id}
                  onChange={(e) => setInitForm({ ...initForm, track_id: e.target.value })}
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                >
                  <option value="">Select Track</option>
                  {tracks?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.code} - {t.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="input-init-start-date" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                    Start Date *
                  </label>
                  <input
                    id="input-init-start-date"
                    type="date"
                    required
                    value={initForm.start_date}
                    onChange={(e) => setInitForm({ ...initForm, start_date: e.target.value })}
                    className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label htmlFor="input-init-expected-date" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                    Expected End Date
                  </label>
                  <input
                    id="input-init-expected-date"
                    type="date"
                    value={initForm.expected_end_date || ''}
                    onChange={(e) => setInitForm({ ...initForm, expected_end_date: e.target.value })}
                    className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="input-init-company" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Company / Corporate Partner
                </label>
                <input
                  id="input-init-company"
                  type="text"
                  placeholder="ExcelR Technology Labs"
                  value={initForm.company_name || ''}
                  onChange={(e) => setInitForm({ ...initForm, company_name: e.target.value })}
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="input-init-notes" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Coordinator Notes
                </label>
                <textarea
                  id="input-init-notes"
                  rows={2}
                  placeholder="Optional onboarding remarks or client allocation details..."
                  value={initForm.coordinator_notes || ''}
                  onChange={(e) => setInitForm({ ...initForm, coordinator_notes: e.target.value })}
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                />
              </div>

              {initMutation.isError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2 text-xs text-rose-700">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-500 mt-0.5" />
                  <span>{(initMutation.error as any)?.message || 'Failed to initialize internship.'}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsInitModalOpen(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-init-internship"
                  type="submit"
                  disabled={initMutation.isPending}
                  className="px-5 py-2 text-sm font-semibold bg-brand-600 hover:bg-brand-700 text-white rounded-xl shadow-md transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {initMutation.isPending && <RefreshCw className="w-4 h-4 animate-spin" />}
                  Confirm Initialization
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2. DIAGNOSTIC ELIGIBILITY CHECK MODAL */}
      {isEligibilityModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 relative">
            <button
              onClick={() => setIsEligibilityModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <UserCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Internship Eligibility Diagnostic</h3>
                <p className="text-xs text-slate-500">
                  FR-INT-001: Evaluates candidate project achievements and calculates recommended accredited duration.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label htmlFor="select-diag-candidate" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Select Candidate for Diagnostic
                </label>
                <div className="flex gap-2">
                  <select
                    id="select-diag-candidate"
                    value={diagCandidateId}
                    onChange={(e) => setDiagCandidateId(e.target.value)}
                    className="flex-1 text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                  >
                    <option value="">Select Candidate</option>
                    {candidatesData?.items?.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.first_name} {c.last_name} ({c.email})
                      </option>
                    ))}
                  </select>
                  <button
                    id="btn-run-diag"
                    type="button"
                    disabled={!diagCandidateId || isDiagLoading}
                    onClick={handleRunDiagnostic}
                    className="px-4 py-2 text-sm font-semibold bg-brand-600 hover:bg-brand-700 text-white rounded-xl transition-all disabled:opacity-50 flex items-center gap-2"
                  >
                    {isDiagLoading && <RefreshCw className="w-4 h-4 animate-spin" />}
                    Analyze
                  </button>
                </div>
              </div>

              {diagError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2 text-xs text-rose-700">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-500 mt-0.5" />
                  <span>{diagError}</span>
                </div>
              )}

              {diagResult && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-900 block">{diagResult.candidate_name}</span>
                      <span className="text-xs text-slate-500">{diagResult.track_title}</span>
                    </div>
                    {diagResult.is_eligible ? (
                      <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Eligible
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                        Prerequisites Incomplete
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200 text-xs">
                    <div className="bg-white p-2.5 rounded-lg border border-slate-100">
                      <span className="text-slate-400 block font-medium">Approved Projects</span>
                      <strong className="text-sm text-slate-800">{diagResult.approved_projects_count} Projects</strong>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-100">
                      <span className="text-slate-400 block font-medium">Accredited Policy Duration</span>
                      <strong className="text-sm text-brand-600">{diagResult.recommended_duration_months} Months</strong>
                    </div>
                  </div>

                  <div>
                    <span className="text-xs font-bold text-slate-600 block mb-1">Diagnostic Details:</span>
                    <ul className="space-y-1">
                      {diagResult.eligibility_reasons.map((r, idx) => (
                        <li key={idx} className="text-xs text-slate-600 flex items-start gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {diagResult.existing_internship_id && (
                    <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700 flex items-center justify-between">
                      <span>Candidate has an existing record active.</span>
                      <button
                        onClick={() => {
                          setIsEligibilityModalOpen(false);
                          setSelectedDetailId(diagResult.existing_internship_id!);
                        }}
                        className="font-bold underline ml-2"
                      >
                        View Record
                      </button>
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center justify-end pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsEligibilityModalOpen(false)}
                  className="px-4 py-2 text-sm font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. MILESTONE & DETAIL DRAWER */}
      {selectedDetailId && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-xl h-full shadow-2xl flex flex-col justify-between overflow-y-auto border-l border-slate-200">
            <div className="p-6 space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
                    <Layers className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">Internship Milestones & Audit</h3>
                    <p className="text-xs text-slate-500">Accredited progression anchored to project achievements.</p>
                  </div>
                </div>
                <button
                  id="btn-close-detail-drawer"
                  onClick={() => setSelectedDetailId(null)}
                  className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {isDetailLoading || !selectedInternshipDetail ? (
                <div className="py-20 text-center text-slate-400">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-brand-600" />
                  Loading progression records...
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Candidate Overview Card */}
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-bold text-slate-900 text-base">
                          {selectedInternshipDetail.candidate_name}
                        </h4>
                        <span className="text-xs text-slate-500 block">
                          {selectedInternshipDetail.candidate_email} • Track: {selectedInternshipDetail.track_code}
                        </span>
                      </div>
                      {getStatusBadge(selectedInternshipDetail.internship_status)}
                    </div>
                    <div className="grid grid-cols-2 gap-2 pt-2 text-xs text-slate-600">
                      <div>
                        <span className="text-slate-400 block font-medium">Corporate Partner:</span>
                        <strong className="text-slate-800">{selectedInternshipDetail.company_name}</strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block font-medium">Accredited Duration:</span>
                        <strong className="text-brand-600">
                          {selectedInternshipDetail.accredited_duration_months} Months Total
                        </strong>
                      </div>
                    </div>
                  </div>

                  {/* Calendar Dates vs Milestone Timeline Banner */}
                  <div className="p-3.5 bg-indigo-50 border border-indigo-200 rounded-xl text-xs text-indigo-900 space-y-1">
                    <div className="flex items-center gap-1.5 font-bold">
                      <Calendar className="w-4 h-4 text-indigo-600" />
                      <span>Decoupled Operational Calendar Tracking:</span>
                    </div>
                    <p className="text-indigo-700">
                      Enrolled: <strong>{selectedInternshipDetail.start_date}</strong> • Expected Completion:{' '}
                      <strong>{selectedInternshipDetail.expected_end_date || 'Open'}</strong>
                      {selectedInternshipDetail.actual_completion_date && (
                        <span> • Formally Completed: <strong>{selectedInternshipDetail.actual_completion_date}</strong></span>
                      )}
                    </p>
                  </div>

                  {/* Sequential Milestone Progression (BR-INT-02 Matrix) */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                        <Award className="w-4 h-4 text-amber-500" />
                        Accredited Milestone Tiers
                      </h4>
                      {selectedInternshipDetail.internship_status === 'ACTIVE' && (
                        <button
                          onClick={() => syncDurationMutation.mutate(selectedInternshipDetail.id)}
                          disabled={syncDurationMutation.isPending}
                          className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1"
                        >
                          <RefreshCw className={`w-3 h-3 ${syncDurationMutation.isPending ? 'animate-spin' : ''}`} />
                          Recalculate Duration
                        </button>
                      )}
                    </div>

                    <div className="space-y-3">
                      {selectedInternshipDetail.milestones?.map((m) => {
                        const isAchieved = m.status === 'ACHIEVED';
                        const isInProgress = m.status === 'IN_PROGRESS';
                        return (
                          <div
                            key={m.id}
                            className={`p-4 rounded-xl border transition-all ${
                              isAchieved
                                ? 'bg-emerald-50/50 border-emerald-200'
                                : isInProgress
                                ? 'bg-purple-50/50 border-purple-200'
                                : 'bg-slate-50/50 border-slate-200 opacity-70'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span
                                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                                    isAchieved
                                      ? 'bg-emerald-600 text-white'
                                      : isInProgress
                                      ? 'bg-purple-600 text-white'
                                      : 'bg-slate-300 text-slate-700'
                                  }`}
                                >
                                  {m.milestone_tier}
                                </span>
                                <div>
                                  <h5 className="font-bold text-sm text-slate-900">{m.title}</h5>
                                  <span className="text-[11px] text-slate-500 font-medium">
                                    Accredited Value: {m.accredited_months} Months
                                  </span>
                                </div>
                              </div>
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
                                  isAchieved
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : isInProgress
                                    ? 'bg-purple-100 text-purple-800'
                                    : 'bg-slate-200 text-slate-600'
                                }`}
                              >
                                {m.status}
                              </span>
                            </div>

                            {m.notes && (
                              <p className="text-xs text-slate-600 mt-2 pl-8 italic">
                                "{m.notes}"
                              </p>
                            )}

                            {m.achieved_at && (
                              <div className="mt-2 pl-8 flex items-center gap-3 text-[11px] text-slate-400">
                                <span>Verified on {new Date(m.achieved_at).toLocaleDateString()}</span>
                                {m.verified_by_name && <span>by {m.verified_by_name}</span>}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Notes & Audit History */}
                  {selectedInternshipDetail.coordinator_notes && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-700 uppercase mb-2">Coordinator Audit Log</h4>
                      <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs font-mono text-slate-700 whitespace-pre-wrap leading-relaxed">
                        {selectedInternshipDetail.coordinator_notes}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end">
              <button
                onClick={() => setSelectedDetailId(null)}
                className="px-4 py-2 text-sm font-semibold bg-white border border-slate-200 rounded-xl hover:bg-slate-100 text-slate-700"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. EDIT DATES & COMPANY MODAL */}
      {editingRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 relative">
            <button
              onClick={() => setEditingRecord(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-lg font-bold text-slate-900 mb-1">Update Operational Calendar</h3>
            <p className="text-xs text-slate-500 mb-4">
              Decoupled dates edit for {editingRecord.candidate_name}.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                updateMutation.mutate({
                  id: editingRecord.id,
                  data: editForm,
                });
              }}
              className="space-y-4"
            >
              <div>
                <label htmlFor="input-edit-start-date" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Start Date *
                </label>
                <input
                  id="input-edit-start-date"
                  type="date"
                  required
                  value={editForm.start_date || ''}
                  onChange={(e) => setEditForm({ ...editForm, start_date: e.target.value })}
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="input-edit-expected-date" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Expected End Date
                </label>
                <input
                  id="input-edit-expected-date"
                  type="date"
                  value={editForm.expected_end_date || ''}
                  onChange={(e) => setEditForm({ ...editForm, expected_end_date: e.target.value })}
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="input-edit-company" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Company Partner
                </label>
                <input
                  id="input-edit-company"
                  type="text"
                  value={editForm.company_name || ''}
                  onChange={(e) => setEditForm({ ...editForm, company_name: e.target.value })}
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingRecord(null)}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-edit-dates"
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 text-sm font-semibold bg-brand-600 hover:bg-brand-700 text-white rounded-xl shadow transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {updateMutation.isPending && <RefreshCw className="w-4 h-4 animate-spin" />}
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 5. COMPLETE INTERNSHIP MODAL */}
      {completingRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 relative">
            <button
              onClick={() => setCompletingRecord(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Confirm Completion</h3>
                <p className="text-xs text-slate-500">Formally marks internship as successfully completed.</p>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                completeMutation.mutate({
                  id: completingRecord.id,
                  data: completeForm,
                });
              }}
              className="space-y-4"
            >
              <div>
                <label htmlFor="input-complete-date" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Actual Completion Date *
                </label>
                <input
                  id="input-complete-date"
                  type="date"
                  required
                  value={completeForm.actual_completion_date || ''}
                  onChange={(e) =>
                    setCompleteForm({ ...completeForm, actual_completion_date: e.target.value })
                  }
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="input-complete-notes" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Completion Remarks / Performance Notes
                </label>
                <textarea
                  id="input-complete-notes"
                  rows={3}
                  placeholder="Supervisor sign-off notes or evaluation summary..."
                  value={completeForm.completion_notes || ''}
                  onChange={(e) =>
                    setCompleteForm({ ...completeForm, completion_notes: e.target.value })
                  }
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-brand-500 focus:outline-none"
                />
              </div>

              {completeMutation.isError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2 text-xs text-rose-700">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-500 mt-0.5" />
                  <span>{(completeMutation.error as any)?.message || 'Failed to complete internship.'}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setCompletingRecord(null)}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-complete"
                  type="submit"
                  disabled={completeMutation.isPending}
                  className="px-4 py-2 text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {completeMutation.isPending && <RefreshCw className="w-4 h-4 animate-spin" />}
                  Confirm Completion
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 6. TERMINATE INTERNSHIP MODAL */}
      {terminatingRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 relative">
            <button
              onClick={() => setTerminatingRecord(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-600"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Terminate Internship</h3>
                <p className="text-xs text-slate-500">Halts active progression. Mandatory reason required.</p>
              </div>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                terminateMutation.mutate({
                  id: terminatingRecord.id,
                  data: { reason: terminateReason },
                });
              }}
              className="space-y-4"
            >
              <div>
                <label htmlFor="input-terminate-reason" className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Mandatory Termination Reason *
                </label>
                <textarea
                  id="input-terminate-reason"
                  required
                  minLength={10}
                  rows={3}
                  placeholder="Provide detailed justification (minimum 10 characters)..."
                  value={terminateReason}
                  onChange={(e) => setTerminateReason(e.target.value)}
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 focus:bg-white focus:ring-2 focus:ring-rose-500 focus:outline-none"
                />
              </div>

              {terminateMutation.isError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2 text-xs text-rose-700">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-500 mt-0.5" />
                  <span>{(terminateMutation.error as any)?.message || 'Failed to terminate internship.'}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setTerminatingRecord(null)}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-terminate"
                  type="submit"
                  disabled={terminateMutation.isPending || terminateReason.length < 10}
                  className="px-4 py-2 text-sm font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {terminateMutation.isPending && <RefreshCw className="w-4 h-4 animate-spin" />}
                  Confirm Termination
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default InternshipsPage;
