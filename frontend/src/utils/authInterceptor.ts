import { AxiosInstance } from 'axios';
import { supabase } from '../services/supabaseClient';

/**
 * Creates an authentication interceptor for an axios instance.
 * Adds Bearer token to requests when not in local profile mode.
 *
 * @param axiosInstance - The axios instance to add the interceptor to
 * @param instanceName - Optional name for logging (e.g., "Analysis API")
 */
export function createAuthInterceptor(
  axiosInstance: AxiosInstance,
  instanceName: string = 'API'
): void {
  axiosInstance.interceptors.request.use(async (config) => {
    const profile = process.env.REACT_APP_PROFILE || 'local';

    // Only add auth headers if profile is not 'local' and supabase is available
    if (profile !== 'local' && supabase) {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
        console.log(
          `[${instanceName}] ${config.method?.toUpperCase()} ${config.url} - Auth token added (profile: ${profile})`
        );
      } else {
        console.warn(
          `[${instanceName}] ${config.method?.toUpperCase()} ${config.url} - No session token available (profile: ${profile})`
        );
      }
    } else {
      console.log(
        `[${instanceName}] ${config.method?.toUpperCase()} ${config.url} - No auth required (profile: ${profile})`
      );
    }

    return config;
  });
}
