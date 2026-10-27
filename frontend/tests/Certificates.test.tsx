import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { CertificatesPage } from '../src/pages/CertificatesPage';
import { PublicVerifyPage } from '../src/pages/PublicVerifyPage';
import { api } from '../src/lib/api';

vi.mock('../src/lib/api', () => ({
  api: {
    getTracks: vi.fn(),
    getCandidates: vi.fn(),
    getCertificates: vi.fn(),
    getCertificate: vi.fn(),
    getCertificateEligibility: vi.fn(),
    initiateCertificate: vi.fn(),
    reviewCertificateStage1: vi.fn(),
    approveCertificateStage2: vi.fn(),
    revokeCertificate: vi.fn(),
    downloadCertificatePdf: vi.fn(),
    verifyCertificatePublic: vi.fn(),
  },
}));

const mockTracks = [
  {
    id: 'trk-1',
    code: 'FSD',
    title: 'Full Stack Development',
    total_mandatory_assignments: 2,
    total_required_projects: 3,
    is_active: true,
  },
];

const mockCandidates = {
  items: [
    {
      id: 'cand-1',
      first_name: 'Priya',
      last_name: 'Sharma',
      candidate_number: 'EXR-2026-001',
      email: 'priya@example.com',
      phone: '+919876543210',
      status: 'ACTIVE',
      batch_id: 'batch-1',
      batch_code: 'FSD-2026-01',
      track_code: 'FSD',
    },
  ],
  total: 1,
};

const mockCertificates = {
  items: [
    {
      id: 'cert-1',
      candidate_id: 'cand-1',
      candidate_display_name: 'Priya Sharma',
      track_id: 'trk-1',
      course_display_title: 'Full Stack Development',
      serial_number: 'EXCELR-2026-FSD-9C4E2A8F',
      certificate_type: 'FINAL_COMPREHENSIVE',
      accredited_duration_months: 6,
      issue_date: '2026-10-27',
      verification_hash: 'a1b2c3d4e5f6789012345678abcdef0123456789abcdef0123456789abcdef01',
      verification_qr_url: '/verify/EXCELR-2026-FSD-9C4E2A8F',
      status: 'PENDING_APPROVAL',
      requested_by_id: 'user-coord',
      requested_at: '2026-10-27T10:00:00Z',
      approvals: [],
      revocations: [],
      created_at: '2026-10-27T10:00:00Z',
      updated_at: '2026-10-27T10:00:00Z',
    },
    {
      id: 'cert-2',
      candidate_id: 'cand-2',
      candidate_display_name: 'Rahul Verma',
      track_id: 'trk-1',
      course_display_title: 'Full Stack Development',
      serial_number: 'EXCELR-2026-FSD-1A2B3C4D',
      certificate_type: 'FINAL_COMPREHENSIVE',
      accredited_duration_months: 6,
      issue_date: '2026-10-25',
      verification_hash: 'b2c3d4e5f6789012345678abcdef0123456789abcdef0123456789abcdef0123',
      verification_qr_url: '/verify/EXCELR-2026-FSD-1A2B3C4D',
      status: 'REVIEWED',
      requested_by_id: 'user-coord',
      requested_at: '2026-10-25T10:00:00Z',
      stage1_reviewer_id: 'user-coord-2',
      stage1_reviewed_at: '2026-10-26T10:00:00Z',
      stage1_notes: 'Prerequisites verified.',
      approvals: [
        {
          id: 'appr-1',
          certificate_id: 'cert-2',
          approver_id: 'user-coord-2',
          approver_name: 'Coordinator Jane',
          stage: 'STAGE_1_REVIEW',
          decision: 'APPROVED',
          decision_notes: 'Prerequisites verified.',
          decided_at_utc: '2026-10-26T10:00:00Z',
        },
      ],
      revocations: [],
      created_at: '2026-10-25T10:00:00Z',
      updated_at: '2026-10-26T10:00:00Z',
    },
    {
      id: 'cert-3',
      candidate_id: 'cand-3',
      candidate_display_name: 'Amit Patel',
      track_id: 'trk-1',
      course_display_title: 'Full Stack Development',
      serial_number: 'EXCELR-2026-FSD-3E4F5A6B',
      certificate_type: 'FINAL_COMPREHENSIVE',
      accredited_duration_months: 6,
      issue_date: '2026-10-20',
      verification_hash: 'c3d4e5f6789012345678abcdef0123456789abcdef0123456789abcdef012345',
      verification_qr_url: '/verify/EXCELR-2026-FSD-3E4F5A6B',
      status: 'ISSUED',
      requested_by_id: 'user-coord',
      requested_at: '2026-10-20T10:00:00Z',
      stage1_reviewer_id: 'user-coord-2',
      stage1_reviewed_at: '2026-10-21T10:00:00Z',
      stage2_approver_id: 'user-approver',
      stage2_approved_at: '2026-10-22T10:00:00Z',
      issued_at_utc: '2026-10-22T10:00:00Z',
      approvals: [],
      revocations: [],
      created_at: '2026-10-20T10:00:00Z',
      updated_at: '2026-10-22T10:00:00Z',
    },
  ],
  total: 3,
  page: 1,
  page_size: 15,
};

