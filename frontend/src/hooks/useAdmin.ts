import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../services/api';
import { useAuth } from './useAuth';

/**
 * Hook to check if current user is an admin.
 * Returns the admin status from backend API.
 */
export function useAdmin() {
  const { user } = useAuth();
  const profile = process.env.REACT_APP_PROFILE || 'local';

  const { data, isLoading, error } = useQuery<boolean>({
    queryKey: ['admin-status', user?.id],
    queryFn: async () => {
      if (profile === 'local') {
        // Local profile always allows admin access
        return true;
      }
      if (!user) {
        return false;
      }
      const status = await videoApi.checkAdminStatus();
      return status.is_admin;
    },
    enabled: !!user || profile === 'local',
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    isAdmin: data ?? false,
    isLoading,
    error,
  };
}
