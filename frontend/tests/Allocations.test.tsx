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
    assignGroupMentor: vi.fn(),
    allocateProjectToGroup: vi.fn(),
    submitGroupDeliverable: vi.fn(),
    listGroupSubmissions: vi.fn(),
    reviewGroupSubmission: vi.fn(),
    requestGroupProgression: vi.fn(),
    getGroupReadiness: vi.fn(),
    advanceGroup: vi.fn(),
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

const mockProjects = {
  items: [
    {
      id: 'prj-1',
      track_id: 'trk-1',
      track_code: 'DA',
      code: 'PRJ-DA-01',
      title: 'Retail Store Performance Analytics',
      tier: 'TIER_1_FOUNDATIONAL',
      version: 1,
      min_team_size: 2,
      max_team_size: 5,
      is_active: true,
      milestones_count: 3,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'prj-2',
      track_id: 'trk-1',
      track_code: 'DA',
      code: 'PRJ-DA-02',
      title: 'Supply Chain Forecasting Platform',
      tier: 'TIER_2_INTERMEDIATE',
      version: 1,
      min_team_size: 2,
      max_team_size: 5,
      is_active: true,
      milestones_count: 4,
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
  total_pages: 1,
};

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
    readiness_status: 'BLOCKED_PENDING_MEMBERS' as const,
    mentor_id: 'user-mentor-1',
    mentor_name: 'Dr. Jane Evaluator',
    created_at: '2026-03-01T00:00:00Z',
  },
];

const mockCandidates = {
  items: [
    {
      id: 'cand-1',
      candidate_number: 'EX-2026-0001',
      first_name: 'Alice',
      last_name: 'Johnson',
      email: 'alice@example.com',
      phone: '+919876543210',
      enrolled_batch_id: 'batch-1',
      lifecycle_status: 'ACTIVE',
      project_eligible: true,
    },
    {
      id: 'cand-2',
      candidate_number: 'EX-2026-0002',
      first_name: 'Bob',
      last_name: 'Smith',
      email: 'bob@example.com',
      phone: '+919876543211',
      enrolled_batch_id: 'batch-1',
      lifecycle_status: 'ACTIVE',
      project_eligible: true,
    },
  ],
  total: 2,
  page: 1,
  page_size: 50,
  total_pages: 1,
};

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
  active_members_count: 2,
  status: 'ACTIVE' as const,
  readiness_status: 'BLOCKED_PENDING_MEMBERS' as const,
  mentor_id: 'user-mentor-1',
  mentor_name: 'Dr. Jane Evaluator',
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
  ],
};

const mockReadiness = {
  group_id: 'grp-1',
  group_name: 'Analytics Falcon Alpha',
  group_status: 'ACTIVE',
  readiness_status: 'BLOCKED_PENDING_MEMBERS',
  current_project_id: 'prj-1',
  current_project_title: 'Retail Store Performance Analytics',
  current_tier: 'TIER_1_FOUNDATIONAL',
  current_milestone_id: 'm-1',
  current_milestone_title: 'Architecture & Schema',
  deliverable_approved: true,
  active_members_count: 2,
  requests_count: 1,
  ready_candidate_ids: ['cand-1'],
  pending_candidate_ids: ['cand-2'],
  pending_candidate_names: ['Bob Smith'],
  can_advance: false,
  latest_submission_status: 'APPROVED',
  latest_submission_score: 92,
  progression_requests: [
    {
      id: 'req-1',
      candidate_id: 'cand-1',
      candidate_name: 'Alice Johnson',
      candidate_number: 'EX-2026-0001',
      status: 'APPROVED',
      requested_at: '2026-03-10T12:00:00Z',
      notes: 'Finalized tests and schemas.',
    },
  ],
};

