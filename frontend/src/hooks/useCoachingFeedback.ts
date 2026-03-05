import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';

/**
 * Auto-fetches the latest cached coaching trace for a serve window.
 * Returns null if no trace exists yet.
 */
export function useCachedCoachingFeedback(serveWindowId: number | null) {
  return useQuery({
    queryKey: ['coaching-feedback-cached', serveWindowId],
    queryFn: () => biomechanicsApi.getCachedCoachingFeedback(serveWindowId!),
    enabled: serveWindowId !== null && serveWindowId > 0,
    staleTime: Infinity, // Cached traces don't change
    retry: 0,
  });
}

/**
 * Generates fresh coaching feedback (costs tokens).
 * Manual trigger only — call refetch() to fire.
 */
export function useCoachingFeedback(serveWindowId: number | null) {
  return useQuery({
    queryKey: ['coaching-feedback', serveWindowId],
    queryFn: () => biomechanicsApi.getCoachingFeedback(serveWindowId!),
    enabled: false, // Manual trigger only — costs API tokens
    staleTime: 10 * 60 * 1000,
    retry: 0,
  });
}

export function useCoachingNotes(
  serveWindowId: number | null,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['coaching-notes', serveWindowId],
    queryFn: () => biomechanicsApi.getCoachingNotes(serveWindowId!),
    enabled: enabled && serveWindowId !== null && serveWindowId > 0,
    staleTime: 30 * 1000,
  });
}

export function useSaveCoachingNote(serveWindowId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (note: string) =>
      biomechanicsApi.saveCoachingNote(serveWindowId!, note),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['coaching-notes', serveWindowId],
      });
    },
  });
}
