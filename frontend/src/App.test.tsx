import { render, screen } from '@testing-library/react';
import App from './App';

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

test('renders tennis analysis app title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Tennis Video Analyzer/i);
  expect(titleElement).toBeInTheDocument();
});

test('renders upload section', () => {
  render(<App />);
  const uploadElement = screen.getByTestId('video-upload');
  expect(uploadElement).toBeInTheDocument();
});

test('renders video library button', () => {
  render(<App />);
  const videoLibraryButton = screen.getByText(/Video Library/i);
  expect(videoLibraryButton).toBeInTheDocument();
});

test('renders app subtitle', () => {
  render(<App />);
  const subtitleElement = screen.getByText(
    /Upload your tennis videos for advanced performance analysis/i
  );
  expect(subtitleElement).toBeInTheDocument();
});
