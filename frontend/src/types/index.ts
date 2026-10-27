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
