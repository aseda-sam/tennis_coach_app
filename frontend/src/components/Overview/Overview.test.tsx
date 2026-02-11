import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import Overview from './Overview';

// Mock the useProgress hook
const mockUseProgress = jest.fn();
jest.mock('../../hooks/useProgress', () => ({
  useProgress: (...args: unknown[]) => mockUseProgress(...args),
}));

// Mock recharts to avoid SVG rendering issues in tests
jest.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderOverview = () =>
  render(
    <QueryClientProvider client={queryClient}>
      <Overview />
    </QueryClientProvider>
  );

const MOCK_PROGRESS = {
  time_period: '30d',
  total_serves: 20,
  total_videos: 3,
  metrics: {
    elbow_angle: {
      current_avg: 152.5,
      previous_avg: 148.0,
      trend: 'improving' as const,
      consistency: 6.1,
      consistency_rating: 'good' as const,
      data_points: [
        { date: '2026-01-20', avg: 148.0, count: 5 },
        { date: '2026-01-27', avg: 152.0, count: 8 },
        { date: '2026-02-03', avg: 155.0, count: 7 },
      ],
    },
    knee_bend: {
      current_rate: 0.85,
      previous_rate: 0.72,
      trend: 'improving' as const,
      data_points: [
        { date: '2026-01-20', avg: 0.72, count: 5 },
        { date: '2026-01-27', avg: 0.85, count: 8 },
      ],
    },
  },
  court_side: {
    deuce: 12,
    ad: 8,
    unknown: 0,
  },
};

describe('Overview', () => {
  beforeEach(() => {
    mockUseProgress.mockReset();
  });

  it('renders loading state', () => {
    mockUseProgress.mockReturnValue({
      progress: null,
      loading: true,
      error: null,
    });

    renderOverview();
    expect(screen.getByText(/Loading progress/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseProgress.mockReturnValue({
      progress: null,
      loading: false,
      error: 'Something went wrong',
    });

    renderOverview();
    expect(
      screen.getByText(/Failed to load progress data/i)
    ).toBeInTheDocument();
  });

  it('renders empty state when less than 2 videos', () => {
    mockUseProgress.mockReturnValue({
      progress: { ...MOCK_PROGRESS, total_videos: 1 },
      loading: false,
      error: null,
    });

    renderOverview();
    expect(screen.getByText(/Upload a few more serves/i)).toBeInTheDocument();
  });

  it('renders metric cards with data', () => {
    mockUseProgress.mockReturnValue({
      progress: MOCK_PROGRESS,
      loading: false,
      error: null,
    });

    renderOverview();
    // "Elbow Angle" appears in both MetricCard and ConsistencyReport
    expect(screen.getAllByText('Elbow Angle').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Knee Bend Rate')).toBeInTheDocument();
  });

  it('renders serve count summary', () => {
    mockUseProgress.mockReturnValue({
      progress: MOCK_PROGRESS,
      loading: false,
      error: null,
    });

    renderOverview();
    expect(screen.getByText(/20 serves across 3 videos/i)).toBeInTheDocument();
  });

  it('renders trend chart', () => {
    mockUseProgress.mockReturnValue({
      progress: MOCK_PROGRESS,
      loading: false,
      error: null,
    });

    renderOverview();
    expect(screen.getByText('Elbow Angle Over Time')).toBeInTheDocument();
  });

  it('renders court side diagram', () => {
    mockUseProgress.mockReturnValue({
      progress: MOCK_PROGRESS,
      loading: false,
      error: null,
    });

    renderOverview();
    expect(screen.getByText('Court Side Distribution')).toBeInTheDocument();
  });

  it('renders consistency report', () => {
    mockUseProgress.mockReturnValue({
      progress: MOCK_PROGRESS,
      loading: false,
      error: null,
    });

    renderOverview();
    expect(screen.getByText('Consistency Report')).toBeInTheDocument();
  });

  it('time filter changes period', () => {
    mockUseProgress.mockReturnValue({
      progress: MOCK_PROGRESS,
      loading: false,
      error: null,
    });

    renderOverview();

    // Initially called with default '30d'
    expect(mockUseProgress).toHaveBeenCalledWith('30d');

    // Click 7 days filter
    fireEvent.click(screen.getByText('Last 7 Days'));
    expect(mockUseProgress).toHaveBeenCalledWith('7d');

    // Click all time filter
    fireEvent.click(screen.getByText('All Time'));
    expect(mockUseProgress).toHaveBeenCalledWith('all');
  });

  it('renders page title', () => {
    mockUseProgress.mockReturnValue({
      progress: MOCK_PROGRESS,
      loading: false,
      error: null,
    });

    renderOverview();
    expect(screen.getByText('Progress Overview')).toBeInTheDocument();
  });
});
