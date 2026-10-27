import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AssignmentsPage } from '../src/pages/AssignmentsPage';
import { api } from '../src/lib/api';

vi.mock('../src/lib/api', () => ({
  api: {
    getAssignments: vi.fn(),
    getAllocations: vi.fn(),
    getTracks: vi.fn(),
    getBatches: vi.fn(),
    getSubmissions: vi.fn(),
    getSubmissionDetail: vi.fn(),
    submitAssignmentDeliverable: vi.fn(),
    reviewSubmission: vi.fn(),
  },
}));

const mockSubmissions = [
  {
    id: 'sub-1',
    allocation_id: 'alloc-1',
    candidate_id: 'cand-1',
    candidate_name: 'John Doe',
    candidate_number: 'EXR-2026-001',
    assignment_code: 'DA-SQL-01',
    assignment_title: 'Relational Database Queries',
    batch_code: 'DA-2026-B1',
    current_submission_status: 'SUBMITTED',
    current_completion_status: 'INCOMPLETE',
    total_attempts: 1,
    latest_score: null,
    due_date_utc: '2026-03-01T18:00:00Z',
    latest_submitted_at_utc: '2026-02-28T15:30:00Z',
    is_late: false,
  },
  {
    id: 'sub-2',
    allocation_id: 'alloc-2',
    candidate_id: 'cand-2',
    candidate_name: 'Jane Smith',
    candidate_number: 'EXR-2026-002',
    assignment_code: 'DA-PY-02',
    assignment_title: 'Pandas Data Cleaning',
    batch_code: 'DA-2026-B1',
    current_submission_status: 'APPROVED',
    current_completion_status: 'PASSED_COMPLETED',
    total_attempts: 2,
    latest_score: 92.0,
    due_date_utc: '2026-03-01T18:00:00Z',
    latest_submitted_at_utc: '2026-03-02T10:00:00Z',
    is_late: true,
  },
];

const mockSubmissionDetail = {
  id: 'sub-1',
  allocation_id: 'alloc-1',
  candidate_id: 'cand-1',
  candidate_name: 'John Doe',
  candidate_number: 'EXR-2026-001',
  candidate_email: 'john@example.com',
  assignment_id: 'asg-1',
  assignment_code: 'DA-SQL-01',
  assignment_title: 'Relational Database Queries',
  assignment_rubric: [
    { key: 'syntax', title: 'SQL Syntax & Formatting', max_points: 40, description: 'Correct syntax' },
    { key: 'correctness', title: 'Query Logic & Performance', max_points: 60, description: 'Optimized joins' },
  ],
  passing_score: 60.0,
  max_score: 100.0,
  current_submission_status: 'SUBMITTED',
  current_completion_status: 'INCOMPLETE',
  total_attempts: 1,
  latest_score: null,
  first_submitted_at_utc: '2026-02-28T15:30:00Z',
  latest_submitted_at_utc: '2026-02-28T15:30:00Z',
  due_date_utc: '2026-03-01T18:00:00Z',
  grace_period_end_utc: null,
  attempts: [
    {
      id: 'att-1',
      attempt_number: 1,
      file_asset: null,
      repository_url: 'https://github.com/johndoe/sql-assignment',
      student_notes: 'Initial attempt submitted for grading.',
      submitted_at_utc: '2026-02-28T15:30:00Z',
      is_late: false,
      lateness_minutes: 0,
      created_at: '2026-02-28T15:30:00Z',
      reviews: [],
    },
  ],
};

