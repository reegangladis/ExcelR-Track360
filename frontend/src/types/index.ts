export interface SystemHealth {
  status: 'healthy' | 'unhealthy';
  app_name: string;
  environment: string;
  version: string;
  uptime_seconds: number;
  timestamp: string;
}

export interface SystemReadiness {
  status: 'ready' | 'not_ready';
  environment: string;
  database: {
    status: 'connected' | 'unavailable';
    latency_ms?: number;
    target?: string;
    error?: string;
  };
  dependencies: {
    database: 'healthy' | 'unhealthy';
  };
  detail?: string;
  timestamp: string;
}

export interface ApiProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  code: string;
  timestamp: string;
  invalid_params?: Array<{
    name: string;
    reason: string;
    type?: string;
  }>;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  status: string;
  is_verified: boolean;
  last_login_at?: string | null;
  roles: string[];
  permissions: string[];
}

export interface LoginResponse {
  user: UserProfile;
  csrf_token: string;
  message: string;
}

export interface PasswordResetResponse {
  message: string;
  reset_token?: string | null;
}

export interface CandidateItem {
  id: string;
  user_id?: string | null;
  candidate_number: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  alternate_phone?: string | null;
  academic_qualification?: string | null;
  lifecycle_status: string;
  project_eligible: boolean;
  completed_projects_count: number;
  created_at: string;
  updated_at: string;
  batch_code?: string | null;
}

