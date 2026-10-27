import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api';
import {
  ProjectGroupItem,
  BatchItem,
  ProjectListItem,
  CandidateItem,
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

  // Candidates for add member / form group
  const activeBatchIdForCandidates = targetGroupForMember?.batch_id || selectedBatch;
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

  const renderTeamSizeMeter = (activeCount: number, minSize: number, targetSize: number, maxSize: number) => {
    const percentage = Math.min(100, Math.round((activeCount / maxSize) * 100));
    let barColor = 'bg-amber-500';
    let statusText = `Forming (${activeCount}/${targetSize}) - Need ${minSize - activeCount} more to activate`;

    if (activeCount >= minSize && activeCount <= maxSize) {
      barColor = 'bg-emerald-500';
      statusText = activeCount === targetSize
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
                        <span className="text-xs text-slate-500 truncate max-w-[150px]" title={group.project_title}>
                          • {group.project_title}
                        </span>
                      )}
                    </div>
                  </div>
                  {getStatusBadge(group.status)}
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
              <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between">
                <button
                  id={`btn-manage-group-${group.id}`}
                  onClick={() => setSelectedGroupId(selectedGroupId === group.id ? null : group.id)}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors"
                >
                  {selectedGroupId === group.id ? 'Hide Roster' : 'Manage Team Roster'}
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>

                {group.status !== 'LOCKED' && group.status !== 'DISSOLVED' && group.active_members_count < group.max_size && (
                  <button
                    id={`btn-quick-add-${group.id}`}
                    onClick={() => {
                      setTargetGroupForMember(group as any);
                      setSelectedCandidateToAdd('');
                      setAddMemberError(null);
                      setIsAddMemberModalOpen(true);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
                  >
                    <Plus className="w-3 h-3" />
                    Add Member
                  </button>
                )}
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
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Batch: <span className="font-semibold text-slate-700">{groupDetail.batch_code}</span> | 
                    Active Members: <span className="font-mono font-bold text-slate-800">{groupDetail.active_members_count}</span> (Min: {groupDetail.min_size}, Target: {groupDetail.target_size}, Max: {groupDetail.max_size})
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {groupDetail.status === 'ACTIVE' && (
                    <button
                      id="btn-lock-group"
                      onClick={() => updateStatusMutation.mutate({ groupId: groupDetail.id, status: 'LOCKED' })}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 transition-colors"
                    >
                      <Lock className="w-3.5 h-3.5" />
                      Lock Team Roster
                    </button>
                  )}

                  {groupDetail.status === 'LOCKED' && (
                    <button
                      id="btn-unlock-group"
                      onClick={() => updateStatusMutation.mutate({ groupId: groupDetail.id, status: 'ACTIVE' })}
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
                        if (window.confirm('Are you sure you want to dissolve this project group? Active members will be marked as TRANSFERRED/REMOVED.')) {
                          updateStatusMutation.mutate({ groupId: groupDetail.id, status: 'DISSOLVED' });
                        }
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-colors"
                    >
                      Dissolve Group
                    </button>
                  )}

                  {groupDetail.active_members_count < groupDetail.max_size && groupDetail.status !== 'LOCKED' && groupDetail.status !== 'DISSOLVED' && (
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

                {(!groupDetail.members || groupDetail.members.length === 0) ? (
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
                              {member.member_status === 'ACTIVE' && groupDetail.status !== 'LOCKED' && groupDetail.status !== 'DISSOLVED' && (
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
                  setFormError(`Cannot assign more than ${formData.max_size} candidates (Selected: ${formData.selected_candidate_ids.length}).`);
                  return;
                }
                formGroupMutation.mutate({
                  batch_id: formData.batch_id,
                  group_name: formData.group_name.trim(),
                  project_id: formData.project_id || undefined,
                  min_size: formData.min_size,
                  target_size: formData.target_size,
                  max_size: formData.max_size,
                  candidate_ids: formData.selected_candidate_ids.length > 0 ? formData.selected_candidate_ids : undefined,
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
                  onChange={(e) => setFormData({ ...formData, batch_id: e.target.value, selected_candidate_ids: [] })}
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
                  <p className="text-slate-400 italic text-[11px]">Select a cohort batch first to view candidates.</p>
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
                            isSelected ? 'bg-indigo-50 text-indigo-900 font-medium' : 'hover:bg-slate-100 text-slate-700'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setFormData({
                                  ...formData,
                                  selected_candidate_ids: [...formData.selected_candidate_ids, cand.id],
                                });
                              } else {
                                setFormData({
                                  ...formData,
                                  selected_candidate_ids: formData.selected_candidate_ids.filter((id) => id !== cand.id),
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