const mockSubmissions = [
  {
    id: 'sub-1',
    group_id: 'grp-1',
    project_id: 'prj-1',
    submitted_by_id: 'cand-1',
    submitted_by_name: 'Alice Johnson',
    attempt_number: 1,
    repo_url: 'https://github.com/excelr/analytics-alpha',
    live_demo_url: 'https://demo.example.com',
    documentation_url: 'https://docs.example.com',
    notes: 'Initial milestone release',
    status: 'SUBMITTED' as const,
    score: null,
    rubric_scores: [],
    feedback: null,
    submitted_at: '2026-03-08T10:00:00Z',
  },
];

describe('Phase 10: Project Allocation & Group Completion Flow', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    vi.mocked(api.getTracks).mockResolvedValue([
      {
        id: 'trk-1',
        course_id: 'crs-1',
        code: 'DA',
        title: 'Data Analytics Track',
        total_mandatory_assignments: 3,
        total_required_projects: 3,
        is_active: true,
      } as any,
    ]);
    vi.mocked(api.getBatches).mockResolvedValue(mockBatches);
    vi.mocked(api.getProjects).mockResolvedValue(mockProjects);
    vi.mocked(api.getProjectGroups).mockResolvedValue({
      items: mockGroups,
      total: 1,
      page: 1,
      page_size: 9,
      total_pages: 1,
    });
    vi.mocked(api.getProjectGroup).mockResolvedValue(mockGroupDetail);
    vi.mocked(api.getCandidates).mockResolvedValue(mockCandidates);
    vi.mocked(api.getGroupReadiness).mockResolvedValue(mockReadiness);
    vi.mocked(api.listGroupSubmissions).mockResolvedValue(mockSubmissions);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <ProjectsPage />
      </QueryClientProvider>
    );

  it('renders readiness badges and mentor information on group cards', async () => {
    renderComponent();

    // Switch to Project Groups tab
    const groupsTab = screen.getByRole('button', { name: /Project Groups & Team Sizing/i });
    fireEvent.click(groupsTab);

    // Wait for group card to render
    await waitFor(() => {
      expect(screen.getByText('Analytics Falcon Alpha')).toBeInTheDocument();
    });

    // Check mentor information badge
    expect(screen.getByText(/Mentor:/i)).toBeInTheDocument();
    expect(screen.getByText('Dr. Jane Evaluator')).toBeInTheDocument();

    // Check readiness badge
    expect(screen.getByText('PENDING SIGN-OFFS')).toBeInTheDocument();
  });

  it('opens Allocate Project modal with prerequisite waiver and triggers allocation', async () => {
    vi.mocked(api.allocateProjectToGroup).mockResolvedValue({
      ...mockGroupDetail,
      project_id: 'prj-2',
      project_title: 'Supply Chain Forecasting Platform',
    });

    renderComponent();

    const groupsTab = screen.getByRole('button', { name: /Project Groups & Team Sizing/i });
    fireEvent.click(groupsTab);

    await waitFor(() => {
      expect(screen.getByText('Analytics Falcon Alpha')).toBeInTheDocument();
    });

    // Click Allocate button on group card
    const allocateBtn = screen.getByRole('button', { name: /Allocate/i });
    fireEvent.click(allocateBtn);

    // Check modal opens
    expect(screen.getByText(/Allocate Project to Analytics Falcon Alpha/i)).toBeInTheDocument();

    // Select project specification
    const projectSelect = screen.getByLabelText(/Select Project Specification/i);
    fireEvent.change(projectSelect, { target: { value: 'prj-2' } });

    // Toggle prerequisite waiver checkbox
    const waiverCheckbox = screen.getByLabelText(/Waive Prerequisite Mandatory Assignments/i);
    fireEvent.click(waiverCheckbox);

    // Enter waiver justification
    const waiverJustification = screen.getByPlaceholderText(/State academic reason or coordinator approval rationale/i);
    fireEvent.change(waiverJustification, {
      target: { value: 'Approved by Head of Data Science due to advanced prior credentials.' },
    });

    // Submit allocation
    const submitBtn = screen.getByRole('button', { name: /Confirm Project Allocation/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.allocateProjectToGroup).toHaveBeenCalledWith('grp-1', {
        project_id: 'prj-2',
        waive_prerequisites: true,
        waiver_justification: 'Approved by Head of Data Science due to advanced prior credentials.',
      });
    });
  });

  it('opens Assign Mentor modal and triggers mentor assignment', async () => {
    vi.mocked(api.assignGroupMentor).mockResolvedValue({
      ...mockGroupDetail,
      mentor_id: 'user-mentor-2',
      mentor_name: 'Prof. Alan Turing',
    });

    renderComponent();

    const groupsTab = screen.getByRole('button', { name: /Project Groups & Team Sizing/i });
    fireEvent.click(groupsTab);

    await waitFor(() => {
      expect(screen.getByText('Analytics Falcon Alpha')).toBeInTheDocument();
    });

    // Click Change mentor link
    const changeMentorBtn = screen.getByText('Change');
    fireEvent.click(changeMentorBtn);

    // Check modal opens
    expect(screen.getByText(/Assign Staff Mentor to Analytics Falcon Alpha/i)).toBeInTheDocument();

    // Enter Mentor UUID
    const mentorInput = screen.getByLabelText(/Staff Mentor \/ Evaluator User ID/i);
    fireEvent.change(mentorInput, { target: { value: '00000000-0000-0000-0000-000000000002' } });

    // Submit mentor assignment
    const submitMentorBtn = screen.getByRole('button', { name: /Assign Mentor/i });
    fireEvent.click(submitMentorBtn);

    await waitFor(() => {
      expect(api.assignGroupMentor).toHaveBeenCalledWith('grp-1', '00000000-0000-0000-0000-000000000002');
    });
  });

  it('inspects group readiness checklist, records candidate sign-off, and advances group with coordinator override', async () => {
    vi.mocked(api.requestGroupProgression).mockResolvedValue({
      ...mockReadiness,
      requests_count: 2,
      can_advance: true,
    });

    vi.mocked(api.advanceGroup).mockResolvedValue({
      ...mockGroupDetail,
      readiness_status: 'AWAITING_SUBMISSION' as const,
    });

    renderComponent();

    const groupsTab = screen.getByRole('button', { name: /Project Groups & Team Sizing/i });
    fireEvent.click(groupsTab);

    await waitFor(() => {
      expect(screen.getByText('Analytics Falcon Alpha')).toBeInTheDocument();
    });

    // Click Readiness button
    const readinessBtn = screen.getByRole('button', { name: /Readiness/i });
    fireEvent.click(readinessBtn);

    // Modal opens and shows checklist
    await waitFor(() => {
      expect(screen.getByText(/Group Readiness & Advancement: Analytics Falcon Alpha/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Alice Johnson/i)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/Bob Smith/i)[0]).toBeInTheDocument();
      expect(screen.getByText(/Awaiting Sign-off/i)).toBeInTheDocument();
    });

    // Submit progression sign-off for Bob
    const candidateSelect = screen.getByLabelText(/Select Candidate to Sign-off/i);
    fireEvent.change(candidateSelect, { target: { value: 'cand-2' } });

    const notesInput = screen.getByPlaceholderText(/Completed deliverable review and tests/i);
    fireEvent.change(notesInput, { target: { value: 'All components tested and verified.' } });

    const recordSignoffBtn = screen.getByRole('button', { name: /Record Sign-off/i });
    fireEvent.click(recordSignoffBtn);

    await waitFor(() => {
      expect(api.requestGroupProgression).toHaveBeenCalledWith('grp-1', {
        candidate_id: 'cand-2',
        notes: 'All components tested and verified.',
      });
    });

    // Advance group with coordinator override justification
    const overrideInput = screen.getByPlaceholderText(/Provide formal pedagogical justification/i);
    fireEvent.change(overrideInput, {
      target: { value: 'Milestone passed by committee evaluation.' },
    });

    const advanceBtn = screen.getByRole('button', { name: /Advance Group to Next Project \/ Capstone/i });
    fireEvent.click(advanceBtn);

    await waitFor(() => {
      expect(api.advanceGroup).toHaveBeenCalledWith('grp-1', {
        override_justification: 'Milestone passed by committee evaluation.',
      });
    });
  });

  it('manages deliverable submissions and submits evaluator rubric review', async () => {
    vi.mocked(api.submitGroupDeliverable).mockResolvedValue({
      id: 'sub-2',
      group_id: 'grp-1',
      project_id: 'prj-1',
      submitted_by_id: 'cand-1',
      submitted_by_name: 'Alice Johnson',
      attempt_number: 2,
      repo_url: 'https://github.com/excelr/analytics-alpha-v2',
      status: 'SUBMITTED' as const,
      rubric_scores: [],
      submitted_at: '2026-03-12T10:00:00Z',
    });

    vi.mocked(api.reviewGroupSubmission).mockResolvedValue({
      ...mockSubmissions[0],
      status: 'APPROVED' as const,
      score: 95,
      feedback: 'Excellent modular structure and clean data modeling.',
    });

    renderComponent();

    const groupsTab = screen.getByRole('button', { name: /Project Groups & Team Sizing/i });
    fireEvent.click(groupsTab);

    await waitFor(() => {
      expect(screen.getByText('Analytics Falcon Alpha')).toBeInTheDocument();
    });

    // Click Submissions button
    const submissionsBtn = screen.getByRole('button', { name: /Submissions/i });
    fireEvent.click(submissionsBtn);

    // Modal opens showing existing attempt #1
    await waitFor(() => {
      expect(screen.getByText(/Deliverable Submissions & Reviews: Analytics Falcon Alpha/i)).toBeInTheDocument();
      expect(screen.getByText(/Attempt #1/i)).toBeInTheDocument();
    });

    // Fill new deliverable form
    const submitterSelect = screen.getByLabelText(/Submitting Candidate/i);
    fireEvent.change(submitterSelect, { target: { value: 'cand-1' } });

    const repoUrlInput = screen.getByPlaceholderText('https://github.com/org/repo');
    fireEvent.change(repoUrlInput, { target: { value: 'https://github.com/excelr/analytics-alpha-v2' } });

    const notesArea = screen.getByPlaceholderText(/Provide release notes, testing credentials/i);
    fireEvent.change(notesArea, { target: { value: 'Fixed all lint errors and added unit test suite.' } });

    const submitDeliverableBtn = screen.getByRole('button', { name: /Submit Deliverable/i });
    fireEvent.click(submitDeliverableBtn);

    await waitFor(() => {
      expect(api.submitGroupDeliverable).toHaveBeenCalledWith('grp-1', {
        submitted_by_candidate_id: 'cand-1',
        repo_url: 'https://github.com/excelr/analytics-alpha-v2',
        notes: 'Fixed all lint errors and added unit test suite.',
      });
    });

    // Open review form on attempt #1
    const openReviewBtn = screen.getByText('Review Submission');
    fireEvent.click(openReviewBtn);

    // Submit review
    const feedbackInput = screen.getByPlaceholderText(/Provide actionable code quality/i);
    fireEvent.change(feedbackInput, { target: { value: 'Excellent modular structure and clean data modeling.' } });

    const submitReviewBtn = screen.getByRole('button', { name: /Submit Review/i });
    fireEvent.click(submitReviewBtn);

    await waitFor(() => {
      expect(api.reviewGroupSubmission).toHaveBeenCalledWith('grp-1', 'sub-1', {
        status: 'APPROVED',
        score: 85,
        feedback: 'Excellent modular structure and clean data modeling.',
      });
    });
  });
});
