import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AssignmentItem, AllocationItem } from '@/types';
import {
  BookOpen,
  Plus,
  Calendar,
  Layers,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  FileCode,
  Tag,
  AlertCircle,
  Loader2,
  ListPlus,
  Trash2,
  ClipboardCheck,
  UploadCloud,
  Award,
} from 'lucide-react';
import { SubmissionReviewModal } from '@/components/SubmissionReviewModal';
import { SubmitDeliverableModal } from '@/components/SubmitDeliverableModal';

export const AssignmentsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Active View Tab: 'catalogue' | 'allocations' | 'submissions'
  const [activeTab, setActiveTab] = useState<'catalogue' | 'allocations' | 'submissions'>('catalogue');

  // Search & Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTrack, setSelectedTrack] = useState('');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 12;

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isAllocateModalOpen, setIsAllocateModalOpen] = useState(false);
  const [selectedSubmissionIdForReview, setSelectedSubmissionIdForReview] = useState<string | null>(null);
  const [isSubmitDeliverableModalOpen, setIsSubmitDeliverableModalOpen] = useState(false);
  const [activeAllocationForSubmit, setActiveAllocationForSubmit] = useState<string | undefined>(undefined);

  // Assignment Form State
  const [formData, setFormData] = useState({
    track_id: '',
    code: '',
    title: '',
    instructions_markdown: '',
    sequence_order: 1,
    is_mandatory: true,
    max_score: 100,
    passing_score: 60,
    allowed_file_types: ['pdf', 'zip', 'ipynb'],
    max_file_size_mb: 25,
  });
  const [rubricRows, setRubricRows] = useState<
    Array<{ key: string; title: string; max_points: number }>
  >([
    { key: 'syntax_quality', title: 'Code Quality & Structure', max_points: 30 },
    { key: 'correctness', title: 'Correctness & Test Cases', max_points: 50 },
    { key: 'documentation', title: 'Markdown Documentation', max_points: 20 },
  ]);
  const [formError, setFormError] = useState<string | null>(null);

  // Allocation Form State
  const [allocTargetType, setAllocTargetType] = useState<'batch' | 'candidate'>('batch');
  const [allocData, setAllocData] = useState({
    assignment_id: '',
    batch_id: '',
    candidate_id: '',
    due_date_utc: '',
    grace_period_end_utc: '',
  });
  const [allocError, setAllocError] = useState<string | null>(null);

  // Fetch Tracks & Batches for Dropdowns
  const { data: tracks } = useQuery({
    queryKey: ['tracks'],
    queryFn: () => api.getTracks(),
  });

  const { data: batches } = useQuery({
    queryKey: ['batches'],
    queryFn: () => api.getBatches(),
  });

  // Fetch Assignments Query
  const { data: assignmentData, isLoading: isAssignmentsLoading } = useQuery({
    queryKey: ['assignments', selectedTrack, searchTerm, page],
    queryFn: () =>
      api.getAssignments({
        track_id: selectedTrack || undefined,
        search: searchTerm || undefined,
        page,
        page_size: pageSize,
      }),
  });

  // Fetch Allocations Query
  const { data: allocationData, isLoading: isAllocationsLoading } = useQuery({
    queryKey: ['allocations', page],
    queryFn: () =>
      api.getAllocations({
        page,
        page_size: pageSize,
      }),
    enabled: activeTab === 'allocations',
  });

  // Fetch Submissions Query (Phase 7)
  const { data: submissionData, isLoading: isSubmissionsLoading } = useQuery({
    queryKey: ['submissions', selectedStatusFilter, page],
    queryFn: () =>
      api.getSubmissions({
        status: selectedStatusFilter || undefined,
        page,
        page_size: pageSize,
      }),
    enabled: activeTab === 'submissions',
  });

  // Create Assignment Mutation
  const createAssignmentMutation = useMutation({
    mutationFn: (payload: any) => api.createAssignment(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      setIsCreateModalOpen(false);
      setFormData({
        track_id: '',
        code: '',
        title: '',
        instructions_markdown: '',
        sequence_order: 1,
        is_mandatory: true,
        max_score: 100,
        passing_score: 60,
        allowed_file_types: ['pdf', 'zip', 'ipynb'],
        max_file_size_mb: 25,
      });
      setFormError(null);
    },
    onError: (err: any) => {
      setFormError(err.message || 'Failed to create assignment.');
    },
  });

  // Create Allocation Mutation
  const createAllocationMutation = useMutation({
    mutationFn: (payload: any) => api.createAllocation(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['allocations'] });
      setIsAllocateModalOpen(false);
      setAllocData({
        assignment_id: '',
        batch_id: '',
        candidate_id: '',
        due_date_utc: '',
        grace_period_end_utc: '',
      });
      setAllocError(null);
    },
    onError: (err: any) => {
      setAllocError(err.message || 'Failed to allocate assignment.');
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!formData.track_id) {
      setFormError('Please select a course track.');
      return;
    }
    if (formData.passing_score > formData.max_score) {
      setFormError('Passing score cannot exceed maximum score.');
      return;
    }

    createAssignmentMutation.mutate({
      ...formData,
      rubric_template: rubricRows,
    });
  };

  const handleAllocateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setAllocError(null);

    if (!allocData.assignment_id) {
      setAllocError('Please select an assignment.');
      return;
    }
    if (!allocData.due_date_utc) {
      setAllocError('Please specify a due date.');
      return;
    }

    if (allocTargetType === 'batch' && !allocData.batch_id) {
      setAllocError('Please select a cohort batch.');
      return;
    }
    if (allocTargetType === 'candidate' && !allocData.candidate_id) {
      setAllocError('Please provide a candidate ID.');
      return;
    }

    createAllocationMutation.mutate({
      assignment_id: allocData.assignment_id,
      batch_id: allocTargetType === 'batch' ? allocData.batch_id : undefined,
      candidate_id: allocTargetType === 'candidate' ? allocData.candidate_id : undefined,
      due_date_utc: new Date(allocData.due_date_utc).toISOString(),
      grace_period_end_utc: allocData.grace_period_end_utc
        ? new Date(allocData.grace_period_end_utc).toISOString()
        : undefined,
    });
  };

  const addRubricRow = () => {
    setRubricRows([
      ...rubricRows,
      {
        key: `criterion_${rubricRows.length + 1}`,
        title: 'New Evaluation Criterion',
        max_points: 10,
      },
    ]);
  };

  const removeRubricRow = (idx: number) => {
    setRubricRows(rubricRows.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <BookOpen className="w-7 h-7 text-indigo-600" />
            Curriculum Assignments & Cohort Allocations
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative assignment template catalogue, rubric standards, and cohort deadline controls.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setActiveAllocationForSubmit(undefined);
              setIsSubmitDeliverableModalOpen(true);
            }}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors shadow-sm"
          >
            <UploadCloud className="w-4 h-4" />
            Submit Deliverable
          </button>
          <button
            onClick={() => setIsAllocateModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
          >
            <Calendar className="w-4 h-4 text-slate-500" />
            Allocate to Cohort
          </button>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Assignment
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => {
              setActiveTab('catalogue');
              setPage(1);
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
              activeTab === 'catalogue'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Layers className="w-4 h-4" />
            Assignment Catalogue
          </button>
          <button
            onClick={() => {
              setActiveTab('allocations');
              setPage(1);
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
              activeTab === 'allocations'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Calendar className="w-4 h-4" />
            Cohort Allocations
          </button>
          <button
            onClick={() => {
              setActiveTab('submissions');
              setPage(1);
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
              activeTab === 'submissions'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <ClipboardCheck className="w-4 h-4" />
            Submissions & Review Queue
          </button>
        </nav>
      </div>

      {/* VIEW 1: Assignment Catalogue */}
      {activeTab === 'catalogue' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
            <div className="relative w-full md:w-96">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setPage(1);
                }}
                placeholder="Search by code or assignment title..."
                className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
              />
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-500" />
                <select
                  value={selectedTrack}
                  onChange={(e) => {
                    setSelectedTrack(e.target.value);
                    setPage(1);
                  }}
                  className="text-sm border border-slate-200 rounded-lg py-2 px-3 focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
                >
                  <option value="">All Curriculum Tracks</option>
                  {tracks?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.code} - {t.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Assignments Grid / Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {isAssignmentsLoading ? (
              <div className="p-12 text-center flex flex-col items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-3" />
                <span className="text-sm text-slate-500 font-medium">Loading assignment catalog...</span>
              </div>
            ) : assignmentData?.items.length === 0 ? (
              <div className="p-12 text-center">
                <FileCode className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-slate-800">No assignments found</h3>
                <p className="text-sm text-slate-500 mt-1 mb-4">
                  {searchTerm || selectedTrack
                    ? 'No matching assignments found for current search.'
                    : 'Get started by creating your first curriculum assignment.'}
                </p>
                <button
                  onClick={() => setIsCreateModalOpen(true)}
                  className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
                >
                  <Plus className="w-4 h-4" />
                  Create Template
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                  <thead className="bg-slate-50 font-semibold text-slate-600">
                    <tr>
                      <th className="py-3.5 pl-6 pr-3">Seq #</th>
                      <th className="px-3 py-3.5">Assignment Code</th>
                      <th className="px-3 py-3.5">Title & Track</th>
                      <th className="px-3 py-3.5">Scoring Policy</th>
                      <th className="px-3 py-3.5">File Specs</th>
                      <th className="px-3 py-3.5">Rubric Dimensions</th>
                      <th className="py-3.5 pl-3 pr-6 text-right">Mandatory</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {assignmentData?.items.map((asg: AssignmentItem) => (
                      <tr key={asg.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-4 pl-6 pr-3 font-mono font-bold text-xs text-slate-500">
                          #{asg.sequence_order}
                        </td>
                        <td className="px-3 py-4 font-mono font-bold text-xs text-indigo-600">
                          {asg.code}
                        </td>
                        <td className="px-3 py-4">
                          <div className="font-semibold text-slate-900">{asg.title}</div>
                          <div className="text-xs text-slate-500">{asg.track_name || 'Curriculum Track'}</div>
                        </td>
                        <td className="px-3 py-4 text-xs">
                          <div className="font-medium text-slate-800">
                            Passing: <span className="font-bold text-emerald-600">{asg.passing_score}</span> / {asg.max_score} pts
                          </div>
                        </td>
                        <td className="px-3 py-4 text-xs">
                          <div className="flex gap-1 flex-wrap">
                            {asg.allowed_file_types?.map((ft) => (
                              <span key={ft} className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono text-[10px]">
                                .{ft}
                              </span>
                            ))}
                            <span className="text-slate-400 text-[10px]">(&le; {asg.max_file_size_mb}MB)</span>
                          </div>
                        </td>
                        <td className="px-3 py-4 text-xs">
                          <span className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded-full font-semibold">
                            <Tag className="w-3 h-3" />
                            {asg.rubric_template?.length || 0} Criteria
                          </span>
                        </td>
                        <td className="py-4 pl-3 pr-6 text-right">
                          {asg.is_mandatory ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Mandatory
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400 italic">Optional</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 2: Cohort Allocations */}
      {activeTab === 'allocations' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {isAllocationsLoading ? (
              <div className="p-12 text-center flex flex-col items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-3" />
                <span className="text-sm text-slate-500 font-medium">Loading allocation records...</span>
              </div>
            ) : allocationData?.items.length === 0 ? (
              <div className="p-12 text-center">
                <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-slate-800">No active allocations</h3>
                <p className="text-sm text-slate-500 mt-1 mb-4">
                  Assignments have not yet been assigned to any cohorts or students.
                </p>
                <button
                  onClick={() => setIsAllocateModalOpen(true)}
                  className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
                >
                  <Calendar className="w-4 h-4" />
                  Allocate Assignment
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                  <thead className="bg-slate-50 font-semibold text-slate-600">
                    <tr>
                      <th className="py-3.5 pl-6 pr-3">Assignment Code</th>
                      <th className="px-3 py-3.5">Title</th>
                      <th className="px-3 py-3.5">Allocated Target</th>
                      <th className="px-3 py-3.5">Due Date (UTC)</th>
                      <th className="px-3 py-3.5">Grace Period End</th>
                      <th className="py-3.5 pl-3 pr-6 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {allocationData?.items.map((alloc: AllocationItem) => (
                      <tr key={alloc.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-4 pl-6 pr-3 font-mono font-bold text-xs text-indigo-600">
                          {alloc.assignment_code}
                        </td>
                        <td className="px-3 py-4 font-semibold text-slate-900">
                          {alloc.assignment_title}
                        </td>
                        <td className="px-3 py-4 text-xs">
                          {alloc.batch_code ? (
                            <span className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded font-semibold">
                              Cohort: {alloc.batch_code}
                            </span>
                          ) : (
                            <span className="bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded font-semibold">
                              Candidate: {alloc.candidate_name || 'Individual'}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-4 text-xs font-mono text-slate-800">
                          {new Date(alloc.due_date_utc).toLocaleString()}
                        </td>
                        <td className="px-3 py-4 text-xs font-mono text-slate-500">
                          {alloc.grace_period_end_utc
                            ? new Date(alloc.grace_period_end_utc).toLocaleString()
                            : 'None'}
                        </td>
                        <td className="py-4 pl-3 pr-6 text-right">
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                            <Clock className="w-3.5 h-3.5" /> {alloc.allocation_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 3: Submissions & Review Queue (Phase 7) */}
      {activeTab === 'submissions' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <label htmlFor="sub_status_filter" className="text-xs font-semibold text-slate-600 flex items-center gap-1.5 shrink-0">
                <Filter className="w-3.5 h-3.5 text-slate-400" /> Filter Status:
              </label>
              <select
                id="sub_status_filter"
                value={selectedStatusFilter}
                onChange={(e) => {
                  setSelectedStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-700 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">All Statuses</option>
                <option value="SUBMITTED">Submitted (Pending Review)</option>
                <option value="UNDER_REVIEW">Under Review</option>
                <option value="APPROVED">Approved (Passed)</option>
                <option value="CORRECTIONS_REQUESTED">Corrections Requested</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>

            <div className="text-xs text-slate-500">
              Showing {submissionData?.items.length || 0} of {submissionData?.total || 0} candidate submissions
            </div>
          </div>

          {/* Submissions Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {isSubmissionsLoading ? (
              <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                <span className="text-sm">Loading submissions & evaluation queue...</span>
              </div>
            ) : !submissionData?.items || submissionData.items.length === 0 ? (
              <div className="p-12 text-center text-slate-500 space-y-3">
                <ClipboardCheck className="w-10 h-10 mx-auto text-slate-300" />
                <h3 className="text-base font-semibold text-slate-700">No Submissions Found</h3>
                <p className="text-xs max-w-sm mx-auto">
                  Candidates have not submitted any deliverables matching the current filter criteria.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/75 text-slate-600 uppercase text-[11px] font-semibold tracking-wider">
                      <th className="py-3.5 pl-6 pr-3">Candidate</th>
                      <th className="px-3 py-3.5">Assignment</th>
                      <th className="px-3 py-3.5">Batch</th>
                      <th className="px-3 py-3.5 text-center">Attempt</th>
                      <th className="px-3 py-3.5">Submitted UTC</th>
                      <th className="px-3 py-3.5">Lateness</th>
                      <th className="px-3 py-3.5">Score</th>
                      <th className="px-3 py-3.5">Status</th>
                      <th className="py-3.5 pl-3 pr-6 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {submissionData.items.map((sub) => {
                      const isApproved = sub.current_submission_status === 'APPROVED';
                      const isCorrections = sub.current_submission_status === 'CORRECTIONS_REQUESTED';
                      const isRejected = sub.current_submission_status === 'REJECTED';

                      return (
                        <tr key={sub.id} className="hover:bg-slate-50/75 transition-colors">
                          <td className="py-4 pl-6 pr-3 font-medium text-slate-900">
                            <div>{sub.candidate_name}</div>
                            <div className="text-[11px] font-mono text-slate-400">{sub.candidate_number}</div>
                          </td>
                          <td className="px-3 py-4">
                            <span className="font-mono font-semibold text-indigo-600 block">{sub.assignment_code}</span>
                            <span className="text-[11px] text-slate-500 line-clamp-1">{sub.assignment_title}</span>
                          </td>
                          <td className="px-3 py-4 font-mono text-slate-600">
                            {sub.batch_code || <span className="text-slate-400">Direct</span>}
                          </td>
                          <td className="px-3 py-4 text-center">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                              #{sub.total_attempts}
                            </span>
                          </td>
                          <td className="px-3 py-4 font-mono text-slate-600">
                            {sub.latest_submitted_at_utc ? (
                              new Date(sub.latest_submitted_at_utc).toLocaleString()
                            ) : (
                              <span className="text-slate-400">N/A</span>
                            )}
                          </td>
                          <td className="px-3 py-4">
                            {sub.is_late ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                                Late
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                On Time
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-4 font-mono">
                            {sub.latest_score !== null && sub.latest_score !== undefined ? (
                              <span className={isApproved ? 'font-bold text-emerald-600' : 'font-semibold text-slate-700'}>
                                {sub.latest_score.toFixed(1)} pts
                              </span>
                            ) : (
                              <span className="text-slate-400 italic">Ungraded</span>
                            )}
                          </td>
                          <td className="px-3 py-4">
                            {isApproved && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Done
                              </span>
                            )}
                            {isCorrections && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                                <Clock className="w-3.5 h-3.5" /> Redo
                              </span>
                            )}
                            {isRejected && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                                Rejected
                              </span>
                            )}
                            {sub.current_submission_status === 'SUBMITTED' && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                                Submitted
                              </span>
                            )}
                            {sub.current_submission_status === 'PENDING' && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                                Not submitted
                              </span>
                            )}
                            {!isApproved && !isCorrections && !isRejected && sub.current_submission_status !== 'SUBMITTED' && sub.current_submission_status !== 'PENDING' && (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                                {sub.current_submission_status}
                              </span>
                            )}
                          </td>
                          <td className="py-4 pl-3 pr-6 text-right space-x-2">
                            <button
                              onClick={() => {
                                setActiveAllocationForSubmit(sub.allocation_id);
                                setIsSubmitDeliverableModalOpen(true);
                              }}
                              title="Submit New Attempt Deliverable"
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
                            >
                              <UploadCloud className="w-3.5 h-3.5 text-slate-400" />
                              Submit
                            </button>
                            <button
                              onClick={() => setSelectedSubmissionIdForReview(sub.id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition-colors"
                            >
                              <Award className="w-3.5 h-3.5" />
                              Evaluate
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
        </div>
      )}


      {/* CREATE ASSIGNMENT MODAL */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Plus className="w-5 h-5 text-indigo-600" />
              Create Curriculum Assignment Template
            </h2>

            {formError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="asg_track" className="block font-medium text-slate-700 text-xs mb-1">
                    Specialization Track *
                  </label>
                  <select
                    id="asg_track"
                    required
                    value={formData.track_id}
                    onChange={(e) => setFormData({ ...formData, track_id: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
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
                  <label htmlFor="asg_code" className="block font-medium text-slate-700 text-xs mb-1">
                    Assignment Code *
                  </label>
                  <input
                    id="asg_code"
                    type="text"
                    required
                    placeholder="e.g. DA-ASG-01"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm font-mono"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="asg_title" className="block font-medium text-slate-700 text-xs mb-1">
                  Assignment Title *
                </label>
                <input
                  id="asg_title"
                  type="text"
                  required
                  placeholder="e.g. Advanced SQL Data Wrangling & Views"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label htmlFor="asg_seq" className="block font-medium text-slate-700 text-xs mb-1">
                    Sequence Order #
                  </label>
                  <input
                    id="asg_seq"
                    type="number"
                    min="1"
                    value={formData.sequence_order}
                    onChange={(e) => setFormData({ ...formData, sequence_order: Number(e.target.value) })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="asg_max" className="block font-medium text-slate-700 text-xs mb-1">
                    Max Score
                  </label>
                  <input
                    id="asg_max"
                    type="number"
                    min="1"
                    value={formData.max_score}
                    onChange={(e) => setFormData({ ...formData, max_score: Number(e.target.value) })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="asg_pass" className="block font-medium text-slate-700 text-xs mb-1">
                    Passing Threshold
                  </label>
                  <input
                    id="asg_pass"
                    type="number"
                    min="1"
                    value={formData.passing_score}
                    onChange={(e) => setFormData({ ...formData, passing_score: Number(e.target.value) })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="asg_inst" className="block font-medium text-slate-700 text-xs mb-1">
                  Instructions & Specifications (Markdown) *
                </label>
                <textarea
                  id="asg_inst"
                  required
                  rows={4}
                  placeholder="# Assignment Brief&#10;Describe problem statements, schemas, and deliverables..."
                  value={formData.instructions_markdown}
                  onChange={(e) => setFormData({ ...formData, instructions_markdown: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm font-mono text-xs"
                />
              </div>

              {/* Rubric Criteria Builder */}
              <div className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <ListPlus className="w-4 h-4 text-indigo-600" />
                    Rubric Scoring Dimensions
                  </span>
                  <button
                    type="button"
                    onClick={addRubricRow}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    + Add Criterion
                  </button>
                </div>

                {rubricRows.map((r, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Title"
                      value={r.title}
                      onChange={(e) => {
                        const updated = [...rubricRows];
                        updated[idx].title = e.target.value;
                        setRubricRows(updated);
                      }}
                      className="flex-1 border border-slate-300 rounded p-1.5 text-xs bg-white"
                    />
                    <input
                      type="number"
                      placeholder="Max Pts"
                      value={r.max_points}
                      onChange={(e) => {
                        const updated = [...rubricRows];
                        updated[idx].max_points = Number(e.target.value);
                        setRubricRows(updated);
                      }}
                      className="w-20 border border-slate-300 rounded p-1.5 text-xs bg-white text-right"
                    />
                    {rubricRows.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeRubricRow(idx)}
                        className="text-slate-400 hover:text-red-600 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="is_mandatory"
                  checked={formData.is_mandatory}
                  onChange={(e) => setFormData({ ...formData, is_mandatory: e.target.checked })}
                  className="rounded text-indigo-600"
                />
                <label htmlFor="is_mandatory" className="text-xs font-medium text-slate-700">
                  Mandatory Curriculum Prerequisite (Required before Project 1 gating)
                </label>
              </div>

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
                  disabled={createAssignmentMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {createAssignmentMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Save Assignment Template
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ALLOCATE ASSIGNMENT MODAL */}
      {isAllocateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-indigo-600" />
              Allocate Assignment to Cohort
            </h2>

            {allocError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{allocError}</span>
              </div>
            )}

            <form onSubmit={handleAllocateSubmit} className="space-y-4 text-sm">
              <div>
                <label htmlFor="alloc_asg" className="block font-medium text-slate-700 text-xs mb-1">
                  Assignment Template *
                </label>
                <select
                  id="alloc_asg"
                  required
                  value={allocData.assignment_id}
                  onChange={(e) => setAllocData({ ...allocData, assignment_id: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                >
                  <option value="">Select assignment...</option>
                  {assignmentData?.items.map((asg: AssignmentItem) => (
                    <option key={asg.id} value={asg.id}>
                      {asg.code} - {asg.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 text-xs mb-1">Allocation Target *</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                    <input
                      type="radio"
                      name="target_type"
                      checked={allocTargetType === 'batch'}
                      onChange={() => setAllocTargetType('batch')}
                      className="text-indigo-600"
                    />
                    Cohort Batch (Group)
                  </label>
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                    <input
                      type="radio"
                      name="target_type"
                      checked={allocTargetType === 'candidate'}
                      onChange={() => setAllocTargetType('candidate')}
                      className="text-indigo-600"
                    />
                    Individual Candidate
                  </label>
                </div>
              </div>

              {allocTargetType === 'batch' ? (
                <div>
                  <label htmlFor="alloc_batch" className="block font-medium text-slate-700 text-xs mb-1">
                    Select Cohort Batch *
                  </label>
                  <select
                    id="alloc_batch"
                    required
                    value={allocData.batch_id}
                    onChange={(e) => setAllocData({ ...allocData, batch_id: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                  >
                    <option value="">Select batch...</option>
                    {batches?.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.batch_code} - {b.title}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div>
                  <label htmlFor="alloc_candidate" className="block font-medium text-slate-700 text-xs mb-1">
                    Candidate UUID *
                  </label>
                  <input
                    id="alloc_candidate"
                    type="text"
                    required
                    placeholder="Candidate UUID"
                    value={allocData.candidate_id}
                    onChange={(e) => setAllocData({ ...allocData, candidate_id: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-sm font-mono text-xs"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="alloc_due" className="block font-medium text-slate-700 text-xs mb-1">
                    Due Date & Time *
                  </label>
                  <input
                    id="alloc_due"
                    type="datetime-local"
                    required
                    value={allocData.due_date_utc}
                    onChange={(e) => setAllocData({ ...allocData, due_date_utc: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                  />
                </div>
                <div>
                  <label htmlFor="alloc_grace" className="block font-medium text-slate-700 text-xs mb-1">
                    Grace Period End
                  </label>
                  <input
                    id="alloc_grace"
                    type="datetime-local"
                    value={allocData.grace_period_end_utc}
                    onChange={(e) => setAllocData({ ...allocData, grace_period_end_utc: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsAllocateModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createAllocationMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {createAllocationMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Confirm Allocation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modals for Phase 7 */}
      <SubmissionReviewModal
        submissionId={selectedSubmissionIdForReview}
        onClose={() => setSelectedSubmissionIdForReview(null)}
      />

      <SubmitDeliverableModal
        isOpen={isSubmitDeliverableModalOpen}
        onClose={() => setIsSubmitDeliverableModalOpen(false)}
        allocations={allocationData?.items || []}
        defaultAllocationId={activeAllocationForSubmit}
      />
    </div>
  );
};
