import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api';
import {
  ProjectGroupItem,
  BatchItem,
  ProjectListItem,
  CandidateItem,
  GroupReadinessResponse,
  ProjectGroupSubmissionItem,
} from '@/types';
import {
  Users,
  Plus,
  Search,
  Crown,
  UserMinus,
  Lock,
  Unlock,
  CheckCircle2,
  Loader2,
  X,
  ShieldAlert,
  ArrowRight,
  Clock,
  Upload,
  FileCheck,
  AlertCircle,
  Trophy,
  UserCheck,
  GraduationCap,
  FolderGit2,
  ExternalLink,
  Award,
  Sparkles,
  CheckSquare,
} from 'lucide-react';

export const ProjectGroupsTab: React.FC = () => {
  const queryClient = useQueryClient();

  // Filters State
  const [selectedBatch, setSelectedBatch] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 9;

  // Selected group for detailed member management
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  // Modals State
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);
  const [targetGroupForMember, setTargetGroupForMember] = useState<ProjectGroupItem | null>(null);

  // Phase 10 Modals State
  const [isAllocateModalOpen, setIsAllocateModalOpen] = useState(false);
  const [targetGroupForAllocate, setTargetGroupForAllocate] = useState<ProjectGroupItem | null>(null);
  const [allocateData, setAllocateData] = useState({
    project_id: '',
    waive_prerequisites: false,
    waiver_justification: '',
  });
  const [allocateError, setAllocateError] = useState<string | null>(null);

  const [isMentorModalOpen, setIsMentorModalOpen] = useState(false);
  const [targetGroupForMentor, setTargetGroupForMentor] = useState<ProjectGroupItem | null>(null);
  const [mentorIdInput, setMentorIdInput] = useState<string>('');
  const [mentorError, setMentorError] = useState<string | null>(null);

  const [isReadinessModalOpen, setIsReadinessModalOpen] = useState(false);
  const [targetGroupForReadiness, setTargetGroupForReadiness] = useState<ProjectGroupItem | null>(null);
  const [selectedCandidateSignoff, setSelectedCandidateSignoff] = useState<string>('');
  const [signoffNotes, setSignoffNotes] = useState<string>('');
  const [advanceOverrideJustification, setAdvanceOverrideJustification] = useState<string>('');
  const [readinessError, setReadinessError] = useState<string | null>(null);

  const [isSubmissionsModalOpen, setIsSubmissionsModalOpen] = useState(false);
  const [targetGroupForSubmissions, setTargetGroupForSubmissions] = useState<ProjectGroupItem | null>(null);
  const [submissionFormData, setSubmissionFormData] = useState({
    submitted_by_candidate_id: '',
    repo_url: '',
    live_demo_url: '',
    documentation_url: '',
    notes: '',
  });
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const [reviewSubmissionId, setReviewSubmissionId] = useState<string | null>(null);
  const [reviewFormData, setReviewFormData] = useState({
    status: 'APPROVED' as 'APPROVED' | 'CORRECTIONS_REQUESTED',
    score: 85,
    feedback: '',
  });
  const [reviewError, setReviewError] = useState<string | null>(null);

  // Queries
  const { data: batches } = useQuery<BatchItem[]>({
    queryKey: ['batches'],
    queryFn: () => api.getBatches(),
  });

  const { data: projectsData } = useQuery({
    queryKey: ['projects-catalog-groups'],
    queryFn: () => api.getProjects({ page_size: 100 }),
  });

  const { data: groupsData, isLoading: isGroupsLoading } = useQuery({
    queryKey: ['project-groups', selectedBatch, selectedStatus, searchTerm, page],
    queryFn: () =>
      api.getProjectGroups({
        batch_id: selectedBatch || undefined,
        status: selectedStatus || undefined,
        search: searchTerm || undefined,
        page,
        page_size: pageSize,
      }),
  });

  const { data: groupDetail, isLoading: isDetailLoading } = useQuery<ProjectGroupItem | null>({
    queryKey: ['project-group-detail', selectedGroupId],
    queryFn: () => (selectedGroupId ? api.getProjectGroup(selectedGroupId) : null),
    enabled: !!selectedGroupId,
  });

  // Query for group readiness
  const {
    data: groupReadiness,
    isLoading: isReadinessLoading,
    refetch: refetchReadiness,
  } = useQuery<GroupReadinessResponse | null>({
    queryKey: ['group-readiness', targetGroupForReadiness?.id],
    queryFn: () => (targetGroupForReadiness ? api.getGroupReadiness(targetGroupForReadiness.id) : null),
    enabled: isReadinessModalOpen && !!targetGroupForReadiness?.id,
  });

  // Query for group submissions
  const {
    data: groupSubmissions,
    isLoading: isSubmissionsLoading,
    refetch: refetchSubmissions,
  } = useQuery<ProjectGroupSubmissionItem[]>({
    queryKey: ['group-submissions', targetGroupForSubmissions?.id],
    queryFn: () =>
      targetGroupForSubmissions ? api.listGroupSubmissions(targetGroupForSubmissions.id) : Promise.resolve([]),
    enabled: isSubmissionsModalOpen && !!targetGroupForSubmissions?.id,
  });

  // Candidates for add member / form group
  const activeBatchIdForCandidates =
    targetGroupForMember?.batch_id ||
    targetGroupForAllocate?.batch_id ||
    targetGroupForReadiness?.batch_id ||
    targetGroupForSubmissions?.batch_id ||
    selectedBatch;

  const { data: candidateList } = useQuery({
    queryKey: ['candidates-for-group', activeBatchIdForCandidates],
    queryFn: () =>
      api.getCandidates({
        batch_id: activeBatchIdForCandidates || undefined,
        lifecycle_status: 'ACTIVE',
        page_size: 100,
      }),
    enabled: !!activeBatchIdForCandidates,
  });

  // Form Group State
  const [formData, setFormData] = useState({
    batch_id: '',
    group_name: '',
    project_id: '',
    min_size: 2,
    target_size: 4,
    max_size: 5,
    selected_candidate_ids: [] as string[],
  });
  const [formError, setFormError] = useState<string | null>(null);

  // Add Member State
  const [selectedCandidateToAdd, setSelectedCandidateToAdd] = useState<string>('');
  const [addMemberRole, setAddMemberRole] = useState<'MEMBER' | 'LEADER'>('MEMBER');
  const [addMemberError, setAddMemberError] = useState<string | null>(null);

  // Mutations
  const formGroupMutation = useMutation({
    mutationFn: (payload: {
      batch_id: string;
      group_name: string;
      project_id?: string;
      min_size: number;
      target_size: number;
      max_size: number;
      candidate_ids?: string[];
    }) => api.createProjectGroup(payload),
    onSuccess: (newGroup) => {
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      setIsFormModalOpen(false);
      setSelectedGroupId(newGroup.id);
      setFormData({
        batch_id: '',
        group_name: '',
        project_id: '',
        min_size: 2,
        target_size: 4,
        max_size: 5,
        selected_candidate_ids: [],
      });
      setFormError(null);
    },
    onError: (err: ApiError) => {
      setFormError(err.data?.detail || err.message || 'Failed to form project group.');
    },
  });

  const addMemberMutation = useMutation({
    mutationFn: ({
      groupId,
      candidateId,
      role,
    }: {
      groupId: string;
      candidateId: string;
      role: 'LEADER' | 'MEMBER';
    }) => api.addGroupMember(groupId, { candidate_id: candidateId, role }),
    onSuccess: (updatedGroup) => {
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      queryClient.invalidateQueries({ queryKey: ['project-group-detail', updatedGroup.id] });
      setIsAddMemberModalOpen(false);
      setSelectedCandidateToAdd('');
      setAddMemberError(null);
    },
    onError: (err: ApiError) => {
      setAddMemberError(err.data?.detail || err.message || 'Failed to add member to group.');
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: ({
      groupId,
      candidateId,
      override,
    }: {
      groupId: string;
      candidateId: string;
      override?: boolean;
    }) => api.removeGroupMember(groupId, candidateId, override),
    onSuccess: (updatedGroup) => {
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      queryClient.invalidateQueries({ queryKey: ['project-group-detail', updatedGroup.id] });
    },
    onError: (err: ApiError, variables) => {
      if (err.status === 422 && err.data?.detail?.includes('minimum team size')) {
        const confirmOverride = window.confirm(
          `${err.data.detail}\n\nDo you want to apply administrative override to remove this member anyway?`
        );
        if (confirmOverride) {
          removeMemberMutation.mutate({
            groupId: variables.groupId,
            candidateId: variables.candidateId,
            override: true,
          });
        }
      } else {
        alert(err.data?.detail || err.message || 'Failed to remove member.');
      }
    },
  });

  const setLeaderMutation = useMutation({
    mutationFn: ({ groupId, candidateId }: { groupId: string; candidateId: string }) =>
      api.setGroupLeader(groupId, candidateId),
    onSuccess: (updatedGroup) => {
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      queryClient.invalidateQueries({ queryKey: ['project-group-detail', updatedGroup.id] });
    },
    onError: (err: ApiError) => {
      alert(err.data?.detail || err.message || 'Failed to assign team leader.');
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ groupId, status }: { groupId: string; status: string }) =>
      api.updateProjectGroup(groupId, { status }),
    onSuccess: (updatedGroup) => {
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      queryClient.invalidateQueries({ queryKey: ['project-group-detail', updatedGroup.id] });
    },
    onError: (err: ApiError) => {
      alert(err.data?.detail || err.message || 'Failed to update group status.');
    },
  });

  // Phase 10 Mutations
  const assignMentorMutation = useMutation({
    mutationFn: ({ groupId, mentor_id }: { groupId: string; mentor_id: string }) =>
      api.assignGroupMentor(groupId, mentor_id),
    onSuccess: (updatedGroup) => {
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      queryClient.invalidateQueries({ queryKey: ['project-group-detail', updatedGroup.id] });
      setIsMentorModalOpen(false);
      setMentorIdInput('');
      setMentorError(null);
    },
    onError: (err: ApiError) => {
      setMentorError(err.data?.detail || err.message || 'Failed to assign mentor.');
    },
  });

  const allocateProjectMutation = useMutation({
    mutationFn: ({
      groupId,
      payload,
    }: {
      groupId: string;
      payload: { project_id: string; waive_prerequisites?: boolean; waiver_justification?: string };
    }) => api.allocateProjectToGroup(groupId, payload),
    onSuccess: (updatedGroup) => {
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      queryClient.invalidateQueries({ queryKey: ['project-group-detail', updatedGroup.id] });
      setIsAllocateModalOpen(false);
      setAllocateData({ project_id: '', waive_prerequisites: false, waiver_justification: '' });
      setAllocateError(null);
    },
    onError: (err: ApiError) => {
      setAllocateError(err.data?.detail || err.message || 'Failed to allocate project.');
    },
  });

  const submitDeliverableMutation = useMutation({
    mutationFn: ({
      groupId,
      payload,
    }: {
      groupId: string;
      payload: {
        submitted_by_candidate_id: string;
        repo_url?: string;
        live_demo_url?: string;
        documentation_url?: string;
        notes?: string;
      };
    }) => api.submitGroupDeliverable(groupId, payload),
    onSuccess: () => {
      refetchSubmissions();
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      if (targetGroupForSubmissions) {
        queryClient.invalidateQueries({ queryKey: ['project-group-detail', targetGroupForSubmissions.id] });
      }
      setSubmissionFormData({
        submitted_by_candidate_id: '',
        repo_url: '',
        live_demo_url: '',
        documentation_url: '',
        notes: '',
      });
      setSubmissionError(null);
    },
    onError: (err: ApiError) => {
      setSubmissionError(err.data?.detail || err.message || 'Failed to submit deliverable.');
    },
  });

  const reviewSubmissionMutation = useMutation({
    mutationFn: ({
      groupId,
      submissionId,
      payload,
    }: {
      groupId: string;
      submissionId: string;
      payload: {
        status: 'APPROVED' | 'CORRECTIONS_REQUESTED';
        score?: number;
        feedback?: string;
      };
    }) => api.reviewGroupSubmission(groupId, submissionId, payload),
    onSuccess: () => {
      refetchSubmissions();
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      if (targetGroupForSubmissions) {
        queryClient.invalidateQueries({ queryKey: ['project-group-detail', targetGroupForSubmissions.id] });
      }
      setReviewSubmissionId(null);
      setReviewFormData({ status: 'APPROVED', score: 85, feedback: '' });
      setReviewError(null);
    },
    onError: (err: ApiError) => {
      setReviewError(err.data?.detail || err.message || 'Failed to submit review.');
    },
  });

  const progressionRequestMutation = useMutation({
    mutationFn: ({
      groupId,
      payload,
    }: {
      groupId: string;
      payload: { candidate_id: string; notes?: string };
    }) => api.requestGroupProgression(groupId, payload),
    onSuccess: () => {
      refetchReadiness();
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      if (targetGroupForReadiness) {
        queryClient.invalidateQueries({ queryKey: ['project-group-detail', targetGroupForReadiness.id] });
      }
      setSelectedCandidateSignoff('');
      setSignoffNotes('');
      setReadinessError(null);
    },
    onError: (err: ApiError) => {
      setReadinessError(err.data?.detail || err.message || 'Failed to submit progression sign-off.');
    },
  });

  const advanceGroupMutation = useMutation({
    mutationFn: ({
      groupId,
      payload,
    }: {
      groupId: string;
      payload?: { override_justification?: string };
    }) => api.advanceGroup(groupId, payload),
    onSuccess: (updatedGroup) => {
      refetchReadiness();
      queryClient.invalidateQueries({ queryKey: ['project-groups'] });
      queryClient.invalidateQueries({ queryKey: ['project-group-detail', updatedGroup.id] });
      setIsReadinessModalOpen(false);
      setAdvanceOverrideJustification('');
      setReadinessError(null);
    },
    onError: (err: ApiError) => {
      setReadinessError(err.data?.detail || err.message || 'Failed to advance group.');
    },
  });

  // Helpers
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'FORMING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-700 border border-amber-300">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            FORMING
          </span>
        );
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            ACTIVE
          </span>
        );
      case 'LOCKED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-700 border border-purple-300">
            <Lock className="w-3 h-3 text-purple-600" />
            LOCKED
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-700 border border-blue-300">
            COMPLETED
          </span>
        );
      case 'DISSOLVED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-700 border border-rose-300">
            DISSOLVED
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  const getReadinessBadge = (status?: string) => {
    switch (status) {
      case 'READY_FOR_NEXT_PROJECT':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            READY FOR ADVANCEMENT
          </span>
        );
      case 'BLOCKED_PENDING_MEMBERS':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-700 border border-amber-300">
            <Clock className="w-3 h-3 text-amber-600" />
            PENDING SIGN-OFFS
          </span>
        );
      case 'SUBMITTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-700 border border-blue-300">
            <Upload className="w-3 h-3 text-blue-600" />
            SUBMITTED
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-700 border border-indigo-300">
            <FileCheck className="w-3 h-3 text-indigo-600" />
            UNDER REVIEW
          </span>
        );
      case 'CORRECTIONS_REQUESTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-700 border border-rose-300">
            <AlertCircle className="w-3 h-3 text-rose-600" />
            CORRECTIONS REQUIRED
          </span>
        );
      case 'APPROVED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-700 border border-teal-300">
            <CheckCircle2 className="w-3 h-3 text-teal-600" />
            DELIVERABLE APPROVED
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-700 border border-purple-300">
            <Trophy className="w-3 h-3 text-purple-600" />
            COMPLETED
          </span>
        );
      case 'AWAITING_SUBMISSION':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-700 border border-slate-300">
            <Clock className="w-3 h-3 text-slate-500" />
            AWAITING SUBMISSION
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">
            {status || 'NOT_READY'}
          </span>
        );
    }
  };

  const renderTeamSizeMeter = (activeCount: number, minSize: number, targetSize: number, maxSize: number) => {
    const percentage = Math.min(100, Math.round((activeCount / maxSize) * 100));
    let barColor = 'bg-amber-500';
    let statusText = `Forming (${activeCount}/${targetSize}) - Need ${minSize - activeCount} more to activate`;

    if (activeCount >= minSize && activeCount <= maxSize) {
      barColor = 'bg-emerald-500';
      statusText =
        activeCount === targetSize
          ? `Optimal Target Size (${activeCount}/${targetSize})`
          : activeCount < targetSize
          ? `Ready (${activeCount}/${targetSize} Target)`
          : `At Max Capacity (${activeCount}/${maxSize})`;
    } else if (activeCount > maxSize) {
      barColor = 'bg-rose-500';
      statusText = `Over Capacity (${activeCount}/${maxSize})`;
    }

    return (
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-slate-600">
          <span className="font-medium flex items-center gap-1">
            <Users className="w-3.5 h-3.5 text-slate-400" />
            Team Capacity
          </span>
          <span className="font-mono font-semibold text-slate-900">
            {activeCount} / {targetSize} (Min: {minSize}, Max: {maxSize})
          </span>
        </div>
        <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden border border-slate-200">
          <div
            className={`h-full ${barColor} transition-all duration-300`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <p className="text-[11px] text-slate-500 italic">{statusText}</p>
      </div>
    );
  };

  return (
    <div className="space-y-6" id="project-groups-container">
      {/* Action & Filter Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[220px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              id="groups-search-input"
              type="text"
              placeholder="Search group name or batch..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
            />
          </div>

          <select
            id="groups-batch-filter"
            value={selectedBatch}
            onChange={(e) => {
              setSelectedBatch(e.target.value);
              setPage(1);
            }}
            className="text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
          >
            <option value="">All Cohort Batches</option>
            {batches?.map((b) => (
              <option key={b.id} value={b.id}>
                {b.batch_code} - {b.title}
              </option>
            ))}
          </select>

          <select
            id="groups-status-filter"
            value={selectedStatus}
            onChange={(e) => {
              setSelectedStatus(e.target.value);
              setPage(1);
            }}
            className="text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all shadow-sm"
          >
            <option value="">All Group Statuses</option>
            <option value="FORMING">FORMING (Under min capacity)</option>
            <option value="ACTIVE">ACTIVE (Ready for project)</option>
            <option value="LOCKED">LOCKED (Roster frozen)</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="DISSOLVED">DISSOLVED</option>
          </select>
        </div>

        {/* Action Button */}
        <button
          id="btn-form-project-group"
          onClick={() => {
            setFormData({
              batch_id: selectedBatch || (batches && batches.length > 0 ? batches[0].id : ''),
              group_name: '',
              project_id: '',
              min_size: 2,
              target_size: 4,
              max_size: 5,
              selected_candidate_ids: [],
            });
            setFormError(null);
            setIsFormModalOpen(true);
          }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-sm self-start lg:self-auto"
        >
          <Plus className="w-4 h-4" />
          Form Project Group
        </button>
      </div>

      {/* Main Groups List Grid */}
      {isGroupsLoading ? (
        <div className="flex flex-col items-center justify-center p-12 space-y-3 bg-white rounded-xl border border-slate-200">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
          <p className="text-sm text-slate-500">Loading project group rosters...</p>
        </div>
      ) : !groupsData || groupsData.items.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center">
          <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No Project Groups Found</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            {searchTerm || selectedBatch || selectedStatus
              ? 'No project groups match your current filter criteria.'
              : 'Form cohort student groups with dynamic team sizing (min 2, target 4, max 5) to begin project allocations.'}
          </p>
          <button
            onClick={() => setIsFormModalOpen(true)}
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg text-indigo-600 bg-indigo-50 hover:bg-indigo-100 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Form First Group
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {groupsData.items.map((group) => (
            <div
              key={group.id}
              className={`bg-white rounded-xl border transition-all duration-200 shadow-sm hover:shadow-md flex flex-col justify-between p-5 ${
                selectedGroupId === group.id
                  ? 'border-indigo-500 ring-2 ring-indigo-500/20'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-bold text-slate-900 group-name-title">
                      {group.group_name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium border border-slate-200">
                        {group.batch_code || 'Cohort'}
                      </span>
                      {group.project_title && (
                        <span
                          className="text-xs text-indigo-700 font-medium truncate max-w-[150px]"
                          title={group.project_title}
                        >
                          • {group.project_title}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {getStatusBadge(group.status)}
                    {getReadinessBadge(group.readiness_status)}
                  </div>
                </div>

                {/* Mentor Info */}
                <div className="flex items-center justify-between text-xs bg-slate-50/70 p-2 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-1.5 text-slate-600">
                    <GraduationCap className="w-3.5 h-3.5 text-indigo-500" />
                    <span>Mentor:</span>
                    <span className="font-semibold text-slate-800">
                      {group.mentor_name || 'Unassigned'}
                    </span>
                  </div>
                  <button
                    id={`btn-mentor-group-${group.id}`}
                    onClick={() => {
                      setTargetGroupForMentor(group as any);
                      setMentorIdInput('');
                      setMentorError(null);
                      setIsMentorModalOpen(true);
                    }}
                    className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
                  >
                    {group.mentor_name ? 'Change' : 'Assign'}
                  </button>
                </div>

                {/* Team Sizing Meter */}
                {renderTeamSizeMeter(
                  group.active_members_count,
                  group.min_size,
                  group.target_size,
                  group.max_size
                )}
              </div>

              {/* Card Footer Actions */}
              <div className="mt-5 pt-4 border-t border-slate-100 space-y-2.5">
                <div className="flex items-center justify-between">
                  <button
                    id={`btn-manage-group-${group.id}`}
                    onClick={() => setSelectedGroupId(selectedGroupId === group.id ? null : group.id)}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors"
                  >
                    {selectedGroupId === group.id ? 'Hide Roster' : 'Manage Team Roster'}
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>

                  <div className="flex items-center gap-1.5">
                    {/* Quick Allocate Project Button */}
                    <button
                      id={`btn-allocate-group-${group.id}`}
                      onClick={() => {
                        setTargetGroupForAllocate(group as any);
                        setAllocateData({
                          project_id: group.project_id || '',
                          waive_prerequisites: false,
                          waiver_justification: '',
                        });
                        setAllocateError(null);
                        setIsAllocateModalOpen(true);
                      }}
                      className="px-2 py-1 text-[11px] font-semibold rounded text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors"
                      title="Allocate / Reallocate Project to Group"
                    >
                      Allocate
                    </button>

                    {/* Quick Readiness Button */}
                    <button
                      id={`btn-readiness-group-${group.id}`}
                      onClick={() => {
                        setTargetGroupForReadiness(group as any);
                        setSelectedCandidateSignoff('');
                        setSignoffNotes('');
                        setAdvanceOverrideJustification('');
                        setReadinessError(null);
                        setIsReadinessModalOpen(true);
                      }}
                      className="px-2 py-1 text-[11px] font-semibold rounded text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors"
                      title="View Group Readiness and Candidate Sign-offs"
                    >
                      Readiness
                    </button>

                    {/* Quick Submissions Button */}
                    <button
                      id={`btn-submissions-group-${group.id}`}
                      onClick={() => {
                        setTargetGroupForSubmissions(group as any);
                        setSubmissionFormData({
                          submitted_by_candidate_id: '',
                          repo_url: '',
                          live_demo_url: '',
                          documentation_url: '',
                          notes: '',
                        });
                        setSubmissionError(null);
                        setReviewSubmissionId(null);
                        setIsSubmissionsModalOpen(true);
                      }}
                      className="px-2 py-1 text-[11px] font-semibold rounded text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 transition-colors"
                      title="Deliverable Submissions and Reviews"
                    >
                      Submissions
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Selected Group Detailed Roster Panel */}
      {selectedGroupId && (
        <div
          id="group-detail-panel"
          className="bg-white rounded-xl border border-indigo-200 p-6 shadow-sm space-y-6 animate-fadeIn"
        >
          {isDetailLoading || !groupDetail ? (
            <div className="flex items-center justify-center p-8 space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
              <span className="text-xs text-slate-500 ml-2">Loading group details...</span>
            </div>
          ) : (
            <>
              {/* Detailed Header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-slate-900">{groupDetail.group_name}</h2>
                    {getStatusBadge(groupDetail.status)}
                    {getReadinessBadge(groupDetail.readiness_status)}
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 mt-1.5">
                    <p>
                      Batch: <span className="font-semibold text-slate-700">{groupDetail.batch_code}</span>
                    </p>
                    <p>
                      Active Members:{' '}
                      <span className="font-mono font-bold text-slate-800">
                        {groupDetail.active_members_count}
                      </span>{' '}
                      (Min: {groupDetail.min_size}, Target: {groupDetail.target_size}, Max:{' '}
                      {groupDetail.max_size})
                    </p>
                    {groupDetail.project_title && (
                      <p>
                        Project:{' '}
                        <span className="font-semibold text-indigo-700">
                          {groupDetail.project_title}
                        </span>
                      </p>
                    )}
                    {groupDetail.current_milestone_title && (
                      <p>
                        Current Milestone:{' '}
                        <span className="font-medium text-slate-700">
                          {groupDetail.current_milestone_title}
                        </span>
                      </p>
                    )}
                    <p>
                      Mentor:{' '}
                      <span className="font-semibold text-slate-800">
                        {groupDetail.mentor_name || 'Unassigned'}
                      </span>
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {/* Allocate Project */}
                  <button
                    id="btn-detail-allocate-project"
                    onClick={() => {
                      setTargetGroupForAllocate(groupDetail);
                      setAllocateData({
                        project_id: groupDetail.project_id || '',
                        waive_prerequisites: false,
                        waiver_justification: '',
                      });
                      setAllocateError(null);
                      setIsAllocateModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Allocate Project
                  </button>

                  {/* Assign Mentor */}
                  <button
                    id="btn-detail-assign-mentor"
                    onClick={() => {
                      setTargetGroupForMentor(groupDetail);
                      setMentorIdInput(groupDetail.mentor_id || '');
                      setMentorError(null);
                      setIsMentorModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition-colors"
                  >
                    <GraduationCap className="w-3.5 h-3.5 text-indigo-600" />
                    Assign Mentor
                  </button>

                  {/* Readiness Drawer */}
                  <button
                    id="btn-detail-readiness"
                    onClick={() => {
                      setTargetGroupForReadiness(groupDetail);
                      setSelectedCandidateSignoff('');
                      setSignoffNotes('');
                      setAdvanceOverrideJustification('');
                      setReadinessError(null);
                      setIsReadinessModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors"
                  >
                    <CheckSquare className="w-3.5 h-3.5" />
                    Readiness & Sign-offs
                  </button>

                  {/* Deliverables Drawer */}
                  <button
                    id="btn-detail-submissions"
                    onClick={() => {
                      setTargetGroupForSubmissions(groupDetail);
                      setSubmissionFormData({
                        submitted_by_candidate_id: '',
                        repo_url: '',
                        live_demo_url: '',
                        documentation_url: '',
                        notes: '',
                      });
                      setSubmissionError(null);
                      setReviewSubmissionId(null);
                      setIsSubmissionsModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 transition-colors"
                  >
                    <FolderGit2 className="w-3.5 h-3.5" />
                    Submissions
                  </button>

                  {groupDetail.status === 'ACTIVE' && (
                    <button
                      id="btn-lock-group"
                      onClick={() =>
                        updateStatusMutation.mutate({ groupId: groupDetail.id, status: 'LOCKED' })
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 transition-colors"
                    >
                      <Lock className="w-3.5 h-3.5" />
                      Lock Team Roster
                    </button>
                  )}

                  {groupDetail.status === 'LOCKED' && (
                    <button
                      id="btn-unlock-group"
                      onClick={() =>
                        updateStatusMutation.mutate({ groupId: groupDetail.id, status: 'ACTIVE' })
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors"
                    >
                      <Unlock className="w-3.5 h-3.5" />
                      Unlock Team
                    </button>
                  )}

                  {groupDetail.status !== 'DISSOLVED' && (
                    <button
                      id="btn-dissolve-group"
                      onClick={() => {
                        if (
                          window.confirm(
                            'Are you sure you want to dissolve this project group? Active members will be marked as TRANSFERRED/REMOVED.'
                          )
                        ) {
                          updateStatusMutation.mutate({ groupId: groupDetail.id, status: 'DISSOLVED' });
                        }
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-colors"
                    >
                      Dissolve Group
                    </button>
                  )}

                  {groupDetail.active_members_count < groupDetail.max_size &&
                    groupDetail.status !== 'LOCKED' &&
                    groupDetail.status !== 'DISSOLVED' && (
                      <button
                        id="btn-add-member-detail"
                        onClick={() => {
                          setTargetGroupForMember(groupDetail);
                          setSelectedCandidateToAdd('');
                          setAddMemberError(null);
                          setIsAddMemberModalOpen(true);
                        }}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        Add Member
                      </button>
                    )}

                  <button
                    onClick={() => setSelectedGroupId(null)}
                    className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Members Table */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Enrolled Team Members ({groupDetail.members?.length || 0})
                </h4>

                {!groupDetail.members || groupDetail.members.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No members assigned yet.</p>
                ) : (
                  <div className="overflow-x-auto border border-slate-200 rounded-lg">
                    <table className="w-full text-left text-xs text-slate-700">
                      <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                        <tr>
                          <th className="py-2.5 px-4">Candidate</th>
                          <th className="py-2.5 px-3">Candidate #</th>
                          <th className="py-2.5 px-3">Role</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Joined</th>
                          <th className="py-2.5 px-4 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {groupDetail.members.map((member) => (
                          <tr
                            key={member.id}
                            className={`hover:bg-slate-50/70 transition-colors ${
                              member.member_status !== 'ACTIVE' ? 'opacity-50 bg-slate-50/40' : ''
                            }`}
                          >
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2.5">
                                <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs uppercase">
                                  {member.candidate_name ? member.candidate_name.charAt(0) : 'U'}
                                </div>
                                <div>
                                  <span className="font-semibold text-slate-900 block member-candidate-name">
                                    {member.candidate_name || 'Candidate'}
                                  </span>
                                  <span className="text-[11px] text-slate-400">
                                    {member.candidate_email}
                                  </span>
                                </div>
                              </div>
                            </td>
                            <td className="py-3 px-3 font-mono font-medium text-slate-600">
                              {member.candidate_number || '—'}
                            </td>
                            <td className="py-3 px-3">
                              {member.role === 'LEADER' ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-300">
                                  <Crown className="w-3 h-3 text-amber-500" />
                                  LEADER
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600">
                                  MEMBER
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-3">
                              <span
                                className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  member.member_status === 'ACTIVE'
                                    ? 'bg-emerald-50 text-emerald-700'
                                    : 'bg-slate-100 text-slate-500'
                                }`}
                              >
                                {member.member_status}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-slate-500 text-[11px]">
                              {new Date(member.joined_at).toLocaleDateString()}
                            </td>
                            <td className="py-3 px-4 text-right">
                              {member.member_status === 'ACTIVE' &&
                                groupDetail.status !== 'LOCKED' &&
                                groupDetail.status !== 'DISSOLVED' && (
                                  <div className="inline-flex items-center gap-2">
                                    {member.role !== 'LEADER' && (
                                      <button
                                        id={`btn-make-leader-${member.candidate_id}`}
                                        onClick={() =>
                                          setLeaderMutation.mutate({
                                            groupId: groupDetail.id,
                                            candidateId: member.candidate_id,
                                          })
                                        }
                                        className="text-[11px] font-semibold text-amber-600 hover:text-amber-800 flex items-center gap-1 hover:underline"
                                        title="Promote to Team Leader"
                                      >
                                        <Crown className="w-3 h-3" />
                                        Make Leader
                                      </button>
                                    )}
                                    <button
                                      id={`btn-remove-member-${member.candidate_id}`}
                                      onClick={() =>
                                        removeMemberMutation.mutate({
                                          groupId: groupDetail.id,
                                          candidateId: member.candidate_id,
                                        })
                                      }
                                      className="text-[11px] font-semibold text-rose-600 hover:text-rose-800 flex items-center gap-1 hover:underline"
                                      title="Remove from Group"
                                    >
                                      <UserMinus className="w-3 h-3" />
                                      Remove
                                    </button>
                                  </div>
                                )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Allocate Project Modal (Phase 10) */}
      {isAllocateModalOpen && targetGroupForAllocate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-slate-900">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold">
                  Allocate Project to {targetGroupForAllocate.group_name}
                </h3>
              </div>
              <button
                onClick={() => setIsAllocateModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {allocateError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Allocation Error:</span>
                  <p className="mt-0.5">{allocateError}</p>
                </div>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!allocateData.project_id) return;
                allocateProjectMutation.mutate({
                  groupId: targetGroupForAllocate.id,
                  payload: {
                    project_id: allocateData.project_id,
                    waive_prerequisites: allocateData.waive_prerequisites,
                    waiver_justification: allocateData.waive_prerequisites
                      ? allocateData.waiver_justification
                      : undefined,
                  },
                });
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label htmlFor="allocate-project-select" className="block font-semibold text-slate-700 mb-1">
                  Select Project Specification *
                </label>
                <select
                  id="allocate-project-select"
                  required
                  value={allocateData.project_id}
                  onChange={(e) => setAllocateData({ ...allocateData, project_id: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-xs"
                >
                  <option value="">Select project specification...</option>
                  {projectsData?.items?.map((p: ProjectListItem) => (
                    <option key={p.id} value={p.id}>
                      {p.code} - {p.title} ({p.tier})
                    </option>
                  ))}
                </select>
              </div>

              {/* Prerequisite Waiver Checkbox (BR-PRJ-01) */}
              <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-lg space-y-2.5">
                <label className="flex items-start gap-2.5 cursor-pointer text-xs font-medium text-amber-950">
                  <input
                    id="checkbox-waive-prerequisites"
                    type="checkbox"
                    checked={allocateData.waive_prerequisites}
                    onChange={(e) =>
                      setAllocateData({ ...allocateData, waive_prerequisites: e.target.checked })
                    }
                    className="mt-0.5 rounded border-amber-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="font-semibold block">
                      Waive Prerequisite Mandatory Assignments
                    </span>
                    <span className="text-[11px] text-amber-800 block">
                      Enable if candidates are missing prerequisite assignments but have academic coordinator
                      approval.
                    </span>
                  </div>
                </label>

                {allocateData.waive_prerequisites && (
                  <div>
                    <label
                      htmlFor="allocate-waiver-justification"
                      className="block font-semibold text-slate-700 mb-1"
                    >
                      Waiver Justification * (Audit Logged)
                    </label>
                    <textarea
                      id="allocate-waiver-justification"
                      required
                      rows={2}
                      placeholder="State academic reason or coordinator approval rationale..."
                      value={allocateData.waiver_justification}
                      onChange={(e) =>
                        setAllocateData({ ...allocateData, waiver_justification: e.target.value })
                      }
                      className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                    />
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsAllocateModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-allocate-project"
                  type="submit"
                  disabled={
                    allocateProjectMutation.isPending ||
                    !allocateData.project_id ||
                    (allocateData.waive_prerequisites && !allocateData.waiver_justification.trim())
                  }
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50"
                >
                  {allocateProjectMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Confirm Project Allocation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign Mentor Modal (Phase 10) */}
      {isMentorModalOpen && targetGroupForMentor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-slate-900">
                <GraduationCap className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold">
                  Assign Staff Mentor to {targetGroupForMentor.group_name}
                </h3>
              </div>
              <button
                onClick={() => setIsMentorModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {mentorError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <p>{mentorError}</p>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!mentorIdInput.trim()) return;
                assignMentorMutation.mutate({
                  groupId: targetGroupForMentor.id,
                  mentor_id: mentorIdInput.trim(),
                });
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label htmlFor="assign-mentor-input" className="block font-semibold text-slate-700 mb-1">
                  Staff Mentor / Evaluator User ID *
                </label>
                <input
                  id="assign-mentor-input"
                  type="text"
                  required
                  placeholder="Enter User UUID (e.g. 00000000-0000-0000-0000-000000000001)"
                  value={mentorIdInput}
                  onChange={(e) => setMentorIdInput(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 font-mono text-xs"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Staff mentors are authorized to review deliverables, grade rubric scores, and approve
                  project milestones.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsMentorModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-assign-mentor"
                  type="submit"
                  disabled={assignMentorMutation.isPending || !mentorIdInput.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50"
                >
                  {assignMentorMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Assign Mentor
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Group Readiness & Sign-offs Modal (Phase 10) */}
      {isReadinessModalOpen && targetGroupForReadiness && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-slate-900">
                <CheckSquare className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold">
                  Group Readiness & Advancement: {targetGroupForReadiness.group_name}
                </h3>
              </div>
              <button
                onClick={() => setIsReadinessModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {readinessError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <p>{readinessError}</p>
              </div>
            )}

            {isReadinessLoading || !groupReadiness ? (
              <div className="flex flex-col items-center justify-center p-8 space-y-2">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                <p className="text-xs text-slate-500">Checking collaborative readiness state machine...</p>
              </div>
            ) : (
              <div className="space-y-4 text-xs">
                {/* Readiness Summary Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <div>
                    <span className="text-[11px] text-slate-500 font-medium block">Readiness Status</span>
                    <div id="readiness-status-badge" className="mt-1">
                      {getReadinessBadge(groupReadiness.readiness_status)}
                    </div>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 font-medium block">Deliverable Status</span>
                    <span
                      id="deliverable-approved-status"
                      className={`inline-block mt-1 font-bold px-2 py-0.5 rounded text-[11px] ${
                        groupReadiness.deliverable_approved
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {groupReadiness.deliverable_approved ? 'APPROVED' : 'PENDING APPROVAL'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 font-medium block">Member Sign-offs</span>
                    <span className="font-mono font-bold text-slate-900 mt-1 block">
                      {groupReadiness.requests_count} / {groupReadiness.active_members_count} Signed
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-500 font-medium block">Eligible to Advance</span>
                    <span
                      className={`inline-block mt-1 font-bold px-2 py-0.5 rounded text-[11px] ${
                        groupReadiness.can_advance
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {groupReadiness.can_advance ? 'YES' : 'NO'}
                    </span>
                  </div>
                </div>

                {/* Collaborative Member Checklist (AC-PRJ-004) */}
                <div className="space-y-2">
                  <h4 className="font-bold text-slate-800 flex items-center justify-between">
                    <span>Collaborative Member Sign-off Status</span>
                    <span className="text-[11px] font-normal text-slate-500">
                      All active members must sign off to advance
                    </span>
                  </h4>

                  <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden bg-white">
                    {groupReadiness.progression_requests.length === 0 && (
                      <p className="p-3 text-slate-400 italic text-[11px]">
                        No members have signed off yet.
                      </p>
                    )}
                    {groupReadiness.progression_requests.map((req) => (
                      <div
                        key={req.id}
                        className="p-3 flex items-center justify-between hover:bg-slate-50/50"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          <span className="font-semibold text-slate-900">
                            {req.candidate_name || req.candidate_number || 'Candidate'}
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-400">
                          {new Date(req.requested_at).toLocaleString()}
                        </span>
                      </div>
                    ))}

                    {groupReadiness.pending_candidate_names.map((name, idx) => (
                      <div key={idx} className="p-3 flex items-center justify-between bg-amber-50/30">
                        <div className="flex items-center gap-2">
                          <Clock className="w-4 h-4 text-amber-500" />
                          <span className="font-medium text-slate-700">{name}</span>
                        </div>
                        <span className="text-[11px] font-semibold text-amber-700">Awaiting Sign-off</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Candidate Sign-Off Form */}
                <div className="p-4 bg-indigo-50/50 border border-indigo-100 rounded-lg space-y-3">
                  <h4 className="font-bold text-indigo-950 flex items-center gap-1.5">
                    <UserCheck className="w-4 h-4 text-indigo-600" />
                    Submit Progression Sign-off (Candidate Action)
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label
                        htmlFor="select-signoff-candidate"
                        className="block font-semibold text-slate-700 mb-1"
                      >
                        Select Candidate to Sign-off
                      </label>
                      <select
                        id="select-signoff-candidate"
                        value={selectedCandidateSignoff}
                        onChange={(e) => setSelectedCandidateSignoff(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg p-2 bg-white text-xs"
                      >
                        <option value="">Select candidate...</option>
                        {candidateList?.items?.map((c: CandidateItem) => (
                          <option key={c.id} value={c.id}>
                            {c.first_name} {c.last_name} ({c.candidate_number})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor="input-signoff-notes" className="block font-semibold text-slate-700 mb-1">
                        Sign-off Notes (Optional)
                      </label>
                      <input
                        id="input-signoff-notes"
                        type="text"
                        placeholder="e.g. Completed deliverable review and tests"
                        value={signoffNotes}
                        onChange={(e) => setSignoffNotes(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <button
                      id="btn-submit-signoff"
                      type="button"
                      disabled={progressionRequestMutation.isPending || !selectedCandidateSignoff}
                      onClick={() => {
                        progressionRequestMutation.mutate({
                          groupId: targetGroupForReadiness.id,
                          payload: {
                            candidate_id: selectedCandidateSignoff,
                            notes: signoffNotes || undefined,
                          },
                        });
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors disabled:opacity-50"
                    >
                      {progressionRequestMutation.isPending && (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      )}
                      Record Sign-off
                    </button>
                  </div>
                </div>

                {/* Advancement Section (AC-PRJ-004 & BR-PRJ-02) */}
                <div className="p-4 bg-emerald-50/50 border border-emerald-100 rounded-lg space-y-3">
                  <h4 className="font-bold text-emerald-950 flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-emerald-600" />
                    Tier Advancement (Staff Action)
                  </h4>
                  <p className="text-[11px] text-slate-600">
                    Advances group to the next milestone/tier (Tier 1 → Tier 2 → Tier 3 Capstone →
                    Completed). All active members must have signed off and deliverable approved, or
                    provide coordinator override justification.
                  </p>

                  {!groupReadiness.can_advance && (
                    <div>
                      <label
                        htmlFor="advance-override-justification"
                        className="block font-semibold text-slate-700 mb-1"
                      >
                        Coordinator Override Justification (Required if not fully signed)
                      </label>
                      <textarea
                        id="advance-override-justification"
                        rows={2}
                        placeholder="Provide formal pedagogical justification to bypass pending sign-offs..."
                        value={advanceOverrideJustification}
                        onChange={(e) => setAdvanceOverrideJustification(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                      />
                    </div>
                  )}

                  <div className="flex justify-end pt-2">
                    <button
                      id="btn-confirm-advance-group"
                      type="button"
                      disabled={
                        advanceGroupMutation.isPending ||
                        (!groupReadiness.can_advance && !advanceOverrideJustification.trim())
                      }
                      onClick={() => {
                        advanceGroupMutation.mutate({
                          groupId: targetGroupForReadiness.id,
                          payload: advanceOverrideJustification.trim()
                            ? { override_justification: advanceOverrideJustification.trim() }
                            : undefined,
                        });
                      }}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 transition-colors disabled:opacity-50"
                    >
                      {advanceGroupMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      Advance Group to Next Project / Capstone
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Deliverable Submissions & Review Modal (Phase 10) */}
      {isSubmissionsModalOpen && targetGroupForSubmissions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-slate-900">
                <FolderGit2 className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold">
                  Deliverable Submissions & Reviews: {targetGroupForSubmissions.group_name}
                </h3>
              </div>
              <button
                onClick={() => setIsSubmissionsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {submissionError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <p>{submissionError}</p>
              </div>
            )}

            {reviewError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <p>{reviewError}</p>
              </div>
            )}

            {/* Submission History */}
            <div className="space-y-3">
              <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider">
                Submission History ({groupSubmissions?.length || 0})
              </h4>

              {isSubmissionsLoading ? (
                <div className="flex items-center justify-center p-6 space-y-2">
                  <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
                  <span className="text-xs text-slate-500 ml-2">Loading submissions...</span>
                </div>
              ) : !groupSubmissions || groupSubmissions.length === 0 ? (
                <p className="p-4 border border-dashed border-slate-200 rounded-lg text-center text-xs text-slate-400 italic">
                  No deliverables submitted yet for this project group.
                </p>
              ) : (
                <div className="space-y-3">
                  {groupSubmissions.map((sub) => (
                    <div
                      key={sub.id}
                      className="border border-slate-200 rounded-lg p-4 bg-slate-50/50 space-y-2.5 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                            Attempt #{sub.attempt_number}
                          </span>
                          <span className="text-slate-500">
                            by {sub.submitted_by_name || 'Group Member'} •{' '}
                            {new Date(sub.submitted_at).toLocaleDateString()}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          {getReadinessBadge(sub.status)}
                          {sub.score !== null && sub.score !== undefined && (
                            <span className="font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                              Score: {sub.score}/100
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-slate-600">
                        {sub.repo_url && (
                          <a
                            href={sub.repo_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-indigo-600 hover:underline"
                          >
                            <FolderGit2 className="w-3.5 h-3.5" />
                            Repository
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                        {sub.live_demo_url && (
                          <a
                            href={sub.live_demo_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-emerald-600 hover:underline"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            Live Demo
                          </a>
                        )}
                        {sub.documentation_url && (
                          <a
                            href={sub.documentation_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-purple-600 hover:underline"
                          >
                            Documentation
                          </a>
                        )}
                      </div>

                      {sub.notes && <p className="text-slate-700 italic">"{sub.notes}"</p>}

                      {sub.feedback && (
                        <div className="p-2.5 bg-white border border-slate-200 rounded text-slate-800">
                          <span className="font-semibold text-slate-900 block mb-0.5">
                            Evaluator Feedback:
                          </span>
                          <p>{sub.feedback}</p>
                        </div>
                      )}

                      {/* Review Action Trigger */}
                      {sub.status !== 'APPROVED' && (
                        <div className="pt-1 flex justify-end">
                          <button
                            id={`btn-open-review-${sub.id}`}
                            onClick={() => {
                              setReviewSubmissionId(reviewSubmissionId === sub.id ? null : sub.id);
                              setReviewFormData({
                                status: 'APPROVED',
                                score: sub.score || 85,
                                feedback: sub.feedback || '',
                              });
                            }}
                            className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
                          >
                            {reviewSubmissionId === sub.id ? 'Close Review Form' : 'Review Submission'}
                          </button>
                        </div>
                      )}

                      {/* Review Form */}
                      {reviewSubmissionId === sub.id && (
                        <div className="mt-3 p-3 bg-white border border-indigo-200 rounded-lg space-y-3">
                          <h5 className="font-bold text-slate-900">
                            Evaluate Submission Attempt #{sub.attempt_number}
                          </h5>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label
                                htmlFor="review-status-select"
                                className="block font-semibold text-slate-700 mb-1"
                              >
                                Decision *
                              </label>
                              <select
                                id="review-status-select"
                                value={reviewFormData.status}
                                onChange={(e) =>
                                  setReviewFormData({
                                    ...reviewFormData,
                                    status: e.target.value as 'APPROVED' | 'CORRECTIONS_REQUESTED',
                                  })
                                }
                                className="w-full border border-slate-300 rounded p-2 text-xs bg-white"
                              >
                                <option value="APPROVED">APPROVED (Pass Milestone/Deliverable)</option>
                                <option value="CORRECTIONS_REQUESTED">
                                  CORRECTIONS_REQUESTED (Request Re-submission)
                                </option>
                              </select>
                            </div>
                            <div>
                              <label
                                htmlFor="review-score-input"
                                className="block font-semibold text-slate-700 mb-1"
                              >
                                Score (0 - 100) *
                              </label>
                              <input
                                id="review-score-input"
                                type="number"
                                min="0"
                                max="100"
                                value={reviewFormData.score}
                                onChange={(e) =>
                                  setReviewFormData({
                                    ...reviewFormData,
                                    score: Number(e.target.value),
                                  })
                                }
                                className="w-full border border-slate-300 rounded p-2 text-xs"
                              />
                            </div>
                          </div>
                          <div>
                            <label
                              htmlFor="review-feedback-input"
                              className="block font-semibold text-slate-700 mb-1"
                            >
                              Qualitative Evaluator Feedback
                            </label>
                            <textarea
                              id="review-feedback-input"
                              rows={2}
                              placeholder="Provide actionable code quality, architectural, or documentation critique..."
                              value={reviewFormData.feedback}
                              onChange={(e) =>
                                setReviewFormData({ ...reviewFormData, feedback: e.target.value })
                              }
                              className="w-full border border-slate-300 rounded p-2 text-xs"
                            />
                          </div>
                          <div className="flex justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => setReviewSubmissionId(null)}
                              className="px-3 py-1.5 border border-slate-300 rounded text-slate-700 font-medium"
                            >
                              Cancel
                            </button>
                            <button
                              id="btn-submit-review"
                              type="button"
                              disabled={reviewSubmissionMutation.isPending}
                              onClick={() => {
                                reviewSubmissionMutation.mutate({
                                  groupId: targetGroupForSubmissions.id,
                                  submissionId: sub.id,
                                  payload: reviewFormData,
                                });
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-white bg-indigo-600 hover:bg-indigo-700 font-semibold disabled:opacity-50"
                            >
                              {reviewSubmissionMutation.isPending && (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              )}
                              Submit Review
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* New Deliverable Submission Form */}
            <div className="pt-4 border-t border-slate-200 space-y-3">
              <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                <Upload className="w-4 h-4 text-indigo-600" />
                Submit New Project Deliverable
              </h4>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!submissionFormData.submitted_by_candidate_id) return;
                  submitDeliverableMutation.mutate({
                    groupId: targetGroupForSubmissions.id,
                    payload: {
                      submitted_by_candidate_id: submissionFormData.submitted_by_candidate_id,
                      repo_url: submissionFormData.repo_url || undefined,
                      live_demo_url: submissionFormData.live_demo_url || undefined,
                      documentation_url: submissionFormData.documentation_url || undefined,
                      notes: submissionFormData.notes || undefined,
                    },
                  });
                }}
                className="space-y-3 text-xs"
              >
                <div>
                  <label
                    htmlFor="submission-candidate-select"
                    className="block font-semibold text-slate-700 mb-1"
                  >
                    Submitting Candidate *
                  </label>
                  <select
                    id="submission-candidate-select"
                    required
                    value={submissionFormData.submitted_by_candidate_id}
                    onChange={(e) =>
                      setSubmissionFormData({
                        ...submissionFormData,
                        submitted_by_candidate_id: e.target.value,
                      })
                    }
                    className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-xs"
                  >
                    <option value="">Select candidate submitting deliverable...</option>
                    {candidateList?.items?.map((c: CandidateItem) => (
                      <option key={c.id} value={c.id}>
                        {c.first_name} {c.last_name} ({c.candidate_number})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="submission-repo-url" className="block font-semibold text-slate-700 mb-1">
                      Git Repository URL
                    </label>
                    <input
                      id="submission-repo-url"
                      type="url"
                      placeholder="https://github.com/org/repo"
                      value={submissionFormData.repo_url}
                      onChange={(e) =>
                        setSubmissionFormData({ ...submissionFormData, repo_url: e.target.value })
                      }
                      className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                    />
                  </div>
                  <div>
                    <label htmlFor="submission-demo-url" className="block font-semibold text-slate-700 mb-1">
                      Live Demo URL
                    </label>
                    <input
                      id="submission-demo-url"
                      type="url"
                      placeholder="https://project.example.com"
                      value={submissionFormData.live_demo_url}
                      onChange={(e) =>
                        setSubmissionFormData({
                          ...submissionFormData,
                          live_demo_url: e.target.value,
                        })
                      }
                      className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="submission-notes" className="block font-semibold text-slate-700 mb-1">
                    Submission Notes
                  </label>
                  <textarea
                    id="submission-notes"
                    rows={2}
                    placeholder="Provide release notes, testing credentials, or milestone summary..."
                    value={submissionFormData.notes}
                    onChange={(e) =>
                      setSubmissionFormData({ ...submissionFormData, notes: e.target.value })
                    }
                    className="w-full border border-slate-300 rounded-lg p-2 text-xs"
                  />
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    id="btn-submit-deliverable"
                    type="submit"
                    disabled={
                      submitDeliverableMutation.isPending ||
                      !submissionFormData.submitted_by_candidate_id
                    }
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50"
                  >
                    {submitDeliverableMutation.isPending && (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    )}
                    Submit Deliverable
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Form Group Modal */}
      {isFormModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-slate-900">
                <Users className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold">Form Dynamic Project Group</h3>
              </div>
              <button
                onClick={() => setIsFormModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2.5 text-xs text-rose-700">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Team Sizing Constraint Error:</span>
                  <p className="mt-0.5">{formError}</p>
                </div>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                setFormError(null);
                if (formData.selected_candidate_ids.length > formData.max_size) {
                  setFormError(
                    `Cannot assign more than ${formData.max_size} candidates (Selected: ${formData.selected_candidate_ids.length}).`
                  );
                  return;
                }
                formGroupMutation.mutate({
                  batch_id: formData.batch_id,
                  group_name: formData.group_name.trim(),
                  project_id: formData.project_id || undefined,
                  min_size: formData.min_size,
                  target_size: formData.target_size,
                  max_size: formData.max_size,
                  candidate_ids:
                    formData.selected_candidate_ids.length > 0
                      ? formData.selected_candidate_ids
                      : undefined,
                });
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label htmlFor="form-group-batch" className="block font-semibold text-slate-700 mb-1">
                  Cohort Batch *
                </label>
                <select
                  id="form-group-batch"
                  required
                  value={formData.batch_id}
                  onChange={(e) =>
                    setFormData({ ...formData, batch_id: e.target.value, selected_candidate_ids: [] })
                  }
                  className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-xs"
                >
                  <option value="">Select batch...</option>
                  {batches?.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.batch_code} - {b.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="form-group-name" className="block font-semibold text-slate-700 mb-1">
                  Group Name *
                </label>
                <input
                  id="form-group-name"
                  type="text"
                  required
                  placeholder="e.g. Analytics Falcon Alpha"
                  value={formData.group_name}
                  onChange={(e) => setFormData({ ...formData, group_name: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2.5 text-xs"
                />
              </div>

              <div>
                <label htmlFor="form-group-project" className="block font-semibold text-slate-700 mb-1">
                  Project Specification (Optional Initial Assignment)
                </label>
                <select
                  id="form-group-project"
                  value={formData.project_id}
                  onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-xs"
                >
                  <option value="">Assign project later...</option>
                  {projectsData?.items?.map((p: ProjectListItem) => (
                    <option key={p.id} value={p.id}>
                      {p.code} - {p.title} ({p.tier})
                    </option>
                  ))}
                </select>
              </div>

              {/* Dynamic Sizing Constraints (BR-GRP-01) */}
              <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <div>
                  <label htmlFor="form-group-min-size" className="block font-semibold text-slate-700 mb-1">
                    Min Members
                  </label>
                  <input
                    id="form-group-min-size"
                    type="number"
                    min="1"
                    max="10"
                    value={formData.min_size}
                    onChange={(e) => setFormData({ ...formData, min_size: Number(e.target.value) })}
                    className="w-full border border-slate-300 rounded p-1.5 font-mono text-center"
                  />
                </div>
                <div>
                  <label htmlFor="form-group-target-size" className="block font-semibold text-slate-700 mb-1">
                    Target Members
                  </label>
                  <input
                    id="form-group-target-size"
                    type="number"
                    min="2"
                    max="10"
                    value={formData.target_size}
                    onChange={(e) => setFormData({ ...formData, target_size: Number(e.target.value) })}
                    className="w-full border border-slate-300 rounded p-1.5 font-mono text-center"
                  />
                </div>
                <div>
                  <label htmlFor="form-group-max-size" className="block font-semibold text-slate-700 mb-1">
                    Max Members
                  </label>
                  <input
                    id="form-group-max-size"
                    type="number"
                    min="2"
                    max="10"
                    value={formData.max_size}
                    onChange={(e) => setFormData({ ...formData, max_size: Number(e.target.value) })}
                    className="w-full border border-slate-300 rounded p-1.5 font-mono text-center"
                  />
                </div>
              </div>

              {/* Multi-Candidate Picker */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="block font-semibold text-slate-700">
                    Assign Candidates from Batch (Optional at formation)
                  </label>
                  <span
                    className={`font-mono text-[11px] font-semibold px-2 py-0.5 rounded ${
                      formData.selected_candidate_ids.length > formData.max_size
                        ? 'bg-rose-100 text-rose-700'
                        : 'bg-indigo-50 text-indigo-700'
                    }`}
                  >
                    Selected: {formData.selected_candidate_ids.length} / {formData.max_size} Max
                  </span>
                </div>

                {!formData.batch_id ? (
                  <p className="text-slate-400 italic text-[11px]">
                    Select a cohort batch first to view candidates.
                  </p>
                ) : !candidateList?.items || candidateList.items.length === 0 ? (
                  <p className="text-slate-400 italic text-[11px]">No active candidates in this cohort.</p>
                ) : (
                  <div className="max-h-40 overflow-y-auto border border-slate-200 rounded-lg p-2 space-y-1.5 bg-slate-50/50">
                    {candidateList.items.map((cand: CandidateItem) => {
                      const isSelected = formData.selected_candidate_ids.includes(cand.id);
                      return (
                        <label
                          key={cand.id}
                          className={`flex items-center gap-2 p-1.5 rounded text-xs cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-indigo-50 text-indigo-900 font-medium'
                              : 'hover:bg-slate-100 text-slate-700'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setFormData({
                                  ...formData,
                                  selected_candidate_ids: [
                                    ...formData.selected_candidate_ids,
                                    cand.id,
                                  ],
                                });
                              } else {
                                setFormData({
                                  ...formData,
                                  selected_candidate_ids: formData.selected_candidate_ids.filter(
                                    (id) => id !== cand.id
                                  ),
                                });
                              }
                            }}
                            className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                          />
                          <span className="truncate">
                            {cand.first_name} {cand.last_name} ({cand.candidate_number})
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsFormModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-form-group"
                  type="submit"
                  disabled={formGroupMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50"
                >
                  {formGroupMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Form Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {isAddMemberModalOpen && targetGroupForMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-slate-900">
                <Users className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold">Add Member to {targetGroupForMember.group_name}</h3>
              </div>
              <button
                onClick={() => setIsAddMemberModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {addMemberError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <p>{addMemberError}</p>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!selectedCandidateToAdd) return;
                addMemberMutation.mutate({
                  groupId: targetGroupForMember.id,
                  candidateId: selectedCandidateToAdd,
                  role: addMemberRole,
                });
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label htmlFor="add-member-candidate-select" className="block font-semibold text-slate-700 mb-1">
                  Select Cohort Candidate *
                </label>
                <select
                  id="add-member-candidate-select"
                  required
                  value={selectedCandidateToAdd}
                  onChange={(e) => setSelectedCandidateToAdd(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-xs"
                >
                  <option value="">Select candidate from cohort...</option>
                  {candidateList?.items?.map((cand: CandidateItem) => (
                    <option key={cand.id} value={cand.id}>
                      {cand.first_name} {cand.last_name} ({cand.candidate_number}) - {cand.email}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="add-member-role-select" className="block font-semibold text-slate-700 mb-1">
                  Initial Member Role
                </label>
                <select
                  id="add-member-role-select"
                  value={addMemberRole}
                  onChange={(e) => setAddMemberRole(e.target.value as 'MEMBER' | 'LEADER')}
                  className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-xs"
                >
                  <option value="MEMBER">Team Member</option>
                  <option value="LEADER">Team Leader</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsAddMemberModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  id="btn-confirm-add-member"
                  type="submit"
                  disabled={addMemberMutation.isPending || !selectedCandidateToAdd}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50"
                >
                  {addMemberMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Add Member
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
