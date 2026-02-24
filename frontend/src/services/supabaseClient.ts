import { createClient, SupabaseClient } from '@supabase/supabase-js';

const profile = import.meta.env.VITE_PROFILE || 'local';
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabasePublishableKey =
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || '';

let supabase: SupabaseClient | null = null;

if (profile === 'local') {
  // Auth disabled in local profile mode
} else {
  if (!supabaseUrl || !supabasePublishableKey) {
    throw new Error(
      `Supabase credentials required when VITE_PROFILE=${profile}`
    );
  }
  supabase = createClient(supabaseUrl, supabasePublishableKey);
}

export { supabase };
