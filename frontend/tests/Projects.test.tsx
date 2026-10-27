import { render, screen, fireEvent } from '@testing-library/react';
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
  },
}));

const mockProjects = [
  {
    id: 'prj-1',
    track_id: 'trk-1',
    track_title: 'Data Analytics Track',
    code: 'PRJ-DA-01',
    title: 'Retail Store Performance Analytics',
    tier: 'TIER_1_FOUNDATIONAL' as const,
    complexity: 'LOW' as const,
    min_team_size: 2,
    max_team_size: 4,
    passing_score: 65.0,
    milestone_count: 3,
    is_active: true,
    created_at: '2026-02-01T00:00:00Z',
  },
  {
    id: 'prj-2',
    track_id: 'trk-1',
    track_title: 'Data Analytics Track',
    code: 'PRJ-DA-02',
    title: 'Enterprise Lakehouse & Pipeline Platform',
    tier: 'TIER_3_CAPSTONE' as const,
    complexity: 'CRITICAL' as const,
    min_team_size: 3,
    max_team_size: 5,
    passing_score: 75.0,
    milestone_count: 4,
    is_active: true,
    created_at: '2026-02-15T00:00:00Z',
  },
];

const mockProjectDetail = {
  id: 'prj-1',
  track_id: 'trk-1',
  track_title: 'Data Analytics Track',
  code: 'PRJ-DA-01',
  title: 'Retail Store Performance Analytics',
  description: 'Design and deploy a full-scale star schema and interactive analytics dashboard.',
  tier: 'TIER_1_FOUNDATIONAL' as const,
  complexity: 'LOW' as const,
  min_team_size: 2,
  max_team_size: 4,
  passing_score: 65.0,
  deliverable_specs: [
    { key: 'repo', title: 'Source Code Repository', deliverable_type: 'GIT_REPO' as const, is_required: true },
  ],
  rubric_template: [
    { key: 'schema', title: 'Data Schema & Normalization', max_points: 50.0 },
    { key: 'dashboard', title: 'Dashboard UX & Analytics', max_points: 50.0 },
  ],
  is_active: true,
  milestones: [
    {
      id: 'm-1',
      project_id: 'prj-1',
      sequence_order: 1,
      title: 'Milestone 1: Schema Architecture',
      description: 'Data modeling and ingestion.',
      weight_percentage: 30.0,
      max_score: 100.0,
      is_mandatory: true,
      required_deliverables: [],
      created_at: '2026-02-01T00:00:00Z',
      updated_at: '2026-02-01T00:00:00Z',
    },
    {
      id: 'm-2',
      project_id: 'prj-1',
      sequence_order: 2,
      title: 'Milestone 2: Pipeline Execution',
      description: 'Automated ETL routines.',
      weight_percentage: 70.0,
      max_score: 100.0,
      is_mandatory: true,
      required_deliverables: [],
      created_at: '2026-02-01T00:00:00Z',
      updated_at: '2026-02-01T00:00:00Z',
    },
  ],
  created_at: '2026-02-01T00:00:00Z',
  updated_at: '2026-02-01T00:00:00Z',
};

describe('ProjectsPage Component', () => {
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

    vi.mocked(api.getProjects).mockResolvedValue({
      items: mockProjects,
      total: 2,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });
    vi.mocked(api.getTracks).mockResolvedValue([
      {
        id: 'trk-1',
        course_id: 'crs-1',
        code: 'DAT',
        title: 'Data Analytics Track',
        total_mandatory_assignments: 3,
        total_required_projects: 3,
        is_active: true,
      },
    ]);
    vi.mocked(api.getProject).mockResolvedValue(mockProjectDetail);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <ProjectsPage />
      </QueryClientProvider>
    );

  it('renders page header, tier tabs, and action button', () => {
    renderComponent();

    expect(screen.getByText('Enterprise Projects & Milestone Tiers')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /New Project Specification/i })).toBeInTheDocument();
    expect(screen.getByText('All Project Tiers')).toBeInTheDocument();
    expect(screen.getByText('Tier 1: Foundational')).toBeInTheDocument();
    expect(screen.getByText('Tier 2: Intermediate')).toBeInTheDocument();
    expect(screen.getByText('Tier 3: Capstone')).toBeInTheDocument();
  });

  it('displays project specifications with tier badges and milestone counts', async () => {
    renderComponent();

    expect(await screen.findByText('PRJ-DA-01')).toBeInTheDocument();
    expect(screen.getByText('Retail Store Performance Analytics')).toBeInTheDocument();
    expect(screen.getByText('PRJ-DA-02')).toBeInTheDocument();
    expect(screen.getByText('Enterprise Lakehouse & Pipeline Platform')).toBeInTheDocument();

    expect(screen.getByText(/3 Milestones/i)).toBeInTheDocument();
    expect(screen.getByText(/4 Milestones/i)).toBeInTheDocument();
  });

  it('filters projects by tier when tab is clicked', async () => {
    renderComponent();

    const capstoneTab = screen.getByRole('button', { name: /Tier 3: Capstone/i });
    fireEvent.click(capstoneTab);

    expect(api.getProjects).toHaveBeenCalledWith(
      expect.objectContaining({ tier: 'TIER_3_CAPSTONE' })
    );
  });

  it('opens and closes New Project Specification modal', async () => {
    renderComponent();

    const newBtn = screen.getByRole('button', { name: /New Project Specification/i });
    fireEvent.click(newBtn);

    expect(screen.getByText('New Project Specification Template')).toBeInTheDocument();
    expect(screen.getByLabelText(/Project Code \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Project Title \*/i)).toBeInTheDocument();
    expect(screen.getByText(/Sequential Milestone Stages \*/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText('New Project Specification Template')).not.toBeInTheDocument();
  });

  it('inspects project details and sequential milestones', async () => {
    renderComponent();

    expect(await screen.findByText('PRJ-DA-01')).toBeInTheDocument();

    const inspectBtns = screen.getAllByRole('button', { name: /Inspect Milestones & Rubrics/i });
    fireEvent.click(inspectBtns[0]);

    expect(await screen.findByText(/Sequential Milestones Breakdown/i)).toBeInTheDocument();
    expect(screen.getByText(/Milestone 1: Schema Architecture/i)).toBeInTheDocument();
    expect(screen.getByText(/Weight: 30%/i)).toBeInTheDocument();
  });
});
