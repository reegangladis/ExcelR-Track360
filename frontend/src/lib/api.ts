import {
  SystemHealth,
  SystemReadiness,
  UserProfile,
  LoginResponse,
  PasswordResetResponse,
  CandidateItem,
  CandidatePaginated,
  BatchItem,
  ImportPreviewResult,
  ImportRowItem,
  AssignmentItem,
  AssignmentPaginated,
  AllocationItem,
  AllocationPaginated,
  TrackItem,
  AssignmentSubmissionPaginated,
  AssignmentSubmissionDetail,
  SubmissionAttemptItem,
  SubmissionReviewItem,
  ProjectItem,
  ProjectPaginated,
  ProjectMilestoneItem,
  ProjectGroupItem,
  ProjectGroupPaginated,
  ProjectAllocationRequest,
  ProjectGroupSubmissionCreate,
  ProjectGroupSubmissionReviewRequest,
  ProjectGroupSubmissionItem,
  ProjectProgressionRequestCreate,
  GroupReadinessResponse,
  GroupAdvanceRequest,
  InternshipRecordItem,
  InternshipPaginatedResponse,
  InternshipCreateRequest,
  InternshipUpdateRequest,
  InternshipCompleteRequest,
  InternshipTerminateRequest,
  CandidateInternshipEligibilityResponse,
  CertificateItem,
  CertificateListResponse,
  CertificateEligibilityDiagnostic,
  CertificateIssueRequest,
  CertificateReviewRequest,
  CertificateApprovalRequest,
  CertificateRevokeRequest,
  CertificatePublicVerifyResponse,
  NotificationEventItem,
  NotificationListResponse,
  NotificationUnreadCountResponse,
  NotificationDispatchCreate,
  EmailQueueListResponse,
  EmailRetryRequest,
  AuditLogListResponse,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
  return match ? decodeURIComponent(match[3]) : null;
}

let memoryCsrfToken: string | null = null;

export function setMemoryCsrfToken(token: string | null): void {
  memoryCsrfToken = token;
}

export function getCsrfToken(): string | null {
  return memoryCsrfToken || getCookie('track360_csrf');
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const method = (options?.method || 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'X-Requested-With': 'XMLHttpRequest',
    ...((options?.headers as Record<string, string>) || {}),
  };

  if (!(options?.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  // Automatically attach CSRF token on state-changing methods
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers['X-CSRF-Token'] = csrf;
    }
  }

  const response = await fetch(url, {
    credentials: 'include',
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: any;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }
    throw new ApiError(
      errorData?.detail || `API request failed with status ${response.status}`,
      response.status,
      errorData
    );
  }

  return response.json() as Promise<T>;
}