describe('Submissions & Review Queue Frontend Flow', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    vi.mocked(api.getAssignments).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });
    vi.mocked(api.getAllocations).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });
    vi.mocked(api.getTracks).mockResolvedValue([]);
    vi.mocked(api.getBatches).mockResolvedValue([]);
    vi.mocked(api.getSubmissions).mockResolvedValue({
      items: mockSubmissions,
      total: 2,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });
    vi.mocked(api.getSubmissionDetail).mockResolvedValue(mockSubmissionDetail);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AssignmentsPage />
      </QueryClientProvider>
    );

  it('renders submissions tab and displays submission items with lateness & status badges', async () => {
    renderComponent();

    const submissionsTab = screen.getByRole('button', { name: /Submissions & Review Queue/i });
    expect(submissionsTab).toBeInTheDocument();
    fireEvent.click(submissionsTab);

    // Verify candidates are rendered
    expect(await screen.findByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('EXR-2026-001')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('EXR-2026-002')).toBeInTheDocument();

    // Verify assignment codes
    expect(screen.getByText('DA-SQL-01')).toBeInTheDocument();
    expect(screen.getByText('DA-PY-02')).toBeInTheDocument();

    // Verify lateness badges
    expect(screen.getByText('On Time')).toBeInTheDocument();
    expect(screen.getByText('Late')).toBeInTheDocument();

    // Verify attempt numbers and scores
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
    expect(screen.getByText('92.0 pts')).toBeInTheDocument();
    expect(screen.getByText('Ungraded')).toBeInTheDocument();
  });

  it('filters submissions by status', async () => {
    renderComponent();

    const submissionsTab = screen.getByRole('button', { name: /Submissions & Review Queue/i });
    fireEvent.click(submissionsTab);

    expect(await screen.findByText('John Doe')).toBeInTheDocument();

    const filterSelect = screen.getByLabelText(/Filter Status:/i);
    fireEvent.change(filterSelect, { target: { value: 'APPROVED' } });

    expect(api.getSubmissions).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'APPROVED' })
    );
  });

  it('opens evaluation modal, calculates rubric scores, and submits review', async () => {
    renderComponent();

    const submissionsTab = screen.getByRole('button', { name: /Submissions & Review Queue/i });
    fireEvent.click(submissionsTab);

    expect(await screen.findByText('John Doe')).toBeInTheDocument();

    const evaluateButtons = screen.getAllByRole('button', { name: /Evaluate/i });
    fireEvent.click(evaluateButtons[0]);

    // Check modal header and content
    expect(await screen.findByText(/Rubric Evaluation & Grading/i)).toBeInTheDocument();
    expect(await screen.findByText(/SQL Syntax & Formatting/i)).toBeInTheDocument();
    expect(await screen.findByText(/Query Logic & Performance/i)).toBeInTheDocument();
    expect(await screen.findByText('https://github.com/johndoe/sql-assignment')).toBeInTheDocument();

    // Fill qualitative feedback
    const feedbackInput = screen.getByLabelText(/Qualitative Feedback \*/i);
    fireEvent.change(feedbackInput, { target: { value: 'Well structured SQL queries with clear explanations.' } });

    vi.mocked(api.reviewSubmission).mockResolvedValue({
      id: 'rev-1',
      attempt_id: 'att-1',
      reviewer_id: 'rev-id',
      review_outcome: 'APPROVED',
      total_score: 100.0,
      qualitative_feedback: 'Well structured SQL queries with clear explanations.',
      review_completed_at_utc: '2026-03-02T12:00:00Z',
      rubric_scores: [],
    });

    const submitReviewBtn = screen.getByRole('button', { name: /Confirm Evaluation & Save Score/i });
    fireEvent.click(submitReviewBtn);

    await waitFor(() => {
      expect(api.reviewSubmission).toHaveBeenCalledWith(
        'sub-1',
        expect.objectContaining({
          review_outcome: 'APPROVED',
          qualitative_feedback: 'Well structured SQL queries with clear explanations.',
        })
      );
    });
  });

  it('opens submit deliverable modal from top header', async () => {
    renderComponent();

    const submitDeliverableBtn = screen.getByRole('button', { name: /Submit Deliverable/i });
    fireEvent.click(submitDeliverableBtn);

    expect(screen.getByText('Submit Assignment Deliverable')).toBeInTheDocument();
    expect(screen.getByLabelText(/Select Allocated Assignment \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Git Repository URL/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText('Submit Assignment Deliverable')).not.toBeInTheDocument();
  });
});
