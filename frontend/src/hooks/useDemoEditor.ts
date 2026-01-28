import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../services/api';
import { useAuth } from './useAuth';

/**
 * Hook to check if current user is a demo editor.
 * Returns the demo editor status from backend API.
 */
export function useDemoEditor() {
  const { user } = useAuth();
  const profile = process.env.REACT_APP_PROFILE || 'local';

  const { data, isLoading, error } = useQuery<boolean>({
    queryKey: ['demo-editor-status', user?.id],
    queryFn: async () => {
      if (profile === 'local') {
        // Local profile always allows demo editing
        return true;
      }
      if (!user) {
        return false;
      }
      const status = await videoApi.checkDemoEditorStatus();
      return status.is_demo_editor;
    },
    enabled: !!user || profile === 'local',
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    isDemoEditor: data ?? false,
    isLoading,
    error,
  };
}
