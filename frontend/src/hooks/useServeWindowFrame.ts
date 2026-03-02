import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';

const STALE_TIME = 5 * 60 * 1000;

/**
 * Fetch a KTP frame from the backend as a blob URL.
 * Automatically revokes previous object URLs on refetch/unmount.
 */
export function useServeWindowFrame(
  serveWindowId: number | null,
  ktp = 'trophy_position'
): { frameUrl: string | null; isLoading: boolean } {
  const prevUrlRef = useRef<string | null>(null);

  const { data: frameUrl = null, isLoading } = useQuery({
    queryKey: ['serve-window-frame', serveWindowId, ktp],
    queryFn: async () => {
      const blob = await biomechanicsApi.getFrame(serveWindowId!, ktp);
      return URL.createObjectURL(blob);
    },
    enabled: serveWindowId != null,
    staleTime: STALE_TIME,
  });

  // Revoke previous object URL when a new one is created or on unmount
  useEffect(() => {
    if (prevUrlRef.current && prevUrlRef.current !== frameUrl) {
      URL.revokeObjectURL(prevUrlRef.current);
    }
    prevUrlRef.current = frameUrl;

    return () => {
      if (prevUrlRef.current) {
        URL.revokeObjectURL(prevUrlRef.current);
        prevUrlRef.current = null;
      }
    };
  }, [frameUrl]);

  return { frameUrl, isLoading };
}
