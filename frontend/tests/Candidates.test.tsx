import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CandidatesPage } from '../src/pages/CandidatesPage';
import { api } from '../src/lib/api';

vi.mock('../src/lib/api', () => ({
  api: {
    getCandidates: vi.fn(),
    getBatches: vi.fn(),
    createCandidate: vi.fn(),
    transitionCandidateStatus: vi.fn(),
    previewCandidateImport: vi.fn(),
    commitCandidateImport: vi.fn(),
  },
}));

const mockCandidates = [
  {
    id: 'c1',
    candidate_number: 'EX-2026-0001',
    first_name: 'John',
    last_name: 'Doe',
    email: 'john.doe@example.com',
    phone: '+919876543210',
    lifecycle_status: 'ACTIVE',
    project_eligible: true,
    completed_projects_count: 0,
    academic_qualification: 'B.Tech CS',
    batch_code: 'DA-2026-B1',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'c2',
    candidate_number: 'EX-2026-0002',
    first_name: 'Jane',
    last_name: 'Smith',
    email: 'jane.smith@example.com',
    phone: '+919876543211',
    lifecycle_status: 'ENROLLED',
    project_eligible: false,
    completed_projects_count: 0,
    academic_qualification: 'MCA',
    batch_code: 'DA-2026-B1',
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
];

const mockBatches = [
  {
    id: 'b1',
    track_id: 't1',
    batch_code: 'DA-2026-B1',
    title: 'Data Analytics Cohort 1',
    start_date: '2026-01-01',
    status: 'ACTIVE',
  },
];

describe('CandidatesPage Component', () => {
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

    vi.mocked(api.getCandidates).mockResolvedValue({
      items: mockCandidates,
      total: 2,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });

    vi.mocked(api.getBatches).mockResolvedValue(mockBatches);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <CandidatesPage />
      </QueryClientProvider>
    );

  it('renders page header and action buttons', async () => {
    renderComponent();

    expect(screen.getByText('Candidate Lifecycle Management')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add Candidate/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Bulk CSV Import/i })).toBeInTheDocument();
  });

  it('displays candidate records from api query', async () => {
    renderComponent();

    expect(await screen.findByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('EX-2026-0001')).toBeInTheDocument();
    expect(screen.getByText('john.doe@example.com')).toBeInTheDocument();

    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('EX-2026-0002')).toBeInTheDocument();
  });

  it('opens and closes Add Candidate modal', async () => {
    renderComponent();

    const addBtn = screen.getByRole('button', { name: /Add Candidate/i });
    fireEvent.click(addBtn);

    expect(screen.getByText('Enroll Single Candidate')).toBeInTheDocument();
    expect(screen.getByLabelText(/First Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText('Enroll Single Candidate')).not.toBeInTheDocument();
  });

  it('opens and closes Bulk CSV Import modal', async () => {
    renderComponent();

    const importBtn = screen.getByRole('button', { name: /Bulk CSV Import/i });
    fireEvent.click(importBtn);

    expect(screen.getByText(/Bulk Candidate Ingestion/i)).toBeInTheDocument();
    expect(screen.getByText('Choose CSV roster to upload')).toBeInTheDocument();

    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText(/Bulk Candidate Ingestion/i)).not.toBeInTheDocument();
  });
});
