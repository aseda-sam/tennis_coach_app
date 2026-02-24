import { supabase } from '../services/supabaseClient';

/**
 * Returns auth headers for API requests.
 * In local profile mode, no auth headers are added.
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
  const profile = import.meta.env.VITE_PROFILE || 'local';

  if (profile === 'local' || !supabase) {
    return {};
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    return {};
  }

  return {
    Authorization: `Bearer ${session.access_token}`,
  };
}
