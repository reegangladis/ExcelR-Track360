import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from '../src/app/App';

// Mock API responses for test environment
vi.mock('../src/lib/api', () => ({
  api: {
    getHealth: vi.fn().mockResolvedValue({
      status: 'healthy',
      app_name: 'ExcelR Track360',
      environment: 'test',
      version: '0.1.0',
      uptime_seconds: 42,
      timestamp: '2026-10-24T12:00:00Z',
    }),
    getReadiness: vi.fn().mockResolvedValue({
      status: 'ready',
      environment: 'test',
      database: { status: 'connected', latency_ms: 1.2 },
      dependencies: { database: 'healthy' },
      timestamp: '2026-10-24T12:00:00Z',
    }),
    getMe: vi.fn().mockRejectedValue(new Error('Unauthenticated')),
  },
}));

describe('App Component', () => {
  it('renders application brand title and navigation', async () => {
    render(<App />);
    
    // Check brand presence
    const brandElements = await screen.findAllByText(/Track360/i);
    expect(brandElements.length).toBeGreaterThan(0);
    
    // Check navigation items
    expect(screen.getByText('Candidates')).toBeInTheDocument();
    expect(screen.getByText('Assignments')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
  });

  it('renders hero tagline and platform description', async () => {
    render(<App />);
    
    const taglines = screen.getAllByText(/Track Every Student. Every Assignment. Every Milestone./i);
    expect(taglines.length).toBeGreaterThan(0);
  });
});
