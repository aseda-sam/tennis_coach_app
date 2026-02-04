import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../services/api';
import { AppConfig } from '../types/config';

const FALLBACK_CONFIG: AppConfig = {
  upload_limits: {
    max_file_size_bytes: 100 * 1024 * 1024,
    max_video_duration_seconds: 300,
    supported_formats: ['.mp4', '.mov', '.avi', '.mkv', '.wmv'],
  },
};

export function useAppConfig() {
  const { data, isLoading, error } = useQuery<AppConfig>({
    queryKey: ['app-config'],
    queryFn: () => videoApi.getAppConfig(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  return {
    config: data ?? FALLBACK_CONFIG,
    isLoading,
    error,
  };
}
