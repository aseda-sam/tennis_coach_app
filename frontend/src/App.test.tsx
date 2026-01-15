import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

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

// Mock the API service to avoid axios import issues
jest.mock('./services/api', () => ({
  videoApi: {
    uploadVideo: jest.fn(),
    getVideos: jest.fn(),
    getVideo: jest.fn(),
    deleteVideo: jest.fn(),
    streamVideo: jest.fn(),
    streamAnnotatedVideo: jest.fn(),
  },
  analysisApi: {
    startAnalysis: jest.fn(),
    getAnalysis: jest.fn(),
    getAllAnalyses: jest.fn(),
    deleteAnalysis: jest.fn(),
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

test('renders tennis coach app title', () => {
  renderWithProviders(<App />);
  const titleElement = screen.getByText(/Tennis Coach/i);
  expect(titleElement).toBeInTheDocument();
});

test('renders upload section', () => {
  renderWithProviders(<App />);
  const uploadElement = screen.getByTestId('video-upload');
  expect(uploadElement).toBeInTheDocument();
});

test('renders library button', () => {
  renderWithProviders(<App />);
  const libraryButton = screen.getByText(/Library/i);
  expect(libraryButton).toBeInTheDocument();
});

test('renders app subtitle', () => {
  renderWithProviders(<App />);
  const subtitleElement = screen.getByText(
    /Upload your tennis video and get personalized feedback/i
  );
  expect(subtitleElement).toBeInTheDocument();
});