export interface CandidatePaginated {
  items: CandidateItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TrackItem {
  id: string;
  course_id: string;
  code: string;
  title: string;
  total_mandatory_assignments: number;
  total_required_projects: number;
  is_active: boolean;
}

export interface BatchItem {
  id: string;
  track_id: string;
  batch_code: string;
  title: string;
  start_date: string;
  expected_end_date?: string | null;
  status: string;
}

export interface ImportRowItem {
  row_number: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  batch_code?: string | null;
  academic_qualification?: string | null;
  is_valid: boolean;
  error_field?: string | null;
  error_message?: string | null;
}

export interface ImportPreviewResult {
  total_rows: number;
  valid_rows_count: number;
  error_rows_count: number;
  rows: ImportRowItem[];
}

export interface RubricCriterionItem {
  key: string;
  title: string;
  max_points: number;
  description?: string;
}

export interface AssignmentItem {
  id: string;
  track_id: string;
  code: string;
  title: string;
  instructions_markdown: string;
  sequence_order: number;
  is_mandatory: boolean;
  max_score: number;
  passing_score: number;
  rubric_template: RubricCriterionItem[];
  allowed_file_types: string[];
  max_file_size_mb: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  track_name?: string | null;
}

export interface AssignmentPaginated {
  items: AssignmentItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AllocationItem {
  id: string;
  assignment_id: string;
  assignment_code: string;
  assignment_title: string;
  batch_id?: string | null;
  batch_code?: string | null;
  candidate_id?: string | null;
  candidate_name?: string | null;
  due_date_utc: string;
  grace_period_end_utc?: string | null;
  allocation_status: string;
  created_at: string;
}

export interface AllocationPaginated {
  items: AllocationItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FileAssetItem {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  created_at: string;
}

export interface RubricScoreItem {
  criterion_key: string;
  criterion_title: string;
  max_points: number;
  awarded_points: number;
  criterion_comments?: string | null;
}

export interface SubmissionReviewItem {
  id: string;
  attempt_id: string;
  reviewer_id: string;
  review_outcome: 'APPROVED' | 'CORRECTIONS_REQUESTED' | 'REJECTED';
  total_score: number;
  qualitative_feedback: string;
  internal_evaluator_notes?: string | null;
  review_completed_at_utc: string;
  reviewer_name?: string | null;
  rubric_scores: RubricScoreItem[];
}

export interface SubmissionAttemptItem {
  id: string;
  attempt_number: number;
  file_asset?: FileAssetItem | null;
  repository_url?: string | null;
  student_notes?: string | null;
  submitted_at_utc: string;
  is_late: boolean;
  lateness_minutes: number;
  created_at: string;
  reviews?: SubmissionReviewItem[];
}

export interface AssignmentSubmissionListItem {
  id: string;
  allocation_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_number: string;
  assignment_code: string;
  assignment_title: string;
  batch_code?: string | null;
  current_submission_status: string;
  current_completion_status: string;
  total_attempts: number;
  latest_score?: number | null;
  due_date_utc: string;
  latest_submitted_at_utc?: string | null;
  is_late: boolean;
}

export interface AssignmentSubmissionPaginated {
  items: AssignmentSubmissionListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AssignmentSubmissionDetail {
  id: string;
  allocation_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_number: string;
  candidate_email: string;
  assignment_id: string;
  assignment_code: string;
  assignment_title: string;
  assignment_rubric: RubricCriterionItem[];
  passing_score: number;
  max_score: number;
  current_submission_status: string;
  current_completion_status: string;
  total_attempts: number;
  latest_score?: number | null;
  first_submitted_at_utc?: string | null;
  latest_submitted_at_utc?: string | null;
  due_date_utc: string;
  grace_period_end_utc?: string | null;
  attempts: SubmissionAttemptItem[];
}

export interface DeliverableSpecItem {
  key: string;
  title: string;
  deliverable_type: 'GIT_REPO' | 'FILE_UPLOAD' | 'DEMO_URL' | 'DOCUMENTATION';
  is_required: boolean;
  description?: string;
}

export interface ProjectMilestoneItem {
  id: string;
  project_id: string;
  sequence_order: number;
  title: string;
  description?: string | null;
  weight_percentage: number;
  max_score: number;
  is_mandatory: boolean;
  required_deliverables: Array<Record<string, any>>;
  created_at: string;
  updated_at: string;
}

export interface ProjectListItem {
  id: string;
  track_id: string;
  track_title?: string | null;
  code: string;
  title: string;
  tier: 'TIER_1_FOUNDATIONAL' | 'TIER_2_INTERMEDIATE' | 'TIER_3_CAPSTONE';
  complexity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  min_team_size: number;
  max_team_size: number;
  passing_score: number;
  milestone_count: number;
  is_active: boolean;
  created_at: string;
}

export interface ProjectItem {
  id: string;
  track_id: string;
  track_title?: string | null;
  code: string;
  title: string;
  description?: string | null;
  tier: 'TIER_1_FOUNDATIONAL' | 'TIER_2_INTERMEDIATE' | 'TIER_3_CAPSTONE';
  complexity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  min_team_size: number;
  max_team_size: number;
  passing_score: number;
  deliverable_specs: DeliverableSpecItem[];
  rubric_template: RubricCriterionItem[];
  is_active: boolean;
  milestones: ProjectMilestoneItem[];
  created_at: string;
  updated_at: string;
}

export interface ProjectPaginated {
  items: ProjectListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProjectGroupMemberItem {
  id: string;
  group_id: string;
  candidate_id: string;
  candidate_name?: string | null;
  candidate_number?: string | null;
  candidate_email?: string | null;
  role: 'LEADER' | 'MEMBER';
  member_status: 'ACTIVE' | 'REMOVED' | 'TRANSFERRED';
  joined_at: string;
}

export interface ProjectGroupListItem {
  id: string;
  batch_id: string;
  batch_code?: string | null;
  project_id?: string | null;
  project_code?: string | null;
  project_title?: string | null;
  group_name: string;
  min_size: number;
  target_size: number;
  max_size: number;
  active_members_count: number;
  status: 'FORMING' | 'ACTIVE' | 'LOCKED' | 'COMPLETED' | 'DISSOLVED';
  mentor_id?: string | null;
  mentor_name?: string | null;
  current_milestone_id?: string | null;
  current_milestone_title?: string | null;
  readiness_status?: 'NOT_READY' | 'AWAITING_SUBMISSION' | 'SUBMITTED' | 'UNDER_REVIEW' | 'CORRECTIONS_REQUESTED' | 'APPROVED' | 'BLOCKED_PENDING_MEMBERS' | 'READY_FOR_NEXT_PROJECT' | 'COMPLETED' | string;
  allocated_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface ProjectGroupItem extends ProjectGroupListItem {
  members: ProjectGroupMemberItem[];
  updated_at: string;
}

export interface ProjectGroupPaginated {
  items: ProjectGroupListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProjectAllocationRequest {
  project_id: string;
  waive_prerequisites?: boolean;
  waiver_justification?: string;
}

export interface ProjectGroupSubmissionCreate {
  submitted_by_candidate_id: string;
  repo_url?: string;
  live_demo_url?: string;
  documentation_url?: string;
  file_asset_id?: string;
  notes?: string;
  milestone_id?: string;
}

export interface ProjectGroupSubmissionReviewRequest {
  status: 'APPROVED' | 'CORRECTIONS_REQUESTED';
  score?: number;
  feedback?: string;
  rubric_scores?: Array<{
    criterion: string;
    score: number;
    max_score: number;
    comment?: string;
  }>;
}

export interface ProjectGroupSubmissionItem {
  id: string;
  group_id: string;
  project_id: string;
  project_title?: string | null;
  milestone_id?: string | null;
  milestone_title?: string | null;
  submitted_by_id: string;
  submitted_by_name?: string | null;
  attempt_number: number;
  repo_url?: string | null;
  live_demo_url?: string | null;
  documentation_url?: string | null;
  file_asset_id?: string | null;
  notes?: string | null;
  status: 'SUBMITTED' | 'UNDER_REVIEW' | 'APPROVED' | 'CORRECTIONS_REQUESTED';
  score?: number | null;
  rubric_scores: Array<{ criterion: string; score: number; max_score: number; comment?: string }>;
  feedback?: string | null;
  reviewed_by_id?: string | null;
  reviewed_by_name?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
}

export interface ProjectProgressionRequestCreate {
  candidate_id: string;
  notes?: string;
}

export interface ProjectProgressionRequestItem {
  id: string;
  candidate_id: string;
  candidate_name?: string | null;
  candidate_number?: string | null;
  status: string;
  requested_at: string;
  notes?: string | null;
}

export interface GroupReadinessResponse {
  group_id: string;
  group_name: string;
  group_status: string;
  readiness_status: string;
  current_project_id?: string | null;
  current_project_title?: string | null;
  current_tier?: string | null;
  current_milestone_id?: string | null;
  current_milestone_title?: string | null;
  deliverable_approved: boolean;
  active_members_count: number;
  requests_count: number;
  ready_candidate_ids: string[];
  pending_candidate_ids: string[];
  pending_candidate_names: string[];
  can_advance: boolean;
  latest_submission_status?: string | null;
  latest_submission_score?: number | null;
  progression_requests: ProjectProgressionRequestItem[];
}

export interface GroupAdvanceRequest {
  next_project_id?: string;
  override_justification?: string;
  allow_cap_extension?: boolean;
}

export interface InternshipMilestoneItem {
  id: string;
  milestone_tier: number;
  title: string;
  project_id?: string | null;
  project_code?: string | null;
  project_title?: string | null;
  accredited_months: number;
  status: 'PENDING' | 'IN_PROGRESS' | 'ACHIEVED' | 'WAIVED' | string;
  achieved_at?: string | null;
  verified_by_id?: string | null;
  verified_by_name?: string | null;
  notes?: string | null;
}

export interface InternshipRecordItem {
  id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_number?: string | null;
  candidate_email?: string | null;
  track_id: string;
  track_code: string;
  track_title: string;
  start_date: string;
  expected_end_date?: string | null;
  actual_completion_date?: string | null;
  accredited_duration_months: number;
  internship_status: 'ACTIVE' | 'COMPLETED' | 'TERMINATED' | 'ELIGIBLE' | string;
  company_name?: string | null;
  coordinator_notes?: string | null;
  created_at: string;
  updated_at: string;
  milestones: InternshipMilestoneItem[];
}

export interface InternshipListItem {
  id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_number?: string | null;
  track_code: string;
  start_date: string;
  expected_end_date?: string | null;
  actual_completion_date?: string | null;
  accredited_duration_months: number;
  internship_status: string;
  company_name?: string | null;
}

export interface InternshipPaginatedResponse {
  items: InternshipListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface InternshipCreateRequest {
  candidate_id: string;
  track_id: string;
  start_date: string;
  expected_end_date?: string;
  company_name?: string;
  coordinator_notes?: string;
  initial_status?: string;
}

export interface InternshipUpdateRequest {
  start_date?: string;
  expected_end_date?: string;
  actual_completion_date?: string;
  company_name?: string;
  coordinator_notes?: string;
  internship_status?: string;
}

export interface InternshipCompleteRequest {
  actual_completion_date?: string;
  completion_notes?: string;
}

export interface InternshipTerminateRequest {
  reason: string;
}

export interface CandidateInternshipEligibilityResponse {
  candidate_id: string;
  candidate_name: string;
  track_id: string;
  track_title: string;
  is_eligible: boolean;
  approved_projects_count: number;
  recommended_duration_months: number;
  active_group_count: number;
  eligibility_reasons: string[];
  existing_internship_id?: string | null;
}

// ============================================================================
// Phase 12: Certificate Management & Verification Types
// ============================================================================

export type CertificateStatus = 'PENDING_APPROVAL' | 'REVIEWED' | 'APPROVED' | 'ISSUED' | 'REJECTED' | 'REVOKED';

export interface CertificateApprovalItem {
  id: string;
  certificate_id: string;
  approver_id: string;
  approver_name?: string | null;
  approver_email?: string | null;
  stage: string;
  decision: string;
  decision_notes?: string | null;
  decided_at_utc: string;
}

export interface CertificateRevocationItem {
  id: string;
  certificate_id: string;
  revoked_by_id: string;
  revoker_name?: string | null;
  revoker_email?: string | null;
  reason_category: string;
  detailed_reason: string;
  revoked_at_utc: string;
}

export interface CertificateItem {
  id: string;
  candidate_id: string;
  candidate_display_name: string;
  track_id: string;
  course_display_title: string;
  internship_record_id?: string | null;
  serial_number: string;
  certificate_type: string;
  milestone_level?: number | null;
  accredited_duration_months: number;
  issue_date: string;
  verification_hash: string;
  verification_qr_url: string;
  status: CertificateStatus;
  pdf_file_asset_id?: string | null;
  requested_by_id: string;
  requested_at: string;
  stage1_reviewer_id?: string | null;
  stage1_reviewed_at?: string | null;
  stage1_notes?: string | null;
  stage2_approver_id?: string | null;
  stage2_approved_at?: string | null;
  stage2_notes?: string | null;
  issued_at_utc?: string | null;
  revoked_by_id?: string | null;
  revoked_at?: string | null;
  revocation_category?: string | null;
  revocation_reason?: string | null;
  created_at: string;
  updated_at: string;
  approvals: CertificateApprovalItem[];
  revocations: CertificateRevocationItem[];
}

export interface CertificateEligibilityDiagnostic {
  candidate_id: string;
  candidate_name: string;
  track_id: string;
  track_title: string;
  total_mandatory_assignments: number;
  passed_mandatory_assignments: number;
  assignments_completed: boolean;
  total_required_projects: number;
  approved_project_milestones: number;
  projects_completed: boolean;
  has_internship: boolean;
  internship_status?: string | null;
  internship_completed: boolean;
  accredited_duration_months: number;
  is_eligible: boolean;
  ineligibility_reasons: string[];
  has_active_certificate: boolean;
  existing_certificate_id?: string | null;
  existing_certificate_number?: string | null;
}

export interface CertificateIssueRequest {
  candidate_id: string;
  track_id: string;
  internship_record_id?: string | null;
  certificate_type?: string;
  milestone_level?: number | null;
  issue_date?: string;
  notes?: string;
}

export interface CertificateReviewRequest {
  decision: 'APPROVED' | 'REJECTED';
  decision_notes?: string;
}

export interface CertificateApprovalRequest {
  decision: 'APPROVED' | 'REJECTED';
  decision_notes?: string;
}

export interface CertificateRevokeRequest {
  reason_category: 'ACADEMIC_MALPRACTICE' | 'DATA_ENTRY_ERROR' | 'DISCIPLINARY_ACTION' | 'ADMINISTRATIVE_OVERRIDE';
  detailed_reason: string;
}

export interface CertificatePublicVerifyResponse {
  is_valid: boolean;
  status: string;
  serial_number: string;
  candidate_name: string;
  track_title: string;
  accredited_duration_months: number;
  issue_date: string;
  verification_hash: string;
  issued_at_utc?: string | null;
  revoked_at?: string | null;
  revocation_category?: string | null;
  verification_qr_url: string;
}

export interface CertificateListResponse {
  items: CertificateItem[];
  total: number;
  page: number;
  page_size: number;
}

// ============================================================================
// Domain 6: Notifications & Audit Trail (Phase 13)
// ============================================================================
export interface NotificationEventItem {
  id: string;
  recipient_user_id: string;
  event_type: string;
  title: string;
  body: string;
  action_url?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationEventItem[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
}

export interface NotificationUnreadCountResponse {
  unread_count: number;
}

export interface NotificationDispatchCreate {
  recipient_user_ids: string[];
  event_type: string;
  title: string;
  body: string;
  action_url?: string | null;
  queue_email?: boolean;
  email_subject?: string | null;
  email_html?: string | null;
}

export interface EmailQueueItem {
  id: string;
  recipient_email: string;
  subject: string;
  body_html: string;
  delivery_status: 'PENDING' | 'SENT' | 'FAILED' | 'RETRYING';
  attempt_count: number;
  max_attempts: number;
  last_error_message?: string | null;
  next_retry_at_utc?: string | null;
  sent_at_utc?: string | null;
  created_at: string;
}

export interface EmailQueueListResponse {
  items: EmailQueueItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmailRetryRequest {
  queue_ids?: string[];
}

export interface AuditLogItem {
  id: string;
  actor_user_id?: string | null;
  actor_email?: string | null;
  actor_name?: string | null;
  actor_ip_address?: string | null;
  actor_user_agent?: string | null;
  action_type: string;
  entity_type: string;
  entity_id?: string | null;
  pre_state?: Record<string, any> | null;
  post_state?: Record<string, any> | null;
  justification?: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
}