const mockEligibilityDiagnostic = {
  candidate_id: 'cand-1',
  candidate_name: 'Priya Sharma',
  track_id: 'trk-1',
  track_title: 'Full Stack Development',
  total_mandatory_assignments: 2,
  passed_mandatory_assignments: 2,
  assignments_completed: true,
  total_required_projects: 3,
  approved_project_milestones: 2,
  projects_completed: true,
  has_internship: true,
  internship_status: 'COMPLETED',
  internship_completed: true,
  accredited_duration_months: 6,
  is_eligible: true,
  ineligibility_reasons: [],
  has_active_certificate: false,
};

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('CertificatesPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getTracks as any).mockResolvedValue(mockTracks);
    (api.getCandidates as any).mockResolvedValue(mockCandidates);
    (api.getCertificates as any).mockResolvedValue(mockCertificates);
    (api.getCertificate as any).mockResolvedValue(mockCertificates.items[0]);
    (api.getCertificateEligibility as any).mockResolvedValue(mockEligibilityDiagnostic);
  });

  it('renders certificate directory with metrics and table entries', async () => {
    renderWithProviders(<CertificatesPage />);

    expect(
      screen.getByText(/Certificate Management & Verification Engine/i)
    ).toBeInTheDocument();

    // Verify candidate rows rendered
    await screen.findByText('Priya Sharma');
    expect(screen.getByText('Rahul Verma')).toBeInTheDocument();
    expect(screen.getByText('Amit Patel')).toBeInTheDocument();
    expect(screen.getByText('EXCELR-2026-FSD-9C4E2A8F')).toBeInTheDocument();

    // Verify metrics badges
    expect(screen.getByText('Total Issued')).toBeInTheDocument();
    expect(screen.getAllByText('Stage 1 Review')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Stage 2 Sign-off')[0]).toBeInTheDocument();
  });

  it('opens request certificate modal and calculates diagnostic eligibility', async () => {
    renderWithProviders(<CertificatesPage />);

    // Wait for initial data to load
    await screen.findByText('Priya Sharma');

    const reqBtn = screen.getByRole('button', { name: /Request Certificate/i });
    fireEvent.click(reqBtn);

    // Modal title
    await screen.findByRole('heading', { name: /Request Certificate Issuance/i });

    // Wait for options to be populated
    await screen.findByRole('option', { name: /Priya Sharma/i });

    // Select candidate
    const candSelect = screen.getByLabelText(/Select Candidate \*/i);
    fireEvent.change(candSelect, { target: { value: 'cand-1' } });

    // Select track
    const trackSelect = screen.getByLabelText(/Specialization Course Track \*/i);
    fireEvent.change(trackSelect, { target: { value: 'trk-1' } });

    // Diagnostic card preview
    await screen.findByText(/Prerequisite Diagnostic Evaluation/i);
    await screen.findByText(/Eligible for Credential/i);
    expect(screen.getAllByText(/6 Months/i)[0]).toBeInTheDocument();

    // Submit form
    (api.initiateCertificate as any).mockResolvedValueOnce({
      id: 'cert-new',
      serial_number: 'EXCELR-2026-FSD-NEW12345',
      status: 'PENDING_APPROVAL',
    });

    const submitBtn = screen.getByRole('button', { name: /Submit Request/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.initiateCertificate).toHaveBeenCalledWith(
        expect.objectContaining({
          candidate_id: 'cand-1',
          track_id: 'trk-1',
        })
      );
    });
  });

  it('opens and submits Stage 1 Coordinator Review', async () => {
    renderWithProviders(<CertificatesPage />);

    const stage1Btn = await screen.findByRole('button', { name: /Stage 1 Review/i });
    fireEvent.click(stage1Btn);

    await screen.findByRole('heading', { name: /Stage 1: Coordinator Credential Review/i });

    (api.reviewCertificateStage1 as any).mockResolvedValueOnce({
      ...mockCertificates.items[0],
      status: 'REVIEWED',
    });

    const submitDecision = screen.getByRole('button', { name: /Submit Stage 1 Decision/i });
    fireEvent.click(submitDecision);

    await waitFor(() => {
      expect(api.reviewCertificateStage1).toHaveBeenCalledWith(
        'cert-1',
        expect.objectContaining({
          decision: 'APPROVED',
        })
      );
    });
  });

  it('opens and submits Stage 2 Director Sign-off with SoD indicator', async () => {
    renderWithProviders(<CertificatesPage />);

    const stage2Btn = await screen.findByRole('button', { name: /Stage 2 Sign-off/i });
    fireEvent.click(stage2Btn);

    await screen.findByRole('heading', { name: /Stage 2: Director Sign-off & Generation/i });
    expect(screen.getByText(/Separation of Duties \(SoD\) Protocol/i)).toBeInTheDocument();

    (api.approveCertificateStage2 as any).mockResolvedValueOnce({
      ...mockCertificates.items[1],
      status: 'ISSUED',
    });

    const submitSignoff = screen.getByRole('button', { name: /Execute Stage 2 Sign-off/i });
    fireEvent.click(submitSignoff);

    await waitFor(() => {
      expect(api.approveCertificateStage2).toHaveBeenCalledWith(
        'cert-2',
        expect.objectContaining({
          decision: 'APPROVED',
        }),
        false
      );
    });
  });

  it('opens and executes certificate revocation modal with reason', async () => {
    renderWithProviders(<CertificatesPage />);

    const revokeBtn = await screen.findByTitle('Revoke Certificate');
    fireEvent.click(revokeBtn);

    await screen.findByRole('heading', { name: /Revoke Certificate Credential/i });

    const rationaleInput = screen.getByPlaceholderText(/State comprehensive justification/i);
    fireEvent.change(rationaleInput, {
      target: { value: 'Academic malpractice detected in project deliverable repository.' },
    });

    (api.revokeCertificate as any).mockResolvedValueOnce({
      ...mockCertificates.items[2],
      status: 'REVOKED',
    });

    const confirmRevoke = screen.getByRole('button', { name: /Confirm Revocation/i });
    fireEvent.click(confirmRevoke);

    await waitFor(() => {
      expect(api.revokeCertificate).toHaveBeenCalledWith(
        'cert-3',
        expect.objectContaining({
          reason_category: 'ACADEMIC_MALPRACTICE',
          detailed_reason: 'Academic malpractice detected in project deliverable repository.',
        })
      );
    });
  });

  it('downloads certificate artifact PDF', async () => {
    renderWithProviders(<CertificatesPage />);

    const pdfBtn = await screen.findByRole('button', { name: /PDF/i });
    fireEvent.click(pdfBtn);

    await waitFor(() => {
      expect(api.downloadCertificatePdf).toHaveBeenCalledWith(
        'cert-3',
        'EXCELR-2026-FSD-3E4F5A6B.pdf'
      );
    });
  });
});

