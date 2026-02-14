import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import VideoPlayer from './VideoPlayer';

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

// Mock the Icons component
jest.mock('./Icons', () => ({
  CloseIcon: () => <span data-testid="close-icon">Close</span>,
  PlayIcon: () => <span data-testid="play-icon">Play</span>,
  PauseIcon: () => <span data-testid="pause-icon">Pause</span>,
  VolumeIcon: () => <span data-testid="volume-icon">Volume</span>,
  VolumeOffIcon: () => <span data-testid="volume-off-icon">Muted</span>,
  FullscreenIcon: () => <span data-testid="fullscreen-icon">Fullscreen</span>,
  ArrowBackIcon: () => <span data-testid="arrow-back-icon">Back</span>,
  WarningIcon: () => <span data-testid="warning-icon">Warning</span>,
  AnalyticsIcon: () => <span data-testid="analytics-icon">Analytics</span>,
}));

// Mock hooks and components that VideoPlayer depends on

jest.mock('../hooks/useVideoUrl', () => ({
  useVideoUrl: ({ videoUrl }: { videoUrl: string }) => ({
    resolvedUrl: videoUrl,
    isLoading: false,
    error: null,
  }),
}));

jest.mock('../hooks/useVideos', () => ({
  useVideoMetadata: () => ({
    data: undefined,
  }),
}));

jest.mock('../hooks/useServeAttempts', () => ({
  useServeAttempts: () => ({
    serveAttempts: [],
    updateServeAttempt: jest.fn(),
    deleteServeAttempt: jest.fn(),
    createServeAttempt: jest.fn(),
  }),
}));

jest.mock('./AddServeAttemptButton', () => {
  return function MockAddServeAttemptButton() {
    return <div data-testid="add-serve-attempt-button">Add Serve Attempt</div>;
  };
});

jest.mock('./ServeAttemptRange', () => {
  return function MockServeAttemptRange() {
    return <div data-testid="serve-attempt-range">Serve Attempt Range</div>;
  };
});

jest.mock('./ServeAttemptModal', () => {
  return function MockServeAttemptModal() {
    return <div data-testid="serve-attempt-modal">Serve Attempt Modal</div>;
  };
});

jest.mock('./VideoOverlay', () => {
  return function MockVideoOverlay() {
    return <div data-testid="video-overlay">Overlay</div>;
  };
});

jest.mock('../services/api', () => ({
  videoApi: {
    getVideo: jest.fn(),
  },
}));

describe('VideoPlayer', () => {
  const defaultProps = {
    videoUrl: 'http://example.com/test-video.mp4',
    title: 'Test Video',
    showControls: true,
  };

  beforeEach(() => {
    // Mock console.log to reduce noise in tests
    jest.spyOn(console, 'log').mockImplementation(() => {});
    // Clear query cache before each test
    queryClient.clear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders video player with correct video source', () => {
      renderWithProviders(<VideoPlayer {...defaultProps} />);

      const video = screen.getByTestId('video-element');
      expect(video).toBeInTheDocument();
      expect(video).toHaveAttribute('src', defaultProps.videoUrl);
    });

    it('renders video title when onClose is provided', () => {
      const onCloseMock = jest.fn();
      renderWithProviders(
        <VideoPlayer {...defaultProps} onClose={onCloseMock} />
      );

      expect(screen.getByText(defaultProps.title)).toBeInTheDocument();
      expect(screen.getByTestId('close-icon')).toBeInTheDocument();
    });

    it('does not render header when onClose is not provided', () => {
      renderWithProviders(<VideoPlayer {...defaultProps} />);

      expect(screen.queryByText(defaultProps.title)).not.toBeInTheDocument();
      expect(screen.queryByTestId('close-icon')).not.toBeInTheDocument();
    });

    it('shows play overlay by default', () => {
      renderWithProviders(<VideoPlayer {...defaultProps} />);

      const playIcons = screen.getAllByTestId('play-icon');
      expect(playIcons.length).toBeGreaterThan(0);
    });
  });

  describe('Controls', () => {
    it('renders video controls when showControls is true', () => {
      renderWithProviders(
        <VideoPlayer {...defaultProps} showControls={true} />
      );

      const sliders = screen.getAllByRole('slider');
      expect(sliders.length).toBeGreaterThan(0);
      expect(screen.getByTestId('volume-icon')).toBeInTheDocument();
      expect(screen.getByTestId('fullscreen-icon')).toBeInTheDocument();
    });

    it('does not render controls when showControls is false', () => {
      renderWithProviders(
        <VideoPlayer {...defaultProps} showControls={false} />
      );

      expect(screen.queryByRole('slider')).not.toBeInTheDocument();
      expect(screen.queryByTestId('volume-icon')).not.toBeInTheDocument();
    });

    it('calls onClose when close button is clicked', () => {
      const onCloseMock = jest.fn();

      renderWithProviders(
        <VideoPlayer {...defaultProps} onClose={onCloseMock} />
      );

      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);
      expect(onCloseMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('Video Element', () => {
    it('has correct video attributes', () => {
      renderWithProviders(<VideoPlayer {...defaultProps} />);

      const video = screen.getByTestId('video-element');
      expect(video).toHaveAttribute('preload', 'metadata');
      expect(video).toHaveAttribute('src', defaultProps.videoUrl);
      expect(video).toHaveClass('video-element');
    });

    it('handles play and pause events', () => {
      renderWithProviders(<VideoPlayer {...defaultProps} />);

      const video = screen.getByTestId('video-element');

      // Simulate play event
      fireEvent.play(video);

      // Simulate pause event
      fireEvent.pause(video);

      // Component should handle these events without errors
      expect(video).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('video element is accessible', () => {
      renderWithProviders(<VideoPlayer {...defaultProps} />);

      const video = screen.getByTestId('video-element');
      expect(video).toBeInTheDocument();
    });

    it('close button is accessible when provided', () => {
      const onCloseMock = jest.fn();
      renderWithProviders(
        <VideoPlayer {...defaultProps} onClose={onCloseMock} />
      );

      const closeButton = screen.getByRole('button', { name: /close/i });
      expect(closeButton).toBeInTheDocument();
    });
  });

  describe('Event Handling', () => {
    it('handles video load event', () => {
      renderWithProviders(<VideoPlayer {...defaultProps} />);

      const video = screen.getByTestId('video-element');
      fireEvent.loadedMetadata(video);

      expect(video).toBeInTheDocument();
    });

    it('handles video error event', () => {
      renderWithProviders(<VideoPlayer {...defaultProps} />);

      const video = screen.getByTestId('video-element');
      fireEvent.error(video);

      expect(video).toBeInTheDocument();
    });
  });
});
