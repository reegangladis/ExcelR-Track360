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

