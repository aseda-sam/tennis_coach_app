import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { videoApi } from '../services/api';
import { useVideoUrl } from './useVideoUrl';

jest.mock('../services/api', () => ({
  videoApi: {
    getVideoUrl: jest.fn(),
  },
}));

const mockedGetVideoUrl = videoApi.getVideoUrl as jest.MockedFunction<
  typeof videoApi.getVideoUrl
>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe('useVideoUrl', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('when videoUrl contains /stream and videoId is provided', () => {
    it('returns the resolved signed URL from the API', async () => {
      mockedGetVideoUrl.mockResolvedValue(
        'https://storage.example.com/signed-video-url'
      );

      const { result } = renderHook(
        () =>
          useVideoUrl({
            videoId: 42,
            videoUrl: '/v0/videos/42/stream',
          }),
        { wrapper: createWrapper() }
      );

      // Initially loading
      expect(result.current.isLoading).toBe(true);
      expect(result.current.resolvedUrl).toBe('');

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.resolvedUrl).toBe(
        'https://storage.example.com/signed-video-url'
      );
      expect(result.current.error).toBeNull();
      expect(mockedGetVideoUrl).toHaveBeenCalledWith(42, 3600);
    });

    it('passes custom expiresIn to the API', async () => {
      mockedGetVideoUrl.mockResolvedValue('https://storage.example.com/url');

      const { result } = renderHook(
        () =>
          useVideoUrl({
            videoId: 10,
            videoUrl: '/v0/videos/10/stream',
            expiresIn: 7200,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockedGetVideoUrl).toHaveBeenCalledWith(10, 7200);
      expect(result.current.resolvedUrl).toBe(
        'https://storage.example.com/url'
      );
    });

    it('falls back to original videoUrl on API error', async () => {
      mockedGetVideoUrl.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(
        () =>
          useVideoUrl({
            videoId: 5,
            videoUrl: '/v0/videos/5/stream',
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
      });

      expect(result.current.resolvedUrl).toBe('/v0/videos/5/stream');
      expect(result.current.error?.message).toBe('Network error');
    });
  });

  describe('when videoUrl does not contain /stream', () => {
    it('returns the original videoUrl without calling the API', () => {
      const { result } = renderHook(
        () =>
          useVideoUrl({
            videoId: 42,
            videoUrl: 'https://cdn.example.com/video.mp4',
          }),
        { wrapper: createWrapper() }
      );

      expect(result.current.resolvedUrl).toBe(
        'https://cdn.example.com/video.mp4'
      );
      expect(mockedGetVideoUrl).not.toHaveBeenCalled();
    });
  });

  describe('when videoId is undefined', () => {
    it('returns the original videoUrl without calling the API', () => {
      const { result } = renderHook(
        () =>
          useVideoUrl({
            videoId: undefined,
            videoUrl: '/v0/videos/1/stream',
          }),
        { wrapper: createWrapper() }
      );

      expect(result.current.resolvedUrl).toBe('/v0/videos/1/stream');
      expect(mockedGetVideoUrl).not.toHaveBeenCalled();
    });
  });

  describe('when videoUrl is empty', () => {
    it('returns empty string and does not call the API', () => {
      const { result } = renderHook(
        () =>
          useVideoUrl({
            videoId: 42,
            videoUrl: '',
          }),
        { wrapper: createWrapper() }
      );

      // Empty string does not include '/stream', so shouldFetchSignedUrl is false
      expect(result.current.resolvedUrl).toBe('');
      expect(mockedGetVideoUrl).not.toHaveBeenCalled();
    });
  });

  describe('caching behavior', () => {
    it('does not refetch within staleTime window', async () => {
      mockedGetVideoUrl.mockResolvedValue('https://storage.example.com/url');

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
          },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(
          QueryClientProvider,
          { client: queryClient },
          children
        );

      const { result, unmount } = renderHook(
        () =>
          useVideoUrl({
            videoId: 99,
            videoUrl: '/v0/videos/99/stream',
          }),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockedGetVideoUrl).toHaveBeenCalledTimes(1);

      unmount();

      // Re-render with same params and same query client -- should use cache
      const { result: result2 } = renderHook(
        () =>
          useVideoUrl({
            videoId: 99,
            videoUrl: '/v0/videos/99/stream',
          }),
        { wrapper }
      );

      await waitFor(() => {
        expect(result2.current.isLoading).toBe(false);
      });

      // Should still only have been called once -- cached result reused
      expect(mockedGetVideoUrl).toHaveBeenCalledTimes(1);
      expect(result2.current.resolvedUrl).toBe(
        'https://storage.example.com/url'
      );
    });
  });

  describe('loading state', () => {
    it('starts in loading state when fetching signed URL', () => {
      // Never resolve so we can observe loading state
      mockedGetVideoUrl.mockReturnValue(new Promise(() => {}));

      const { result } = renderHook(
        () =>
          useVideoUrl({
            videoId: 1,
            videoUrl: '/v0/videos/1/stream',
          }),
        { wrapper: createWrapper() }
      );

      expect(result.current.isLoading).toBe(true);
      expect(result.current.resolvedUrl).toBe('');
      expect(result.current.error).toBeNull();
    });

    it('is not loading when query is disabled', () => {
      const { result } = renderHook(
        () =>
          useVideoUrl({
            videoId: undefined,
            videoUrl: 'https://example.com/video.mp4',
          }),
        { wrapper: createWrapper() }
      );

      expect(result.current.isLoading).toBe(false);
    });
  });
});