export const api = {
  // System Probes
  getHealth: async (): Promise<SystemHealth> => {
    return request<SystemHealth>('/health');
  },
  getReadiness: async (): Promise<SystemReadiness> => {
    return request<SystemReadiness>('/ready');
  },

  // Authentication & Session Endpoints
  login: async (credentials: { email: string; password: string }): Promise<LoginResponse> => {
    const res = await request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    if (res.csrf_token) {
      setMemoryCsrfToken(res.csrf_token);
    }
    return res;
  },
  logout: async (): Promise<{ message: string }> => {
    const res = await request<{ message: string }>('/auth/logout', {
      method: 'POST',
    });
    setMemoryCsrfToken(null);
    return res;
  },
  getMe: async (): Promise<UserProfile> => {
    return request<UserProfile>('/auth/me');
  },
  requestPasswordReset: async (email: string): Promise<PasswordResetResponse> => {
    return request<PasswordResetResponse>('/auth/password-reset/request', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },
  confirmPasswordReset: async (payload: { token: string; new_password: string }): Promise<{ message: string }> => {
    return request<{ message: string }>('/auth/password-reset/confirm', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Candidate Management Endpoints
  getCandidates: async (params?: {
    search?: string;
    lifecycle_status?: string;
    batch_id?: string;
    project_eligible?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<CandidatePaginated> => {
    const query = new URLSearchParams();
    if (params?.search) query.append('search', params.search);
    if (params?.lifecycle_status) query.append('lifecycle_status', params.lifecycle_status);
    if (params?.batch_id) query.append('batch_id', params.batch_id);
    if (params?.project_eligible !== undefined) query.append('project_eligible', String(params.project_eligible));
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<CandidatePaginated>(`/candidates${qs ? `?${qs}` : ''}`);
  },
  getCandidate: async (id: string): Promise<CandidateItem> => {
    return request<CandidateItem>(`/candidates/${id}`);
  },
  createCandidate: async (data: {
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    alternate_phone?: string;
    academic_qualification?: string;
    batch_id?: string;
  }): Promise<CandidateItem> => {
    return request<CandidateItem>('/candidates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  updateCandidate: async (id: string, data: Partial<CandidateItem>): Promise<CandidateItem> => {
    return request<CandidateItem>(`/candidates/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  transitionCandidateStatus: async (
    id: string,
    to_status: string,
    reason: string
  ): Promise<CandidateItem> => {
    return request<CandidateItem>(`/candidates/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ to_status, reason }),
    });
  },
  getBatches: async (): Promise<BatchItem[]> => {
    return request<BatchItem[]>('/batches');
  },
  previewCandidateImport: async (file: File): Promise<ImportPreviewResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const csrf = getCsrfToken();
    const headers: Record<string, string> = {
      'X-Requested-With': 'XMLHttpRequest',
    };
    if (csrf) {
      headers['X-CSRF-Token'] = csrf;
    }

    const response = await fetch(`${API_BASE_URL}/candidates/import/preview`, {
      method: 'POST',
      credentials: 'include',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Failed to preview CSV' }));
      throw new ApiError(err.detail || 'Upload failed', response.status, err);
    }
    return response.json();
  },
  commitCandidateImport: async (
    rows: ImportRowItem[],
    default_batch_id?: string
  ): Promise<{ inserted_count: number; skipped_count: number; message: string }> => {
    return request<{ inserted_count: number; skipped_count: number; message: string }>(
      '/candidates/import/commit',
      {
        method: 'POST',
        body: JSON.stringify({ rows, default_batch_id }),
      }
    );
  },

  // Assignment Management Endpoints
  getTracks: async (course_id?: string): Promise<TrackItem[]> => {
    const qs = course_id ? `?course_id=${course_id}` : '';
    return request<TrackItem[]>(`/courses/tracks${qs}`);
  },
  getAssignments: async (params?: {
    track_id?: string;
    search?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<AssignmentPaginated> => {
    const query = new URLSearchParams();
    if (params?.track_id) query.append('track_id', params.track_id);
    if (params?.search) query.append('search', params.search);
    if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<AssignmentPaginated>(`/assignments${qs ? `?${qs}` : ''}`);
  },
  getAssignment: async (id: string): Promise<AssignmentItem> => {
    return request<AssignmentItem>(`/assignments/${id}`);
  },
  createAssignment: async (data: {
    track_id: string;
    code: string;
    title: string;
    instructions_markdown: string;
    sequence_order?: number;
    is_mandatory?: boolean;
    max_score?: number;
    passing_score?: number;
    rubric_template?: Array<{ key: string; title: string; max_points: number; description?: string }>;
    allowed_file_types?: string[];
    max_file_size_mb?: number;
  }): Promise<AssignmentItem> => {
    return request<AssignmentItem>('/assignments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  updateAssignment: async (id: string, data: Partial<AssignmentItem>): Promise<AssignmentItem> => {
    return request<AssignmentItem>(`/assignments/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  getAllocations: async (params?: {
    assignment_id?: string;
    batch_id?: string;
    candidate_id?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<AllocationPaginated> => {
    const query = new URLSearchParams();
    if (params?.assignment_id) query.append('assignment_id', params.assignment_id);
    if (params?.batch_id) query.append('batch_id', params.batch_id);
    if (params?.candidate_id) query.append('candidate_id', params.candidate_id);
    if (params?.status) query.append('status', params.status);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<AllocationPaginated>(`/assignments/allocations${qs ? `?${qs}` : ''}`);
  },
  createAllocation: async (data: {
    assignment_id: string;
    batch_id?: string;
    candidate_id?: string;
    due_date_utc: string;
    grace_period_end_utc?: string;
  }): Promise<AllocationItem> => {
    return request<AllocationItem>('/assignments/allocations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Submissions & Review Queue (Phase 7)
  getSubmissions: async (params?: {
    status?: string;
    batch_id?: string;
    assignment_id?: string;
    candidate_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<AssignmentSubmissionPaginated> => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.batch_id) query.append('batch_id', params.batch_id);
    if (params?.assignment_id) query.append('assignment_id', params.assignment_id);
    if (params?.candidate_id) query.append('candidate_id', params.candidate_id);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<AssignmentSubmissionPaginated>(`/assignments/submissions${qs ? `?${qs}` : ''}`);
  },
  getSubmissionDetail: async (submissionId: string): Promise<AssignmentSubmissionDetail> => {
    return request<AssignmentSubmissionDetail>(`/assignments/submissions/${submissionId}`);
  },
  submitAssignmentDeliverable: async (
    allocationId: string,
    formData: FormData
  ): Promise<SubmissionAttemptItem> => {
    return request<SubmissionAttemptItem>(`/assignments/allocations/${allocationId}/submit`, {
      method: 'POST',
      body: formData,
    });
  },
  reviewSubmission: async (
    submissionId: string,
    payload: {
      review_outcome: 'APPROVED' | 'CORRECTIONS_REQUESTED' | 'REJECTED';
      qualitative_feedback: string;
      internal_evaluator_notes?: string;
      rubric_scores: Array<{
        criterion_key: string;
        criterion_title: string;
        max_points: number;
        awarded_points: number;
        criterion_comments?: string;
      }>;
    }
  ): Promise<SubmissionReviewItem> => {
    return request<SubmissionReviewItem>(`/assignments/submissions/${submissionId}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Project Management Endpoints (Phase 8)
  getProjects: async (params?: {
    track_id?: string;
    tier?: string;
    complexity?: string;
    is_active?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<ProjectPaginated> => {
    const query = new URLSearchParams();
    if (params?.track_id) query.append('track_id', params.track_id);
    if (params?.tier) query.append('tier', params.tier);
    if (params?.complexity) query.append('complexity', params.complexity);
    if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<ProjectPaginated>(`/projects${qs ? `?${qs}` : ''}`);
  },
  getProject: async (id: string): Promise<ProjectItem> => {
    return request<ProjectItem>(`/projects/${id}`);
  },
  createProject: async (data: {
    track_id: string;
    code: string;
    title: string;
    description?: string;
    tier: string;
    complexity?: string;
    min_team_size?: number;
    max_team_size?: number;
    passing_score?: number;
    deliverable_specs?: Array<{ key: string; title: string; deliverable_type: string; is_required: boolean }>;
    rubric_template?: Array<{ key: string; title: string; max_points: number }>;
    milestones?: Array<{
      sequence_order: number;
      title: string;
      description?: string;
      weight_percentage: number;
      max_score?: number;
      is_mandatory?: boolean;
    }>;
  }): Promise<ProjectItem> => {
    return request<ProjectItem>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  updateProject: async (id: string, data: Partial<ProjectItem>): Promise<ProjectItem> => {
    return request<ProjectItem>(`/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  addProjectMilestone: async (
    projectId: string,
    data: {
      sequence_order: number;
      title: string;
      description?: string;
      weight_percentage: number;
      max_score?: number;
      is_mandatory?: boolean;
    }
  ): Promise<ProjectMilestoneItem> => {
    return request<ProjectMilestoneItem>(`/projects/${projectId}/milestones`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Project Groups & Dynamic Team Sizing (Phase 9)
  getProjectGroups: async (params?: {
    batch_id?: string;
    project_id?: string;
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<ProjectGroupPaginated> => {
    const query = new URLSearchParams();
    if (params?.batch_id) query.append('batch_id', params.batch_id);
    if (params?.project_id) query.append('project_id', params.project_id);
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<ProjectGroupPaginated>(`/projects/groups${qs ? `?${qs}` : ''}`);
  },
  getProjectGroup: async (groupId: string): Promise<ProjectGroupItem> => {
    return request<ProjectGroupItem>(`/projects/groups/${groupId}`);
  },
  createProjectGroup: async (data: {
    batch_id: string;
    group_name: string;
    project_id?: string;
    min_size?: number;
    target_size?: number;
    max_size?: number;
    candidate_ids?: string[];
  }): Promise<ProjectGroupItem> => {
    return request<ProjectGroupItem>('/projects/groups', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  updateProjectGroup: async (
    groupId: string,
    data: {
      group_name?: string;
      project_id?: string | null;
      status?: string;
    }
  ): Promise<ProjectGroupItem> => {
    return request<ProjectGroupItem>(`/projects/groups/${groupId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  addGroupMember: async (
    groupId: string,
    data: {
      candidate_id: string;
      role?: 'LEADER' | 'MEMBER';
    }
  ): Promise<ProjectGroupItem> => {
    return request<ProjectGroupItem>(`/projects/groups/${groupId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  removeGroupMember: async (
    groupId: string,
    candidateId: string,
    override: boolean = false
  ): Promise<ProjectGroupItem> => {
    const qs = override ? '?override=true' : '';
    return request<ProjectGroupItem>(`/projects/groups/${groupId}/members/${candidateId}${qs}`, {
      method: 'DELETE',
    });
  },
  setGroupLeader: async (
    groupId: string,
    candidateId: string
  ): Promise<ProjectGroupItem> => {
    return request<ProjectGroupItem>(`/projects/groups/${groupId}/leader/${candidateId}`, {
      method: 'PATCH',
    });
  },
  assignGroupMentor: async (
    groupId: string,
    mentorId: string
  ): Promise<ProjectGroupItem> => {
    return request<ProjectGroupItem>(`/projects/groups/${groupId}/mentor`, {
      method: 'PUT',
      body: JSON.stringify({ mentor_id: mentorId }),
    });
  },
  allocateProjectToGroup: async (
    groupId: string,
    data: ProjectAllocationRequest
  ): Promise<ProjectGroupItem> => {
    return request<ProjectGroupItem>(`/projects/groups/${groupId}/allocate-project`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  submitGroupDeliverable: async (
    groupId: string,
    data: ProjectGroupSubmissionCreate
  ): Promise<ProjectGroupSubmissionItem> => {
    return request<ProjectGroupSubmissionItem>(`/projects/groups/${groupId}/submissions`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  listGroupSubmissions: async (
    groupId: string
  ): Promise<ProjectGroupSubmissionItem[]> => {
    return request<ProjectGroupSubmissionItem[]>(`/projects/groups/${groupId}/submissions`);
  },
  reviewGroupSubmission: async (
    groupId: string,
    submissionId: string,
    data: ProjectGroupSubmissionReviewRequest
  ): Promise<ProjectGroupSubmissionItem> => {
    return request<ProjectGroupSubmissionItem>(
      `/projects/groups/${groupId}/submissions/${submissionId}/review`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },
  requestGroupProgression: async (
    groupId: string,
    data: ProjectProgressionRequestCreate
  ): Promise<GroupReadinessResponse> => {
    return request<GroupReadinessResponse>(`/projects/groups/${groupId}/progression-request`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  getGroupReadiness: async (
    groupId: string
  ): Promise<GroupReadinessResponse> => {
    return request<GroupReadinessResponse>(`/projects/groups/${groupId}/readiness`);
  },
  advanceGroup: async (
    groupId: string,
    data?: GroupAdvanceRequest
  ): Promise<ProjectGroupItem> => {
    return request<ProjectGroupItem>(`/projects/groups/${groupId}/advance`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    });
  },
  // Phase 11: Internships
  getInternships: async (params?: {
    track_id?: string;
    candidate_id?: string;
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<InternshipPaginatedResponse> => {
    const query = new URLSearchParams();
    if (params?.track_id) query.append('track_id', params.track_id);
    if (params?.candidate_id) query.append('candidate_id', params.candidate_id);
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<InternshipPaginatedResponse>(`/internships${qs ? `?${qs}` : ''}`);
  },
  getInternship: async (id: string): Promise<InternshipRecordItem> => {
    return request<InternshipRecordItem>(`/internships/${id}`);
  },
  getCandidateInternship: async (candidateId: string): Promise<InternshipRecordItem> => {
    return request<InternshipRecordItem>(`/internships/candidates/${candidateId}`);
  },
  checkCandidateInternshipEligibility: async (
    candidateId: string
  ): Promise<CandidateInternshipEligibilityResponse> => {
    return request<CandidateInternshipEligibilityResponse>(
      `/internships/candidates/${candidateId}/eligibility`
    );
  },
  initializeInternship: async (
    data: InternshipCreateRequest
  ): Promise<InternshipRecordItem> => {
    return request<InternshipRecordItem>('/internships', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  updateInternship: async (
    id: string,
    data: InternshipUpdateRequest
  ): Promise<InternshipRecordItem> => {
    return request<InternshipRecordItem>(`/internships/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
  completeInternship: async (
    id: string,
    data: InternshipCompleteRequest
  ): Promise<InternshipRecordItem> => {
    return request<InternshipRecordItem>(`/internships/${id}/complete`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  terminateInternship: async (
    id: string,
    data: InternshipTerminateRequest
  ): Promise<InternshipRecordItem> => {
    return request<InternshipRecordItem>(`/internships/${id}/terminate`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  syncInternshipDuration: async (id: string): Promise<InternshipRecordItem> => {
    return request<InternshipRecordItem>(`/internships/${id}/sync-duration`, {
      method: 'POST',
    });
  },
  // Phase 12: Certificates & Public Verification
  getCertificates: async (params?: {
    track_id?: string;
    candidate_id?: string;
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<CertificateListResponse> => {
    const query = new URLSearchParams();
    if (params?.track_id) query.append('track_id', params.track_id);
    if (params?.candidate_id) query.append('candidate_id', params.candidate_id);
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const qs = query.toString();
    return request<CertificateListResponse>(`/certificates${qs ? `?${qs}` : ''}`);
  },
  getCertificate: async (id: string): Promise<CertificateItem> => {
    return request<CertificateItem>(`/certificates/${id}`);
  },
  getCertificateEligibility: async (
    candidateId: string,
    trackId?: string
  ): Promise<CertificateEligibilityDiagnostic> => {
    const qs = trackId ? `?track_id=${trackId}` : '';
    return request<CertificateEligibilityDiagnostic>(`/certificates/eligibility/${candidateId}${qs}`);
  },
  initiateCertificate: async (
    data: CertificateIssueRequest
  ): Promise<CertificateItem> => {
    return request<CertificateItem>('/certificates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  reviewCertificateStage1: async (
    id: string,
    data: CertificateReviewRequest
  ): Promise<CertificateItem> => {
    return request<CertificateItem>(`/certificates/${id}/review`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  approveCertificateStage2: async (
    id: string,
    data: CertificateApprovalRequest,
    allowOverride: boolean = false
  ): Promise<CertificateItem> => {
    const qs = allowOverride ? '?allow_override=true' : '';
    return request<CertificateItem>(`/certificates/${id}/approve${qs}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  revokeCertificate: async (
    id: string,
    data: CertificateRevokeRequest
  ): Promise<CertificateItem> => {
    return request<CertificateItem>(`/certificates/${id}/revoke`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  verifyCertificatePublic: async (
    identifier: string
  ): Promise<CertificatePublicVerifyResponse> => {
    return request<CertificatePublicVerifyResponse>(
      `/certificates/public-verify/${encodeURIComponent(identifier)}`
    );
  },
  downloadCertificatePdf: async (id: string, filename?: string): Promise<Blob> => {
    const res = await fetch(`${API_BASE_URL}/certificates/${id}/pdf`, {
      method: 'GET',
      credentials: 'include',
    });
    if (!res.ok) {
      throw new ApiError(`Failed to download certificate: ${res.statusText}`, res.status);
    }
    const blob = await res.blob();
    if (typeof window !== 'undefined' && filename) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    }
    return blob;
  },

  // ============================================================================
  // Notifications & Alerts (Phase 13)
  // ============================================================================
  getNotifications: async (params?: {
    unread_only?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<NotificationListResponse> => {
    const query = new URLSearchParams();
    if (params?.unread_only !== undefined) query.append('unread_only', String(params.unread_only));
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    const qs = query.toString();
    return request<NotificationListResponse>(`/notifications${qs ? `?${qs}` : ''}`);
  },
  getUnreadNotificationCount: async (): Promise<NotificationUnreadCountResponse> => {
    return request<NotificationUnreadCountResponse>('/notifications/unread-count');
  },
  markNotificationRead: async (id: string): Promise<NotificationEventItem> => {
    return request<NotificationEventItem>(`/notifications/${id}/read`, {
      method: 'PATCH',
    });
  },
  markAllNotificationsRead: async (): Promise<{ message: string; updated_count: number }> => {
    return request<{ message: string; updated_count: number }>('/notifications/mark-all-read', {
      method: 'POST',
    });
  },
  dispatchNotification: async (
    data: NotificationDispatchCreate
  ): Promise<NotificationEventItem[]> => {
    return request<NotificationEventItem[]>('/notifications/dispatch', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  getEmailQueue: async (params?: {
    delivery_status?: string;
    page?: number;
    page_size?: number;
  }): Promise<EmailQueueListResponse> => {
    const query = new URLSearchParams();
    if (params?.delivery_status) query.append('delivery_status', params.delivery_status);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    const qs = query.toString();
    return request<EmailQueueListResponse>(`/notifications/email-queue${qs ? `?${qs}` : ''}`);
  },
  retryFailedEmails: async (
    data?: EmailRetryRequest
  ): Promise<{ message: string; retried_count: number }> => {
    return request<{ message: string; retried_count: number }>(
      '/notifications/email-queue/retry-failed',
      {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }
    );
  },

  // ============================================================================
  // Audit Trail Explorer (Phase 13)
  // ============================================================================
  getAuditLogs: async (params?: {
    actor_id?: string;
    entity_type?: string;
    action_type?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<AuditLogListResponse> => {
    const query = new URLSearchParams();
    if (params?.actor_id) query.append('actor_id', params.actor_id);
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.action_type) query.append('action_type', params.action_type);
    if (params?.date_from) query.append('date_from', params.date_from);
    if (params?.date_to) query.append('date_to', params.date_to);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));
    const qs = query.toString();
    return request<AuditLogListResponse>(`/audit/logs${qs ? `?${qs}` : ''}`);
  },
  exportAuditLogsCsv: async (
    params?: {
      actor_id?: string;
      entity_type?: string;
      action_type?: string;
      date_from?: string;
      date_to?: string;
    },
    filename: string = 'audit_trail_export.csv'
  ): Promise<Blob> => {
    const query = new URLSearchParams();
    if (params?.actor_id) query.append('actor_id', params.actor_id);
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.action_type) query.append('action_type', params.action_type);
    if (params?.date_from) query.append('date_from', params.date_from);
    if (params?.date_to) query.append('date_to', params.date_to);
    const qs = query.toString();
    const res = await fetch(`${API_BASE_URL}/audit/logs/export${qs ? `?${qs}` : ''}`, {
      method: 'GET',
      credentials: 'include',
    });
    if (!res.ok) {
      throw new ApiError(`Failed to export audit logs: ${res.statusText}`, res.status);
    }
    const blob = await res.blob();
    if (typeof window !== 'undefined' && filename) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    }
    return blob;
  },
};

