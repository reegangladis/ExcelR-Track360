import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectsPage } from '../src/pages/ProjectsPage';
import { api } from '../src/lib/api';

vi.mock('../src/lib/api', () => ({
  api: {
    getProjects: vi.fn(),
    getProject: vi.fn(),
    createProject: vi.fn(),
    updateProject: vi.fn(),
    getTracks: vi.fn(),
    getBatches: vi.fn(),
    getCandidates: vi.fn(),
    getProjectGroups: vi.fn(),
    getProjectGroup: vi.fn(),
    createProjectGroup: vi.fn(),
    updateProjectGroup: vi.fn(),
    addGroupMember: vi.fn(),
    removeGroupMember: vi.fn(),
    setGroupLeader: vi.fn(),
  },
}));

const mockBatches = [
  {
    id: 'batch-1',
    track_id: 'trk-1',
    batch_code: 'DA-2026-01',
    title: 'Data Analytics Cohort 1',
    start_date: '2026-01-10',
    expected_end_date: '2026-07-10',
    status: 'ACTIVE',
  },
];

const mockGroups = [
  {
    id: 'grp-1',
    batch_id: 'batch-1',
    batch_code: 'DA-2026-01',
    project_id: 'prj-1',
    project_title: 'Retail Store Performance Analytics',
    group_name: 'Analytics Falcon Alpha',
    min_size: 2,
    target_size: 4,
    max_size: 5,
    active_members_count: 3,
    status: 'ACTIVE' as const,
    created_at: '2026-03-01T00:00:00Z',
  },
  {
    id: 'grp-2',
    batch_id: 'batch-1',
    batch_code: 'DA-2026-01',
    project_id: null,
    project_title: null,
    group_name: 'Data Pioneers Beta',
    min_size: 2,
    target_size: 4,
    max_size: 5,
    active_members_count: 1,
    status: 'FORMING' as const,
    created_at: '2026-03-05T00:00:00Z',
  },
];

const mockGroupDetail = {
  id: 'grp-1',
  batch_id: 'batch-1',
  batch_code: 'DA-2026-01',
  project_id: 'prj-1',
  project_title: 'Retail Store Performance Analytics',
  group_name: 'Analytics Falcon Alpha',
  min_size: 2,
  target_size: 4,
  max_size: 5,
  active_members_count: 3,
  status: 'ACTIVE' as const,
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-03-01T00:00:00Z',
  members: [
    {
      id: 'mem-1',
      group_id: 'grp-1',
      candidate_id: 'cand-1',
      candidate_name: 'Alice Johnson',
      candidate_number: 'EX-2026-0001',
      candidate_email: 'alice@example.com',
      role: 'LEADER' as const,
      member_status: 'ACTIVE' as const,
      joined_at: '2026-03-01T00:00:00Z',
    },
    {
      id: 'mem-2',
      group_id: 'grp-1',
      candidate_id: 'cand-2',
      candidate_name: 'Bob Smith',
      candidate_number: 'EX-2026-0002',
      candidate_email: 'bob@example.com',
      role: 'MEMBER' as const,
      member_status: 'ACTIVE' as const,
      joined_at: '2026-03-01T00:00:00Z',
    },
    {
      id: 'mem-3',
      group_id: 'grp-1',
      candidate_id: 'cand-3',
      candidate_name: 'Charlie Davis',
      candidate_number: 'EX-2026-0003',
      candidate_email: 'charlie@example.com',
      role: 'MEMBER' as const,
      member_status: 'ACTIVE' as const,
      joined_at: '2026-03-02T00:00:00Z',
    },
  ],
};

const mockCandidates = [
  {
    id: 'cand-1',
    user_id: 'u-1',
    candidate_number: 'EX-2026-0001',
    first_name: 'Alice',
    last_name: 'Johnson',
    email: 'alice@example.com',
    phone: '+919800000001',
    lifecycle_status: 'ACTIVE',
    project_eligible: true,
    completed_projects_count: 0,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  },
  {
    id: 'cand-2',
    user_id: 'u-2',
    candidate_number: 'EX-2026-0002',
    first_name: 'Bob',
    last_name: 'Smith',
    email: 'bob@example.com',
    phone: '+919800000002',
    lifecycle_status: 'ACTIVE',
    project_eligible: true,
    completed_projects_count: 0,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  },
  {
    id: 'cand-4',
    user_id: 'u-4',
    candidate_number: 'EX-2026-0004',
    first_name: 'Diana',
    last_name: 'Prince',
    email: 'diana@example.com',
    phone: '+919800000004',
    lifecycle_status: 'ACTIVE',
    project_eligible: true,
    completed_projects_count: 0,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  },
];

