import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InternshipsPage } from '../src/pages/InternshipsPage';
import { api } from '../src/lib/api';

vi.mock('../src/lib/api', () => ({
  api: {
    getTracks: vi.fn(),
    getCandidates: vi.fn(),
    getInternships: vi.fn(),
    getInternship: vi.fn(),
    getCandidateInternship: vi.fn(),
    checkCandidateInternshipEligibility: vi.fn(),
    initializeInternship: vi.fn(),
    updateInternship: vi.fn(),
    completeInternship: vi.fn(),
    terminateInternship: vi.fn(),
    syncInternshipDuration: vi.fn(),
  },
}));

const mockTracks = [
  {
    id: 'trk-1',
    code: 'DA',
    title: 'Data Analytics Track',
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
      candidate_number: 'EX-2026-001',
      email: 'priya@example.com',
      phone: '+919876543210',
      status: 'ACTIVE',
      batch_id: 'batch-1',
      batch_code: 'DA-2026-01',
      track_code: 'DA',
    },
    {
      id: 'cand-2',
      first_name: 'Rahul',
      last_name: 'Verma',
      candidate_number: 'EX-2026-002',
      email: 'rahul@example.com',
      phone: '+919876543211',
      status: 'ACTIVE',
      batch_id: 'batch-1',
      batch_code: 'DA-2026-01',
      track_code: 'DA',
    },
  ],
  total: 2,
  page: 1,
  page_size: 100,
  total_pages: 1,
};

