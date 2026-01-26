import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import React from 'react';
import App from './App';

// Mock localStorage BEFORE importing App to prevent demo landing
const localStorageMock = {
  getItem: jest.fn(() => 'true'), // hasVisitedApp = true
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

// Mock the useAuth hook to avoid async loading state
jest.mock('./hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: 'test-user-id',
      email: 'test@example.com',
    },
    loading: false,
    signOut: jest.fn(),
  }),
}));

// Mock the API service to avoid axios import issues
jest.mock('./services/api', () => ({
  videoApi: {
    uploadVideo: jest.fn(),
    getVideos: jest.fn(),
    getVideo: jest.fn(),
    getDemoVideo: jest.fn(),
    deleteVideo: jest.fn(),
    streamVideo: jest.fn(),
    streamAnnotatedVideo: jest.fn(),
    getVideoUrl: jest.fn(),
  },
  analysisApi: {
    startAnalysis: jest.fn(),
  },
}));

// Mock the components that use the API
jest.mock('./components/VideoUpload', () => {
  return function MockVideoUpload() {
    return <div data-testid="video-upload">Upload Tennis Video</div>;
  };
});

jest.mock('./components/VideoList', () => {
  return function MockVideoList() {
    return <div data-testid="video-list">Uploaded Videos</div>;
  };
});

jest.mock('./components/AnalysisDashboard', () => {
  return function MockAnalysisDashboard() {
    return <div data-testid="analysis-dashboard">Analysis Dashboard</div>;
  };
});

jest.mock('./components/DemoLanding', () => {
  return function MockDemoLanding() {
    return <div data-testid="demo-landing">Demo Landing</div>;
  };
});

jest.mock('./components/DemoDashboard', () => {
  return function MockDemoDashboard() {
    return <div data-testid="demo-dashboard">Demo Dashboard</div>;
  };
});

test('renders tennis coach app title', () => {
  renderWithProviders(<App />);
  const titleElement = screen.getByText(/Tennis Coach/i);
  expect(titleElement).toBeInTheDocument();
});

test('renders demo landing by default', () => {
  renderWithProviders(<App />);
  // App shows demo landing by default
  const demoLanding = screen.getByTestId('demo-landing');
  expect(demoLanding).toBeInTheDocument();
});

test('renders library button', () => {
  renderWithProviders(<App />);
  const libraryButton = screen.getByText(/Library/i);
  expect(libraryButton).toBeInTheDocument();
});

test('renders app content', () => {
  renderWithProviders(<App />);
  // App shows demo landing by default
  const demoLanding = screen.getByTestId('demo-landing');
  expect(demoLanding).toBeInTheDocument();
});