describe('PublicVerifyPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders public portal and displays verified credential details', async () => {
    (api.verifyCertificatePublic as any).mockResolvedValueOnce({
      is_valid: true,
      status: 'ISSUED',
      serial_number: 'EXCELR-2026-FSD-9C4E2A8F',
      candidate_name: 'Priya Sharma',
      track_title: 'Full Stack Development',
      accredited_duration_months: 6,
      issue_date: '2026-10-27',
      verification_hash: 'a1b2c3d4e5f6789012345678abcdef0123456789abcdef0123456789abcdef01',
      verification_qr_url: '/verify/EXCELR-2026-FSD-9C4E2A8F',
    });

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <BrowserRouter>
          <PublicVerifyPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Initial search prompt
    expect(screen.getByText(/Verify Credential Authenticity/i)).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText(/Enter Serial ID/i);
    fireEvent.change(searchInput, { target: { value: 'EXCELR-2026-FSD-9C4E2A8F' } });

    const verifyBtn = screen.getByRole('button', { name: /Verify/i });
    fireEvent.click(verifyBtn);

    // Verified Result
    await screen.findByText(/Authentic Verified Credential/i);
    expect(screen.getByText('Priya Sharma')).toBeInTheDocument();
    expect(screen.getByText('Full Stack Development')).toBeInTheDocument();
    expect(screen.getByText(/6 Months Accredited Program/i)).toBeInTheDocument();
  });
});