const mockInternships = {
  items: [
    {
      id: 'int-1',
      candidate_id: 'cand-1',
      candidate_name: 'Priya Sharma',
      candidate_number: 'EX-2026-001',
      track_code: 'DA',
      start_date: '2026-11-15',
      expected_end_date: '2027-05-15',
      actual_completion_date: null,
      accredited_duration_months: 3,
      internship_status: 'ACTIVE',
      company_name: 'Microsoft Cloud Innovation Labs',
    },
    {
      id: 'int-2',
      candidate_id: 'cand-2',
      candidate_name: 'Rahul Verma',
      candidate_number: 'EX-2026-002',
      track_code: 'DA',
      start_date: '2026-06-01',
      expected_end_date: '2026-12-01',
      actual_completion_date: '2026-12-01',
      accredited_duration_months: 6,
      internship_status: 'COMPLETED',
      company_name: 'ExcelR Technology Labs',
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  total_pages: 1,
};

const mockInternshipDetail = {
  id: 'int-1',
  candidate_id: 'cand-1',
  candidate_name: 'Priya Sharma',
  candidate_number: 'EX-2026-001',
  candidate_email: 'priya@example.com',
  track_id: 'trk-1',
  track_code: 'DA',
  track_title: 'Data Analytics Track',
  start_date: '2026-11-15',
  expected_end_date: '2027-05-15',
  actual_completion_date: null,
  accredited_duration_months: 3,
  internship_status: 'ACTIVE',
  company_name: 'Microsoft Cloud Innovation Labs',
  coordinator_notes: 'Candidate allocated to Microsoft Cloud Innovation Labs cohort.',
  created_at: '2026-11-15T00:00:00Z',
  updated_at: '2026-11-15T00:00:00Z',
  milestones: [
    {
      id: 'ms-1',
      milestone_tier: 1,
      title: 'Milestone 1: Foundational Practical Implementation',
      accredited_months: 3,
      status: 'ACHIEVED',
      achieved_at: '2026-11-15T00:00:00Z',
      verified_by_name: 'Master Administrator',
      notes: 'Auto-verified based on project tier completion.',
    },
    {
      id: 'ms-2',
      milestone_tier: 2,
      title: 'Milestone 2: Intermediate Systems Architecture',
      accredited_months: 6,
      status: 'IN_PROGRESS',
      achieved_at: null,
      verified_by_name: null,
      notes: null,
    },
    {
      id: 'ms-3',
      milestone_tier: 3,
      title: 'Milestone 3: Enterprise Capstone Integration',
      accredited_months: 9,
      status: 'PENDING',
      achieved_at: null,
      verified_by_name: null,
      notes: null,
    },
  ],
};

const renderWithClient = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

describe('Phase 11: Internship Lifecycle & Accredited Milestone Progression', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getTracks).mockResolvedValue(mockTracks as any);
    vi.mocked(api.getCandidates).mockResolvedValue(mockCandidates as any);
    vi.mocked(api.getInternships).mockResolvedValue(mockInternships as any);
    vi.mocked(api.getInternship).mockResolvedValue(mockInternshipDetail as any);
  });

  it('renders internship records with decoupled operational dates and accredited duration policy badges', async () => {
    renderWithClient(<InternshipsPage />);

    expect(await screen.findByText('Internship Lifecycle & Milestone Progression')).toBeInTheDocument();
    expect(screen.getByText(/BR-INT-01 \/ BR-INT-02 Decoupled Duration/i)).toBeInTheDocument();

    // Verify candidate rows
    expect(await screen.findByText('Priya Sharma')).toBeInTheDocument();
    expect(screen.getByText('Microsoft Cloud Innovation Labs')).toBeInTheDocument();
    expect(screen.getByText('Tier 1 Baseline')).toBeInTheDocument();

    expect(screen.getByText('Rahul Verma')).toBeInTheDocument();
    expect(screen.getByText('Tier 2 Intermediate')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('executes Candidate Internship Eligibility Diagnostic workflow (FR-INT-001)', async () => {
    vi.mocked(api.checkCandidateInternshipEligibility).mockResolvedValue({
      candidate_id: 'cand-1',
      candidate_name: 'Priya Sharma',
      track_id: 'trk-1',
      track_title: 'Data Analytics Track',
      is_eligible: true,
      approved_projects_count: 2,
      recommended_duration_months: 6,
      active_group_count: 1,
      eligibility_reasons: [
        'Candidate has completed 2 approved project deliverables.',
        'Eligible for Tier 2 accredited duration mapping (6 months).',
      ],
      existing_internship_id: null,
    });

    renderWithClient(<InternshipsPage />);

    // Click Eligibility Check button
    const diagBtn = await screen.findByRole('button', { name: /eligibility check/i });
    fireEvent.click(diagBtn);

    // Modal opens
    expect(await screen.findByText('Internship Eligibility Diagnostic')).toBeInTheDocument();

    // Select candidate
    const candSelect = await screen.findByLabelText(/select candidate for diagnostic/i);
    fireEvent.change(candSelect, { target: { value: 'cand-1' } });

    // Click Analyze button
    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    fireEvent.click(analyzeBtn);

    // Verify diagnostic calculation results
    await waitFor(() => {
      expect(api.checkCandidateInternshipEligibility).toHaveBeenCalledWith('cand-1');
      expect(screen.getByText(/2 Projects/i)).toBeInTheDocument();
      expect(screen.getAllByText(/6 Months/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Eligible for Tier 2 accredited duration mapping/i)).toBeInTheDocument();
    });
  });

  it('initializes a new internship record with decoupled calendar dates (WF-07)', async () => {
    vi.mocked(api.initializeInternship).mockResolvedValue(mockInternshipDetail);

    renderWithClient(<InternshipsPage />);

    // Click Initialize Internship button
    const initBtn = await screen.findByRole('button', { name: /initialize internship/i });
    fireEvent.click(initBtn);

    // Modal appears
    expect(await screen.findByRole('heading', { name: /initialize internship/i })).toBeInTheDocument();

    // Wait for candidate and track options to populate
    await screen.findByRole('option', { name: /Priya Sharma/i });
    await waitFor(() => {
      expect(screen.getAllByRole('option', { name: /DA - Data Analytics Track/i }).length).toBeGreaterThan(0);
    });

    // Fill form
    fireEvent.change(screen.getByLabelText(/candidate \*/i), { target: { value: 'cand-1' } });
    fireEvent.change(screen.getByLabelText(/academic track \*/i), { target: { value: 'trk-1' } });
    fireEvent.change(screen.getByLabelText(/start date \*/i), { target: { value: '2026-11-15' } });
    fireEvent.change(screen.getByLabelText(/company \/ corporate partner/i), {
      target: { value: 'Amazon Web Services' },
    });

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /confirm initialization/i });
    const form = submitBtn.closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(api.initializeInternship).toHaveBeenCalledWith(
        expect.objectContaining({
          candidate_id: 'cand-1',
          track_id: 'trk-1',
          start_date: '2026-11-15',
          company_name: 'Amazon Web Services',
        })
      );
    });
  });

  it('opens Milestone & Audit drawer and renders sequential milestone progression tiers', async () => {
    renderWithClient(<InternshipsPage />);

    // Wait for table to load
    expect(await screen.findByText('Priya Sharma')).toBeInTheDocument();

    // Click Milestones button on first row
    const milestonesRow = await screen.findByTestId('internship-row-int-1');
    const viewBtn = milestonesRow.querySelector('#btn-view-milestones-int-1')!;
    fireEvent.click(viewBtn);

    // Drawer opens
    expect(await screen.findByText('Internship Milestones & Audit')).toBeInTheDocument();
    expect(
      await screen.findByText(/Candidate allocated to Microsoft Cloud Innovation Labs cohort/i)
    ).toBeInTheDocument();

    // Verify all 3 tiers
    expect(screen.getByText('Milestone 1: Foundational Practical Implementation')).toBeInTheDocument();
    expect(screen.getByText('Milestone 2: Intermediate Systems Architecture')).toBeInTheDocument();
    expect(screen.getByText('Milestone 3: Enterprise Capstone Integration')).toBeInTheDocument();
    expect(screen.getByText(/Auto-verified based on project tier completion/i)).toBeInTheDocument();

    // Close drawer
    const closeBtn = screen.getByRole('button', { name: /close drawer/i });
    fireEvent.click(closeBtn);
    await waitFor(() => {
      expect(screen.queryByText('Internship Milestones & Audit')).not.toBeInTheDocument();
    });
  });

  it('updates operational calendar dates and corporate partner (BR-INT-01)', async () => {
    vi.mocked(api.updateInternship).mockResolvedValue(mockInternshipDetail);

    renderWithClient(<InternshipsPage />);

    // Wait for table to load
    const row = await screen.findByTestId('internship-row-int-1');

    // Click Edit Dates button
    const editBtn = row.querySelector('#btn-edit-dates-int-1')!;
    fireEvent.click(editBtn);

    expect(await screen.findByText('Update Operational Calendar')).toBeInTheDocument();

    // Change company name
    const companyInput = screen.getByLabelText(/company partner/i);
    fireEvent.change(companyInput, { target: { value: 'Google Cloud Platform Labs' } });

    // Save
    const saveBtn = screen.getByRole('button', { name: /save changes/i });
    const form = saveBtn.closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(api.updateInternship).toHaveBeenCalledWith(
        'int-1',
        expect.objectContaining({
          company_name: 'Google Cloud Platform Labs',
        })
      );
    });
  });

  it('completes and terminates internships with required validations', async () => {
    vi.mocked(api.completeInternship).mockResolvedValue({
      ...mockInternshipDetail,
      internship_status: 'COMPLETED',
      actual_completion_date: '2027-05-15',
    });
    vi.mocked(api.terminateInternship).mockResolvedValue({
      ...mockInternshipDetail,
      internship_status: 'TERMINATED',
    });

    renderWithClient(<InternshipsPage />);

    // Wait for table to load
    const row = await screen.findByTestId('internship-row-int-1');

    // 1. Completion Workflow
    const completeBtn = row.querySelector('#btn-complete-internship-int-1')!;
    fireEvent.click(completeBtn);

    expect(await screen.findByRole('heading', { name: /confirm completion/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/actual completion date \*/i), {
      target: { value: '2027-05-15' },
    });
    fireEvent.change(screen.getByLabelText(/completion remarks/i), {
      target: { value: 'Candidate successfully demonstrated all industry capstone deliverables.' },
    });

    const completeSubmitBtn = screen.getByRole('button', { name: /confirm completion/i });
    const completeForm = completeSubmitBtn.closest('form')!;
    fireEvent.submit(completeForm);

    await waitFor(() => {
      expect(api.completeInternship).toHaveBeenCalledWith(
        'int-1',
        expect.objectContaining({
          actual_completion_date: '2027-05-15',
          completion_notes: 'Candidate successfully demonstrated all industry capstone deliverables.',
        })
      );
    });

    // 2. Termination Workflow
    const termRow = await screen.findByTestId('internship-row-int-1');
    const terminateBtn = termRow.querySelector('#btn-terminate-internship-int-1')!;
    fireEvent.click(terminateBtn);

    expect(await screen.findByRole('heading', { name: /terminate internship/i })).toBeInTheDocument();
    const reasonInput = screen.getByLabelText(/mandatory termination reason \*/i);
    fireEvent.change(reasonInput, {
      target: { value: 'Candidate withdrew from internship due to corporate relocation.' },
    });

    const termSubmitBtn = screen.getByRole('button', { name: /confirm termination/i });
    const termForm = termSubmitBtn.closest('form')!;
    fireEvent.submit(termForm);

    await waitFor(() => {
      expect(api.terminateInternship).toHaveBeenCalledWith('int-1', {
        reason: 'Candidate withdrew from internship due to corporate relocation.',
      });
    });
  });
});
