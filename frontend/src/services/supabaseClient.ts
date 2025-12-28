import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || '';
const supabasePublishableKey =
  process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY ||
  process.env.REACT_APP_SUPABASE_ANON_KEY ||
  '';

if (!supabaseUrl || !supabasePublishableKey) {
  throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabasePublishableKey);