describe('Phase 9: Project Groups & Dynamic Team Sizing Component', () => {
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

    vi.mocked(api.getTracks).mockResolvedValue([]);
    vi.mocked(api.getProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });
    vi.mocked(api.getBatches).mockResolvedValue(mockBatches);
    vi.mocked(api.getProjectGroups).mockResolvedValue({
      items: mockGroups,
      total: 2,
      page: 1,
      page_size: 9,
      total_pages: 1,
    });
    vi.mocked(api.getProjectGroup).mockResolvedValue(mockGroupDetail);
    vi.mocked(api.getCandidates).mockResolvedValue({
      items: mockCandidates,
      total: 3,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });
    vi.mocked(api.setGroupLeader).mockResolvedValue(mockGroupDetail);
    vi.mocked(api.removeGroupMember).mockResolvedValue(mockGroupDetail);
    vi.mocked(api.updateProjectGroup).mockResolvedValue(mockGroupDetail);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <ProjectsPage />
      </QueryClientProvider>
    );

  it('switches between Project Specifications and Project Groups tabs', async () => {
    renderComponent();

    // Verify main tab buttons exist
    const catalogTab = screen.getByRole('button', { name: /Project Specifications Catalog/i });
    const groupsTab = screen.getByRole('button', { name: /Project Groups & Team Sizing/i });
    expect(catalogTab).toBeInTheDocument();
    expect(groupsTab).toBeInTheDocument();

    // Click Groups tab
    fireEvent.click(groupsTab);

    // Verify Groups UI is mounted
    expect(await screen.findByText('Analytics Falcon Alpha')).toBeInTheDocument();
    expect(screen.getByText('Data Pioneers Beta')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Form Project Group/i })).toBeInTheDocument();
  });

  it('displays dynamic team sizing meter with accurate member counts and status badges', async () => {
    renderComponent();

    fireEvent.click(screen.getByRole('button', { name: /Project Groups & Team Sizing/i }));

    expect(await screen.findByText('Analytics Falcon Alpha')).toBeInTheDocument();

    // Check status badges
    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    expect(screen.getByText('FORMING')).toBeInTheDocument();

    // Check capacity text (3 / 4, Min: 2, Max: 5)
    expect(screen.getByText(/3 \/ 4 \(Min: 2, Max: 5\)/i)).toBeInTheDocument();
    expect(screen.getByText(/1 \/ 4 \(Min: 2, Max: 5\)/i)).toBeInTheDocument();
  });

  it('opens and closes Form Dynamic Project Group modal with sizing inputs', async () => {
    renderComponent();

    fireEvent.click(screen.getByRole('button', { name: /Project Groups & Team Sizing/i }));

    const formBtn = await screen.findByRole('button', { name: /Form Project Group/i });
    fireEvent.click(formBtn);

    expect(screen.getByText('Form Dynamic Project Group')).toBeInTheDocument();
    expect(screen.getByLabelText(/Cohort Batch \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Group Name \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Min Members/i)).toHaveValue(2);
    expect(screen.getByLabelText(/Target Members/i)).toHaveValue(4);
    expect(screen.getByLabelText(/Max Members/i)).toHaveValue(5);

    // Close modal
    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText('Form Dynamic Project Group')).not.toBeInTheDocument();
  });

  it('manages team roster, displays leader crown badge, and triggers leader assignment', async () => {
    renderComponent();

    fireEvent.click(screen.getByRole('button', { name: /Project Groups & Team Sizing/i }));

    expect(await screen.findByText('Analytics Falcon Alpha')).toBeInTheDocument();

    // Click Manage Team Roster on grp-1
    const manageBtns = await screen.findAllByRole('button', { name: /Manage Team Roster/i });
    fireEvent.click(manageBtns[0]);

    // Detailed roster should be fetched and shown
    expect(await screen.findByText('Enrolled Team Members (3)')).toBeInTheDocument();
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    expect(screen.getByText('Bob Smith')).toBeInTheDocument();
    expect(screen.getByText('Charlie Davis')).toBeInTheDocument();

    // Alice is LEADER
    expect(screen.getByText('LEADER')).toBeInTheDocument();

    // Bob can be promoted to Leader
    const makeLeaderBtns = screen.getAllByRole('button', { name: /Make Leader/i });
    fireEvent.click(makeLeaderBtns[0]);

    await waitFor(() => {
      expect(api.setGroupLeader).toHaveBeenCalledWith('grp-1', 'cand-2');
    });
  });

  it('triggers remove member mutation on member removal button', async () => {
    renderComponent();

    fireEvent.click(screen.getByRole('button', { name: /Project Groups & Team Sizing/i }));

    const manageBtns = await screen.findAllByRole('button', { name: /Manage Team Roster/i });
    fireEvent.click(manageBtns[0]);

    expect(await screen.findByText('Alice Johnson')).toBeInTheDocument();

    const removeBtns = screen.getAllByRole('button', { name: /Remove/i });
    fireEvent.click(removeBtns[0]);

    await waitFor(() => {
      expect(api.removeGroupMember).toHaveBeenCalledWith('grp-1', 'cand-1', undefined);
    });
  });
});
