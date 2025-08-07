import React from 'react';
import { render, screen } from '@testing-library/react';

// Mock the API service to avoid axios import issues
jest.mock('./services/api', () => ({
  videoApi: {
    uploadVideo: jest.fn(),
    getVideos: jest.fn(),
    getVideo: jest.fn(),
    deleteVideo: jest.fn(),
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

import App from './App';

test('renders tennis analysis app title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Tennis Analysis System/i);
  expect(titleElement).toBeInTheDocument();
});

test('renders upload section', () => {
  render(<App />);
  const uploadElement = screen.getByTestId('video-upload');
  expect(uploadElement).toBeInTheDocument();
});

test('renders video list section', () => {
  render(<App />);
  const listElement = screen.getByTestId('video-list');
  expect(listElement).toBeInTheDocument();
});

test('renders footer with phase info', () => {
  render(<App />);
  const footerElement = screen.getByText(/Phase 3/i);
  expect(footerElement).toBeInTheDocument();
});
