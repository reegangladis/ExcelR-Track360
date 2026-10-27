import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { NotificationBell } from '../src/components/NotificationBell';
import { NotificationsPage } from '../src/pages/NotificationsPage';
import { AuditLogsPage } from '../src/pages/AuditLogsPage';
import { api } from '../src/lib/api';
import { EmailQueueListResponse } from '../src/types';

vi.mock('../src/lib/api', () => ({
  api: {
    getUnreadNotificationCount: vi.fn(),
    getNotifications: vi.fn(),
    markNotificationRead: vi.fn(),
    markAllNotificationsRead: vi.fn(),
    dispatchNotification: vi.fn(),
    getEmailQueue: vi.fn(),
    retryFailedEmails: vi.fn(),
    getCandidates: vi.fn(),
    getAuditLogs: vi.fn(),
    exportAuditLogsCsv: vi.fn(),
  },
}));

vi.mock('../src/lib/auth', () => ({
  useAuth: () => ({
    user: {
      id: 'admin-user-uuid',
      email: 'admin@excelr.com',
      full_name: 'Super Admin',
      roles: ['ROLE_SUPER_ADMIN', 'ROLE_OPS_ADMIN'],
      permissions: ['*'],
    },
    isAuthenticated: true,
    hasRole: (role: string) => ['ROLE_SUPER_ADMIN', 'ROLE_OPS_ADMIN'].includes(role),
    hasPermission: () => true,
  }),
}));

const mockNotifications = {
  items: [
    {
      id: 'notif-1',
      recipient_user_id: 'admin-user-uuid',
      event_type: 'ASSIGNMENT_ALLOCATED',
      title: 'New React Assignment Allocated',
      body: 'Assignment #102 has been allocated to candidate Priya Sharma.',
      action_url: '/assignments',
      is_read: false,
      created_at: '2026-10-27T10:00:00Z',
    },
    {
      id: 'notif-2',
      recipient_user_id: 'admin-user-uuid',
      event_type: 'CERTIFICATE_ISSUED',
      title: 'Credential Generated and Verified',
      body: 'Certificate EXCELR-2026-FSD-9C4E2A8F was approved and issued.',
      action_url: '/certificates',
      is_read: true,
      created_at: '2026-10-26T15:30:00Z',
    },
  ],
  total: 2,
  unread_count: 1,
  page: 1,
  page_size: 15,
};

