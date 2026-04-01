import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';

const STALE_TIME = 5 * 60 * 1000;

/**
 * Create an object URL from a blob and revoke it on cleanup.
 *
 * Uses useEffect (not useMemo) so that React StrictMode's simulated
 * unmount+remount cycle correctly re-creates the URL in the second setup
 * call. With useMemo, a cache-hit blob (same reference) would not re-run
 * the factory after StrictMode revoked the URL, leaving a dead URL in the
 * img src on every second open of a modal.
 */
function useBlobUrl(blob: Blob | null | undefined): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!blob) {
      setUrl(null);
      return;
    }
    const newUrl = URL.createObjectURL(blob);
    setUrl(newUrl);
    return () => {
      URL.revokeObjectURL(newUrl);
    };
  }, [blob]);

  return url;
}

/**
 * Fetch a KTP frame from the backend as a blob URL.
 * Caches the Blob in React Query; object URL is created/revoked per mount.
 */
export function useServeWindowFrame(
  serveWindowId: number | null,
  ktp = 'trophy_position'
): { frameUrl: string | null; isLoading: boolean } {
  const { data: blob, isLoading } = useQuery({
    queryKey: ['serve-window-frame', serveWindowId, ktp],
    queryFn: () => biomechanicsApi.getFrame(serveWindowId!, ktp),
    enabled: serveWindowId != null,
    staleTime: STALE_TIME,
  });

  const frameUrl = useBlobUrl(blob);
  return { frameUrl, isLoading };
}

/**
 * Fetch a frame at a specific timestamp as a blob URL.
 * Caches the Blob in React Query; object URL is created/revoked per mount.
 */
export function useServeWindowFrameAtTimestamp(
  serveWindowId: number | null,
  timestamp: number | null | undefined,
  crop?: string
): { frameUrl: string | null; isLoading: boolean } {
  const { data: blob, isLoading } = useQuery({
    queryKey: ['serve-window-frame-ts', serveWindowId, timestamp, crop],
    queryFn: () =>
      biomechanicsApi.getFrameAtTimestamp(serveWindowId!, timestamp!, crop),
    enabled: serveWindowId != null && timestamp != null,
    staleTime: STALE_TIME,
  });

  const frameUrl = useBlobUrl(blob);
  return { frameUrl, isLoading };
}
