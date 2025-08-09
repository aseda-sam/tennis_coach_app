import { fireEvent, render, screen } from '@testing-library/react';
import VideoPlayer from './VideoPlayer';

// Mock the Icons component
jest.mock('./Icons', () => ({
  CloseIcon: () => <span data-testid="close-icon">Close</span>,
  PlayIcon: () => <span data-testid="play-icon">Play</span>,
  PauseIcon: () => <span data-testid="pause-icon">Pause</span>,
  VolumeIcon: () => <span data-testid="volume-icon">Volume</span>,
  VolumeOffIcon: () => <span data-testid="volume-off-icon">Muted</span>,
  FullscreenIcon: () => <span data-testid="fullscreen-icon">Fullscreen</span>,
}));

describe('VideoPlayer', () => {
  const defaultProps = {
    videoUrl: 'http://example.com/test-video.mp4',
    title: 'Test Video Title',
  };

  beforeEach(() => {
    // Mock HTMLVideoElement methods
    Object.defineProperty(HTMLVideoElement.prototype, 'play', {
      writable: true,
      value: jest.fn().mockImplementation(() => Promise.resolve()),
    });
    Object.defineProperty(HTMLVideoElement.prototype, 'pause', {
      writable: true,
      value: jest.fn(),
    });
  });

  describe('Basic Rendering', () => {
    it('renders video player with correct video source', () => {
      render(<VideoPlayer {...defaultProps} />);
      
      const video = document.querySelector('video');
      expect(video).toBeInTheDocument();
      expect(video).toHaveAttribute('src', defaultProps.videoUrl);
    });

    it('renders video title when onClose is provided', () => {
      const onCloseMock = jest.fn();
      render(<VideoPlayer {...defaultProps} onClose={onCloseMock} />);
      
      expect(screen.getByText(defaultProps.title)).toBeInTheDocument();
      expect(screen.getByTestId('close-icon')).toBeInTheDocument();
    });

    it('does not render header when onClose is not provided', () => {
      render(<VideoPlayer {...defaultProps} />);
      
      expect(screen.queryByText(defaultProps.title)).not.toBeInTheDocument();
      expect(screen.queryByTestId('close-icon')).not.toBeInTheDocument();
    });

    it('shows play overlay by default', () => {
      render(<VideoPlayer {...defaultProps} />);
      
      const playIcons = screen.getAllByTestId('play-icon');
      expect(playIcons.length).toBeGreaterThan(0);
    });
  });

  describe('Controls', () => {
    it('renders video controls when showControls is true', () => {
      render(<VideoPlayer {...defaultProps} showControls={true} />);
      
      const sliders = screen.getAllByRole('slider');
      expect(sliders.length).toBeGreaterThan(0);
      expect(screen.getByTestId('volume-icon')).toBeInTheDocument();
      expect(screen.getByTestId('fullscreen-icon')).toBeInTheDocument();
    });

    it('does not render controls when showControls is false', () => {
      render(<VideoPlayer {...defaultProps} showControls={false} />);
      
      expect(screen.queryByRole('slider')).not.toBeInTheDocument();
      expect(screen.queryByTestId('volume-icon')).not.toBeInTheDocument();
    });

    it('calls onClose when close button is clicked', () => {
      const onCloseMock = jest.fn();
      
      render(<VideoPlayer {...defaultProps} onClose={onCloseMock} />);
      
      const closeIcon = screen.getByTestId('close-icon');
      const closeButton = closeIcon.closest('button');
      
      if (closeButton) {
        fireEvent.click(closeButton);
        expect(onCloseMock).toHaveBeenCalledTimes(1);
      }
    });
  });

  describe('Video Element', () => {
    it('has correct video attributes', () => {
      render(<VideoPlayer {...defaultProps} />);
      
      const video = document.querySelector('video');
      expect(video).toHaveAttribute('preload', 'metadata');
      expect(video).toHaveAttribute('src', defaultProps.videoUrl);
      expect(video).toHaveClass('video-element');
    });

    it('handles play and pause events', () => {
      render(<VideoPlayer {...defaultProps} />);
      
      const video = document.querySelector('video');
      if (video) {
        // Simulate play event
        fireEvent.play(video);
        
        // Simulate pause event
        fireEvent.pause(video);
        
        // Component should handle these events without errors
        expect(video).toBeInTheDocument();
      }
    });
  });

  describe('Accessibility', () => {
    it('video element is accessible', () => {
      render(<VideoPlayer {...defaultProps} />);
      
      const video = document.querySelector('video');
      expect(video).toBeInTheDocument();
    });

    it('buttons are accessible', () => {
      render(<VideoPlayer {...defaultProps} onClose={jest.fn()} />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('sliders are accessible', () => {
      render(<VideoPlayer {...defaultProps} showControls={true} />);
      
      const sliders = screen.getAllByRole('slider');
      expect(sliders.length).toBeGreaterThan(0);
    });
  });
});