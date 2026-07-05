import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { renderWithProviders } from '../test-utils';
import { VideoMetadata } from '../types/video';
import VideoList from './VideoList';

// --- Mocks ---

// Mock Icons
vi.mock('./Icons', () => ({
  CloseIcon: () => <span data-testid="close-icon">Close</span>,
  DeleteIcon: () => <span data-testid="delete-icon">Delete</span>,
  UploadIcon: () => <span data-testid="upload-icon">Upload</span>,
  VideoIcon: () => <span data-testid="video-icon">Video</span>,
}));

// Mock child components
vi.mock('./VideoUpload', () => {
  return {
    default: function MockVideoUpload() {
      return <div data-testid="video-upload">Video Upload Form</div>;
    },
  };
});

vi.mock('./VideoEditModal', () => {
  return {
    default: function MockVideoEditModal({
      onClose,
    }: {
      video: VideoMetadata;
      onClose: () => void;
    }) {
      return (
        <div data-testid="video-edit-modal">
          <button onClick={onClose}>Close Edit</button>
        </div>
      );
    },
  };
});

vi.mock('./VideoFilters', () => {
  return {
    default: function MockVideoFilters({
      onChange,
    }: {
      filters: Record<string, unknown>;
      onChange: (f: Record<string, unknown>) => void;
    }) {
      return (
        <div data-testid="video-filters">
          <button onClick={() => onChange({ camera_angle: 'behind' })}>
            Filter Behind
          </button>
          <button onClick={() => onChange({})}>Clear filters</button>
        </div>
      );
    },
  };
});

vi.mock('./VideoFilters.css', () => ({}));

vi.mock('./LoadingIndicator', () => {
  return {
    default: function MockLoadingIndicator({ label }: { label?: string }) {
      return <div data-testid="loading-indicator">{label ?? 'Loading...'}</div>;
    },
  };
});

// Mock CSS import
vi.mock('./VideoList.css', () => ({}));

// Hook mocks — default return values, overridden per test as needed
const mockMutateAsync = vi.fn();
const mockRefetch = vi.fn();

const mockUseVideos = vi.fn();
const mockUseVideoAnalysisStatuses = vi.fn();
const mockUseDeleteVideo = vi.fn();
const mockUseUpdateVideoMetadata = vi.fn();

vi.mock('../hooks/useVideos', () => ({
  useVideos: (...args: unknown[]) => mockUseVideos(...args),
  useVideoAnalysisStatuses: (...args: unknown[]) =>
    mockUseVideoAnalysisStatuses(...args),
  useDeleteVideo: (...args: unknown[]) => mockUseDeleteVideo(...args),
  useUpdateVideoMetadata: (...args: unknown[]) =>
    mockUseUpdateVideoMetadata(...args),
}));

const mockUsePlayerProfile = vi.fn();

vi.mock('../hooks/usePlayerProfile', () => ({
  usePlayerProfile: (...args: unknown[]) => mockUsePlayerProfile(...args),
}));

// --- Test data ---

const mockVideos: VideoMetadata[] = [
  {
    id: 1,
    filename: 'serve_practice_1.mp4',
    file_path: '/videos/serve_practice_1.mp4',
    file_size: 5242880, // 5 MB
    created_at: new Date().toISOString(), // "Today"
    status: 'completed',
    primary_player_id: 10,
  },
  {
    id: 2,
    filename: 'match_clip.mp4',
    file_path: '/videos/match_clip.mp4',
    file_size: 10485760, // 10 MB
    created_at: '2024-06-15T10:00:00Z',
    recorded_at: '2024-06-15T09:30:00Z',
    status: 'completed',
    primary_player_id: null,
  },
];

// --- Helpers ---

function setDefaultMocks({
  videos = mockVideos,
  videosLoading = false,
  videosError = null as Error | null,
  statusesLoading = false,
  playerProfile = { id: 10, name: 'Alice' } as {
    id: number;
    name: string;
  } | null,
  deletePending = false,
  updatePending = false,
} = {}) {
  mockUseVideos.mockReturnValue({
    data: videos,
    isLoading: videosLoading,
    error: videosError,
    refetch: mockRefetch,
  });

  mockUseVideoAnalysisStatuses.mockReturnValue({
    isLoading: statusesLoading,
  });

  mockUsePlayerProfile.mockReturnValue({
    data: playerProfile,
  });

  mockUseDeleteVideo.mockReturnValue({
    mutateAsync: mockMutateAsync,
    isPending: deletePending,
  });

  mockUseUpdateVideoMetadata.mockReturnValue({
    isPending: updatePending,
  });
}

// --- Tests ---

