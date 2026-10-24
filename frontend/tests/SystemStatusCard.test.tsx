import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SystemStatusCard } from '../src/components/SystemStatusCard';

vi.mock('../src/lib/api', () => ({
  api: {
    getHealth: vi.fn().mockResolvedValue({
      status: 'healthy',
      app_name: 'ExcelR Track360',
      environment: 'test',
      version: '0.1.0',
      uptime_seconds: 120,
      timestamp: '2026-10-24T12:00:00Z',
    }),
    getReadiness: vi.fn().mockResolvedValue({
      status: 'ready',
      environment: 'test',
      database: { status: 'connected', latency_ms: 2.5 },
      dependencies: { database: 'healthy' },
      timestamp: '2026-10-24T12:00:00Z',
    }),
  },
}));

describe('SystemStatusCard Component', () => {
  it('renders system status card heading and refresh button', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SystemStatusCard />
      </QueryClientProvider>
    );

    expect(screen.getByText('System Foundation Status')).toBeInTheDocument();
    expect(screen.getByText('Refresh')).toBeInTheDocument();
    expect(screen.getByText(/FastAPI Backend/i)).toBeInTheDocument();
    expect(screen.getByText(/PostgreSQL Database/i)).toBeInTheDocument();
  });
});
