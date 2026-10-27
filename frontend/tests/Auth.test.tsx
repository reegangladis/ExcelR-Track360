import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter, MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '../src/lib/auth';
import { LoginPage } from '../src/pages/LoginPage';
import { ProtectedRoute } from '../src/components/ProtectedRoute';
import { api } from '../src/lib/api';

vi.mock('../src/lib/api', () => ({
  api: {
    getMe: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  },
}));

describe('Authentication & Access Control Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login page with email and password inputs and brand heading', () => {
    vi.mocked(api.getMe).mockRejectedValue(new Error('Unauthenticated'));

    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('submits login form and invokes api.login', async () => {
    vi.mocked(api.getMe).mockRejectedValue(new Error('Unauthenticated'));
    vi.mocked(api.login).mockResolvedValue({
      user: {
        id: '123',
        email: 'admin@excelr.com',
        full_name: 'Administrator',
        status: 'ACTIVE',
        is_verified: true,
        roles: ['ROLE_SUPER_ADMIN'],
        permissions: ['system:users_manage'],
      },
      csrf_token: 'csrf-12345',
      message: 'Session established successfully',
    });

    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: 'admin@excelr.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'Admin@Track360_2026!' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith({
        email: 'admin@excelr.com',
        password: 'Admin@Track360_2026!',
      });
    });
  });

  it('shows restricted message when user lacks required role', async () => {
    vi.mocked(api.getMe).mockResolvedValue({
      id: 'student-1',
      email: 'student@excelr.com',
      full_name: 'Bob Student',
      status: 'ACTIVE',
      is_verified: true,
      roles: ['ROLE_STUDENT'],
      permissions: ['assignment:view'],
    });

    render(
      <MemoryRouter initialEntries={['/admin-only']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/admin-only"
              element={
                <ProtectedRoute requiredRole="ROLE_OPS_ADMIN">
                  <div>Secret Ops Dashboard</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Access Restricted')).toBeInTheDocument();
      expect(screen.queryByText('Secret Ops Dashboard')).not.toBeInTheDocument();
    });
  });
});
