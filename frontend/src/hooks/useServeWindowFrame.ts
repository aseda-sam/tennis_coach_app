import { useEffect, useMemo, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';

const STALE_TIME = 5 * 60 * 1000;

/**
 * Create an object URL from a blob, revoking the previous one.
 * Returns a stable URL that updates only when the blob identity changes.
 */
function useBlobUrl(blob: Blob | null | undefined): string | null {
  const urlRef = useRef<string | null>(null);
  const blobRef = useRef<Blob | null>(null);

  // Only create a new URL when we get a genuinely new blob
  const url = useMemo(() => {
    if (!blob) {
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
        urlRef.current = null;
        blobRef.current = null;
      }
      return null;
    }
    // Same blob object — reuse existing URL
    if (blob === blobRef.current && urlRef.current) {
      return urlRef.current;
    }
    // New blob — revoke old, create new
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
    }
    const newUrl = URL.createObjectURL(blob);
    urlRef.current = newUrl;
    blobRef.current = blob;
    return newUrl;
  }, [blob]);

  // Revoke on unmount
  useEffect(() => {
    return () => {
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
        urlRef.current = null;
        blobRef.current = null;
      }
    };
  }, []);

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
  timestamp: number | null | undefined
): { frameUrl: string | null; isLoading: boolean } {
  const { data: blob, isLoading } = useQuery({
    queryKey: ['serve-window-frame-ts', serveWindowId, timestamp],
    queryFn: () =>
      biomechanicsApi.getFrameAtTimestamp(serveWindowId!, timestamp!),
    enabled: serveWindowId != null && timestamp != null,
    staleTime: STALE_TIME,
  });

  const frameUrl = useBlobUrl(blob);
  return { frameUrl, isLoading };
}
