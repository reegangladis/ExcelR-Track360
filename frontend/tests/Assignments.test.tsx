import { render, screen, fireEvent } from '@testing-library/react';
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
    createAssignment: vi.fn(),
    createAllocation: vi.fn(),
  },
}));

const mockAssignments = [
  {
    id: 'asg-1',
    track_id: 't-1',
    code: 'DA-SQL-01',
    title: 'Relational Database Design & Queries',
    instructions_markdown: '# Instructions\nWrite complex queries.',
    sequence_order: 1,
    is_mandatory: true,
    max_score: 100,
    passing_score: 60,
    rubric_template: [
      { key: 'syntax', title: 'SQL Syntax', max_points: 30 },
      { key: 'performance', title: 'Query Performance', max_points: 70 },
    ],
    allowed_file_types: ['pdf', 'zip'],
    max_file_size_mb: 25,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    track_name: 'Data Analytics Track',
  },
];

const mockAllocations = [
  {
    id: 'alloc-1',
    assignment_id: 'asg-1',
    assignment_code: 'DA-SQL-01',
    assignment_title: 'Relational Database Design & Queries',
    batch_id: 'b-1',
    batch_code: 'DA-2026-B1',
    candidate_id: null,
    candidate_name: null,
    due_date_utc: '2026-02-15T18:00:00Z',
    grace_period_end_utc: '2026-02-17T18:00:00Z',
    allocation_status: 'PENDING',
    created_at: '2026-01-10T00:00:00Z',
  },
];

const mockTracks = [
  {
    id: 't-1',
    course_id: 'c-1',
    code: 'DAT',
    title: 'Data Analytics Track',
    total_mandatory_assignments: 5,
    total_required_projects: 3,
    is_active: true,
  },
];

const mockBatches = [
  {
    id: 'b-1',
    track_id: 't-1',
    batch_code: 'DA-2026-B1',
    title: 'Cohort Jan 2026',
    start_date: '2026-01-01',
    status: 'ACTIVE',
  },
];

describe('AssignmentsPage Component', () => {
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
      items: mockAssignments,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    vi.mocked(api.getAllocations).mockResolvedValue({
      items: mockAllocations,
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    vi.mocked(api.getTracks).mockResolvedValue(mockTracks);
    vi.mocked(api.getBatches).mockResolvedValue(mockBatches);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AssignmentsPage />
      </QueryClientProvider>
    );

  it('renders page header, tabs, and action buttons', () => {
    renderComponent();

    expect(
      screen.getByText('Curriculum Assignments & Cohort Allocations')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /New Assignment/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Allocate to Cohort/i })).toBeInTheDocument();
    expect(screen.getByText('Assignment Catalogue')).toBeInTheDocument();
    expect(screen.getByText('Cohort Allocations')).toBeInTheDocument();
  });

  it('displays assignment catalogue items from query', async () => {
    renderComponent();

    expect(await screen.findByText('DA-SQL-01')).toBeInTheDocument();
    expect(screen.getByText('Relational Database Design & Queries')).toBeInTheDocument();
    expect(screen.getAllByText('Mandatory').length).toBeGreaterThan(0);
    expect(screen.getByText(/2 Criteria/i)).toBeInTheDocument();
  });

  it('switches to Cohort Allocations tab and displays allocation records', async () => {
    renderComponent();

    const allocationsTab = screen.getByRole('button', { name: /Cohort Allocations/i });
    fireEvent.click(allocationsTab);

    expect(await screen.findByText(/Cohort: DA-2026-B1/i)).toBeInTheDocument();
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('opens and closes New Assignment Template modal', async () => {
    renderComponent();

    const createBtn = screen.getByRole('button', { name: /New Assignment/i });
    fireEvent.click(createBtn);

    expect(screen.getByText('Create Curriculum Assignment Template')).toBeInTheDocument();
    expect(screen.getByLabelText(/Assignment Code \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Assignment Title \*/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText('Create Curriculum Assignment Template')).not.toBeInTheDocument();
  });

  it('opens and closes Allocate Assignment modal', async () => {
    renderComponent();

    const allocBtn = screen.getByRole('button', { name: /Allocate to Cohort/i });
    fireEvent.click(allocBtn);

    expect(screen.getByText('Allocate Assignment to Cohort')).toBeInTheDocument();
    expect(screen.getByLabelText(/Assignment Template \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Select Cohort Batch \*/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText('Allocate Assignment to Cohort')).not.toBeInTheDocument();
  });
});