const mockEmailQueue: EmailQueueListResponse = {
  items: [
    {
      id: 'email-1',
      recipient_email: 'priya.sharma@example.com',
      subject: 'Congratulations on your Certificate',
      body_html: '<p>Your certificate has been issued.</p>',
      delivery_status: 'FAILED',
      attempt_count: 3,
      max_attempts: 3,
      last_error_message: 'SMTP connection timeout on port 587',
      next_retry_at_utc: null,
      sent_at_utc: null,
      created_at: '2026-10-27T08:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 15,
};

const mockAuditLogs = {
  items: [
    {
      id: 'audit-log-uuid-1',
      actor_user_id: 'admin-user-uuid',
      actor_email: 'admin@excelr.com',
      actor_name: 'Super Admin',
      actor_ip_address: '192.168.1.10',
      actor_user_agent: 'Mozilla/5.0 Chrome/128.0',
      action_type: 'CERTIFICATE_ISSUED',
      entity_type: 'CERTIFICATE',
      entity_id: 'cert-uuid-999',
      pre_state: { status: 'REVIEWED' },
      post_state: { status: 'ISSUED', serial_number: 'EXCELR-2026-FSD-9C4E2A8F' },
      justification: 'Stage 2 operational approval by ops executive',
      created_at: '2026-10-27T14:30:00Z',
    },
    {
      id: 'audit-log-uuid-2',
      actor_user_id: 'admin-user-uuid',
      actor_email: 'admin@excelr.com',
      actor_name: 'Super Admin',
      actor_ip_address: '192.168.1.10',
      actor_user_agent: 'Mozilla/5.0 Chrome/128.0',
      action_type: 'AUDIT_LOG_EXPORTED',
      entity_type: 'AUDIT_LOGS',
      entity_id: null,
      pre_state: null,
      post_state: { filters: { entity_type: 'CERTIFICATE' } },
      justification: 'Administrative governed CSV export of audit events',
      created_at: '2026-10-27T15:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 25,
};

const mockCandidates = {
  items: [
    {
      id: 'cand-1',
      user_id: 'user-cand-1',
      first_name: 'Priya',
      last_name: 'Sharma',
      email: 'priya@example.com',
    },
  ],
  total: 1,
};

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('Phase 13: Notification Center & Communication Hub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders NotificationBell with unread badge and opens popover feed', async () => {
    vi.mocked(api.getUnreadNotificationCount).mockResolvedValue({ unread_count: 5 });
    vi.mocked(api.getNotifications).mockResolvedValue(mockNotifications);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NotificationBell />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Unread count badge should be visible once query resolves
    expect(await screen.findByText('5')).toBeInTheDocument();

    // Click the bell button to toggle popover
    const bellBtn = screen.getByRole('button', { name: /Notification Center/i });
    fireEvent.click(bellBtn);

    // Notification dropdown header and items should be visible
    expect(await screen.findByText(/New React Assignment Allocated/i)).toBeInTheDocument();
    expect(screen.getByText(/Credential Generated and Verified/i)).toBeInTheDocument();
  });

  it('marks individual notification as read from the bell popover', async () => {
    vi.mocked(api.getUnreadNotificationCount).mockResolvedValue({ unread_count: 1 });
    vi.mocked(api.getNotifications).mockResolvedValue(mockNotifications);
    vi.mocked(api.markNotificationRead).mockResolvedValue({
      ...mockNotifications.items[0],
      is_read: true,
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NotificationBell />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const bellBtn = screen.getByRole('button', { name: /Notification Center/i });
    fireEvent.click(bellBtn);

    await screen.findByText(/New React Assignment Allocated/i);

    const markReadBtn = screen.getByTitle('Mark as read');
    fireEvent.click(markReadBtn);

    await waitFor(() => {
      expect(api.markNotificationRead).toHaveBeenCalledWith('notif-1');
    });
  });

  it('renders NotificationsPage activity feed and switches between tabs', async () => {
    vi.mocked(api.getUnreadNotificationCount).mockResolvedValue({ unread_count: 1 });
    vi.mocked(api.getNotifications).mockResolvedValue(mockNotifications);
    vi.mocked(api.getEmailQueue).mockResolvedValue(mockEmailQueue);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NotificationsPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(
      screen.getByText('Notification Center & Communication Hub')
    ).toBeInTheDocument();

    // Verify activity feed notification title
    expect(await screen.findByText('New React Assignment Allocated')).toBeInTheDocument();

    // Switch to Email Queue tab
    const emailQueueTab = screen.getByRole('button', { name: /Email Dispatch Queue/i });
    fireEvent.click(emailQueueTab);

    // Verify email queue table renders
    expect(await screen.findByText('priya.sharma@example.com')).toBeInTheDocument();
    expect(screen.getByText('SMTP connection timeout on port 587')).toBeInTheDocument();
  });

  it('triggers retryFailedEmails when Retry Failed button is clicked in Email Queue', async () => {
    vi.mocked(api.getUnreadNotificationCount).mockResolvedValue({ unread_count: 0 });
    vi.mocked(api.getNotifications).mockResolvedValue({ items: [], total: 0, unread_count: 0, page: 1, page_size: 15 });
    vi.mocked(api.getEmailQueue).mockResolvedValue(mockEmailQueue);
    vi.mocked(api.retryFailedEmails).mockResolvedValue({
      message: 'Retried failed emails',
      retried_count: 1,
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NotificationsPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Switch to email queue tab
    const emailQueueTab = screen.getByRole('button', { name: /Email Dispatch Queue/i });
    fireEvent.click(emailQueueTab);

    await screen.findByText('priya.sharma@example.com');

    // Click Retry Failed Emails button
    const retryButtons = screen.getAllByRole('button', { name: /Retry Failed/i });
    fireEvent.click(retryButtons[0]);

    await waitFor(() => {
      expect(api.retryFailedEmails).toHaveBeenCalled();
    });
  });

  it('opens broadcast alert modal and dispatches notification successfully', async () => {
    vi.mocked(api.getUnreadNotificationCount).mockResolvedValue({ unread_count: 0 });
    vi.mocked(api.getNotifications).mockResolvedValue({ items: [], total: 0, unread_count: 0, page: 1, page_size: 15 });
    vi.mocked(api.getCandidates).mockResolvedValue(mockCandidates as any);
    vi.mocked(api.dispatchNotification).mockResolvedValue([mockNotifications.items[0]]);

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NotificationsPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Click Broadcast Alert
    const broadcastBtn = screen.getByRole('button', { name: /Broadcast Alert/i });
    fireEvent.click(broadcastBtn);

    // Modal should be open
    expect(await screen.findByText('Broadcast In-App Alert')).toBeInTheDocument();

    // Select candidate checkbox
    const candidateCheckbox = await screen.findByRole('checkbox', { name: /Priya Sharma/i });
    fireEvent.click(candidateCheckbox);

    // Fill Title & Body
    const titleInput = screen.getByPlaceholderText(/Schedule Update/i);
    const bodyInput = screen.getByPlaceholderText(/State the notification message/i);

    fireEvent.change(titleInput, { target: { value: 'Important Exam Schedule' } });
    fireEvent.change(bodyInput, { target: { value: 'Your milestone exam is tomorrow at 10 AM UTC.' } });

    // Submit broadcast
    const submitBtn = screen.getByRole('button', { name: /Send Broadcast/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.dispatchNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          recipient_user_ids: ['user-cand-1'],
          title: 'Important Exam Schedule',
          body: 'Your milestone exam is tomorrow at 10 AM UTC.',
        })
      );
    });
  });
});

describe('Phase 13: Audit Trail Explorer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders AuditLogsPage table with forensic records and compliance badge', async () => {
    vi.mocked(api.getAuditLogs).mockResolvedValue(mockAuditLogs);

    render(
      <BrowserRouter>
        <AuditLogsPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Audit Trail Explorer')).toBeInTheDocument();
    expect(screen.getByText(/Self-Auditing Exports/i)).toBeInTheDocument();

    // Verify row contents
    const certIssuedElements = await screen.findAllByText('CERTIFICATE_ISSUED');
    expect(certIssuedElements[0]).toBeInTheDocument();
    expect(screen.getAllByText('AUDIT_LOG_EXPORTED')[0]).toBeInTheDocument();
    expect(screen.getByText('Stage 2 operational approval by ops executive')).toBeInTheDocument();
    expect(screen.getAllByText('192.168.1.10')[0]).toBeInTheDocument();
  });

  it('filters audit records when domain selector changes', async () => {
    vi.mocked(api.getAuditLogs).mockResolvedValue(mockAuditLogs);

    render(
      <BrowserRouter>
        <AuditLogsPage />
      </BrowserRouter>
    );

    await screen.findByText('Stage 2 operational approval by ops executive');

    const domainSelect = screen.getByLabelText('Entity Domain');
    fireEvent.change(domainSelect, { target: { value: 'CERTIFICATE' } });

    await waitFor(() => {
      expect(api.getAuditLogs).toHaveBeenCalledWith(
        expect.objectContaining({
          entity_type: 'CERTIFICATE',
        })
      );
    });
  });

  it('opens Forensic JSON Inspector modal and displays pre and post states', async () => {
    vi.mocked(api.getAuditLogs).mockResolvedValue(mockAuditLogs);

    render(
      <BrowserRouter>
        <AuditLogsPage />
      </BrowserRouter>
    );

    await screen.findByText('Stage 2 operational approval by ops executive');

    // Click inspect on the first record
    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    // Inspector modal should open
    expect(await screen.findByText('Audit Record Forensic Inspector')).toBeInTheDocument();
    expect(screen.getByText('cert-uuid-999')).toBeInTheDocument();
    expect(screen.getByText(/EXCELR-2026-FSD-9C4E2A8F/i)).toBeInTheDocument();

    // Close modal
    const closeBtn = screen.getByRole('button', { name: /Close Inspector/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText('Audit Record Forensic Inspector')).not.toBeInTheDocument();
    });
  });

  it('triggers exportAuditLogsCsv and displays confirmation banner', async () => {
    vi.mocked(api.getAuditLogs).mockResolvedValue(mockAuditLogs);
    vi.mocked(api.exportAuditLogsCsv).mockResolvedValue(new Blob(['mock-csv-content']));

    render(
      <BrowserRouter>
        <AuditLogsPage />
      </BrowserRouter>
    );

    await screen.findByText('Stage 2 operational approval by ops executive');

    const exportBtn = screen.getByRole('button', { name: /Export CSV/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(api.exportAuditLogsCsv).toHaveBeenCalled();
    });

    expect(
      await screen.findByText('Audit trail export generated and recorded successfully.')
    ).toBeInTheDocument();
  });
});
