import { createClient, SupabaseClient } from '@supabase/supabase-js';

const profile = process.env.REACT_APP_PROFILE || 'local';
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || '';
const supabasePublishableKey =
  process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY || '';

let supabase: SupabaseClient | null = null;

if (profile === 'local') {
  // Auth disabled in local profile mode
} else {
  if (!supabaseUrl || !supabasePublishableKey) {
    throw new Error(
      `Supabase credentials required when REACT_APP_PROFILE=${profile}`
    );
  }
  supabase = createClient(supabaseUrl, supabasePublishableKey);
}

export { supabase };
