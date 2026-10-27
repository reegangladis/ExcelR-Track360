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