describe('VideoList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setDefaultMocks();
  });

  describe('Loading state', () => {
    it('shows loading indicator when videos are loading', () => {
      setDefaultMocks({ videosLoading: true });

      renderWithProviders(<VideoList />);

      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
      expect(
        screen.getByText('Rounding up your videos...')
      ).toBeInTheDocument();
    });

    it('shows loading indicator when analysis statuses are loading', () => {
      setDefaultMocks({ statusesLoading: true });

      renderWithProviders(<VideoList />);

      expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('shows error message and retry button when videos fail to load', () => {
      setDefaultMocks({ videosError: new Error('Network error') });

      renderWithProviders(<VideoList />);

      expect(
        screen.getByText('Failed to load videos. Please try again.')
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /try again/i })
      ).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', async () => {
      const user = userEvent.setup();
      setDefaultMocks({ videosError: new Error('Network error') });

      renderWithProviders(<VideoList />);

      await user.click(screen.getByRole('button', { name: /try again/i }));
      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Empty state', () => {
    it('shows empty state when there are no videos', () => {
      setDefaultMocks({ videos: [] });

      renderWithProviders(<VideoList />);

      expect(screen.getByText('No videos uploaded yet')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Upload your first tennis video to get started with analysis'
        )
      ).toBeInTheDocument();
    });

    it('still shows header with upload button when empty', () => {
      setDefaultMocks({ videos: [] });

      renderWithProviders(<VideoList />);

      expect(screen.getByText('Video Library')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /upload/i })
      ).toBeInTheDocument();
    });
  });

  describe('Rendering video cards', () => {
    it('renders a card for each video with filename', () => {
      renderWithProviders(<VideoList />);

      expect(screen.getByText('serve_practice_1.mp4')).toBeInTheDocument();
      expect(screen.getByText('match_clip.mp4')).toBeInTheDocument();
    });

    it('shows formatted file size on each card', () => {
      renderWithProviders(<VideoList />);

      expect(screen.getByText('5.00 MB')).toBeInTheDocument();
      expect(screen.getByText('10.00 MB')).toBeInTheDocument();
    });

    it('shows video count in header', () => {
      renderWithProviders(<VideoList />);

      expect(screen.getByText('2 sessions')).toBeInTheDocument();
    });

    it('shows "You" badge only when primary_player_id matches the profile', () => {
      renderWithProviders(<VideoList />);

      // Only video 1 matches by id; video 2 is untagged and gets no badge
      const labels = screen.getAllByText('You');
      expect(labels).toHaveLength(1);
    });

    it('shows no player badge for untagged videos', () => {
      // Untagged (primary_player_id null/undefined) means "we don't know",
      // not "you" — no badge should render.
      const untaggedOnly: VideoMetadata[] = [
        { ...mockVideos[1], primary_player_id: null },
      ];
      setDefaultMocks({ videos: untaggedOnly });

      renderWithProviders(<VideoList />);

      expect(screen.queryByText('You')).not.toBeInTheDocument();
      expect(screen.queryByText('Someone Else')).not.toBeInTheDocument();
    });

    it('shows no player badge when player profile is not available', () => {
      setDefaultMocks({ playerProfile: null });

      renderWithProviders(<VideoList />);

      expect(screen.queryByText('You')).not.toBeInTheDocument();
      expect(screen.queryByText('Someone Else')).not.toBeInTheDocument();
    });

    it('shows "Someone Else" when primary_player_id does not match profile', () => {
      // Profile id = 10, second video has primary_player_id = null (handled differently),
      // so set a video where primary_player_id is a different non-null value
      const videosWithOther: VideoMetadata[] = [
        {
          ...mockVideos[0],
          primary_player_id: 999, // does not match profile id 10
        },
      ];
      setDefaultMocks({ videos: videosWithOther });

      renderWithProviders(<VideoList />);

      expect(screen.getByText('Someone Else')).toBeInTheDocument();
    });
  });

  describe('Delete interaction', () => {
    it('calls deleteVideo mutation when delete button is clicked', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue(undefined);

      renderWithProviders(<VideoList />);

      const deleteButtons = screen.getAllByTitle('Delete');
      await user.click(deleteButtons[0]);

      expect(mockMutateAsync).toHaveBeenCalledWith(1);
    });

    it('calls onVideoDeleted callback after successful deletion', async () => {
      const user = userEvent.setup();
      const onVideoDeleted = vi.fn();
      mockMutateAsync.mockResolvedValue(undefined);

      renderWithProviders(<VideoList onVideoDeleted={onVideoDeleted} />);

      const deleteButtons = screen.getAllByTitle('Delete');
      await user.click(deleteButtons[0]);

      expect(onVideoDeleted).toHaveBeenCalledTimes(1);
    });

    it('disables delete buttons when deletion is pending', () => {
      setDefaultMocks({ deletePending: true });

      renderWithProviders(<VideoList />);

      const deleteButtons = screen.getAllByTitle('Delete');
      deleteButtons.forEach((btn) => {
        expect(btn).toBeDisabled();
      });
    });

    it('does not propagate click to card when delete is clicked', async () => {
      const user = userEvent.setup();
      const onViewAnalysis = vi.fn();
      mockMutateAsync.mockResolvedValue(undefined);

      renderWithProviders(<VideoList onViewAnalysis={onViewAnalysis} />);

      const deleteButtons = screen.getAllByTitle('Delete');
      await user.click(deleteButtons[0]);

      // onViewAnalysis should NOT have been called because stopPropagation
      expect(onViewAnalysis).not.toHaveBeenCalled();
    });
  });

  describe('Video selection (view analysis)', () => {
    it('calls onViewAnalysis with the video when card is clicked', async () => {
      const user = userEvent.setup();
      const onViewAnalysis = vi.fn();

      renderWithProviders(<VideoList onViewAnalysis={onViewAnalysis} />);
      const firstCard = screen
        .getByText('serve_practice_1.mp4')
        .closest('.video-card') as HTMLElement;
      await user.click(firstCard);

      expect(onViewAnalysis).toHaveBeenCalledTimes(1);
      expect(onViewAnalysis).toHaveBeenCalledWith(mockVideos[0]);
    });

    it('does not throw when card is clicked without onViewAnalysis prop', async () => {
      const user = userEvent.setup();

      renderWithProviders(<VideoList />);
      const firstCard = screen
        .getByText('serve_practice_1.mp4')
        .closest('.video-card') as HTMLElement;

      // Should not throw
      await user.click(firstCard);
    });
  });

  describe('Upload modal', () => {
    it('opens upload modal when Upload button is clicked', async () => {
      const user = userEvent.setup();

      renderWithProviders(<VideoList />);

      expect(screen.queryByTestId('video-upload')).not.toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /upload/i }));

      expect(screen.getByTestId('video-upload')).toBeInTheDocument();
      expect(screen.getByText('Upload Video')).toBeInTheDocument();
    });

    it('closes upload modal when close button is clicked', async () => {
      const user = userEvent.setup();

      renderWithProviders(<VideoList />);

      await user.click(screen.getByRole('button', { name: /upload/i }));
      expect(screen.getByTestId('video-upload')).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /close/i }));
      expect(screen.queryByTestId('video-upload')).not.toBeInTheDocument();
    });
  });

  describe('Filtering', () => {
    it('renders filter component', () => {
      renderWithProviders(<VideoList />);
      expect(screen.getByTestId('video-filters')).toBeInTheDocument();
    });

    it('shows "matching sessions" when filters are active', async () => {
      const user = userEvent.setup();
      renderWithProviders(<VideoList />);

      await user.click(screen.getByText('Filter Behind'));

      expect(screen.getByText(/matching sessions/)).toBeInTheDocument();
    });

    it('shows normal count when filters are cleared', async () => {
      const user = userEvent.setup();
      renderWithProviders(<VideoList />);

      await user.click(screen.getByText('Filter Behind'));
      await user.click(screen.getByText('Clear filters'));

      expect(screen.getByText('2 sessions')).toBeInTheDocument();
    });

    it('passes filters to useVideos hook', async () => {
      const user = userEvent.setup();
      renderWithProviders(<VideoList />);

      await user.click(screen.getByText('Filter Behind'));

      // useVideos should have been called with the filter
      expect(mockUseVideos).toHaveBeenCalledWith(
        expect.objectContaining({ camera_angle: 'behind' })
      );
    });
  });

  describe('Edit modal', () => {
    it('opens edit modal when Edit button is clicked', async () => {
      const user = userEvent.setup();

      renderWithProviders(<VideoList />);

      const editButtons = screen.getAllByTitle('Edit');
      await user.click(editButtons[0]);

      expect(screen.getByTestId('video-edit-modal')).toBeInTheDocument();
    });

    it('does not propagate click to card when edit is clicked', async () => {
      const user = userEvent.setup();
      const onViewAnalysis = vi.fn();

      renderWithProviders(<VideoList onViewAnalysis={onViewAnalysis} />);

      const editButtons = screen.getAllByTitle('Edit');
      await user.click(editButtons[0]);

      expect(onViewAnalysis).not.toHaveBeenCalled();
    });

    it('disables edit buttons when update mutation is pending', () => {
      setDefaultMocks({ updatePending: true });

      renderWithProviders(<VideoList />);

      const editButtons = screen.getAllByTitle('Edit');
      editButtons.forEach((btn) => {
        expect(btn).toBeDisabled();
      });
    });
  });
});
