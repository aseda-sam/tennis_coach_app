import { Session, User } from '@supabase/supabase-js';
import { useEffect, useState } from 'react';
import { supabase } from '../services/supabaseClient';

// Mock user for local profile
const MOCK_USER: User = {
  id: '00000000-0000-0000-0000-000000000000',
  email: 'dev@localhost',
  app_metadata: {},
  user_metadata: {},
  aud: 'authenticated',
  created_at: new Date().toISOString(),
} as User;

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // If supabase is null (local profile), return mock user
    if (!supabase) {
      setUser(MOCK_USER);
      setSession(null);
      setLoading(false);
      return;
    }

    // Store in local const so TypeScript knows it's non-null
    const supabaseClient = supabase;

    // Handle email confirmation callback
    // When user clicks email confirmation link, Supabase redirects with tokens in URL hash
    const handleEmailConfirmation = async () => {
      // Check if we have hash fragments (email confirmation tokens)
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      const accessToken = hashParams.get('access_token');
      const refreshToken = hashParams.get('refresh_token');
      const type = hashParams.get('type');

      if (type === 'recovery' || type === 'signup' || type === 'invite') {
        // Exchange tokens for session
        if (accessToken && refreshToken) {
          const { data, error } = await supabaseClient.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          if (error) {
            // Error handling is done by the auth system
          } else if (data.session) {
            // Successfully confirmed and logged in
            // If this is an invitation, mark that setup is needed
            if (type === 'invite') {
              // Check if user has display_name in metadata
              const displayName = data.session.user.user_metadata?.display_name;
              if (!displayName) {
                // Mark that user needs setup
                sessionStorage.setItem('needsSetup', 'true');
              }
            }
            // Clean up the URL hash
            window.history.replaceState(null, '', window.location.pathname);
          }
        }
      }
    };

    // Handle email confirmation first
    handleEmailConfirmation().then(() => {
      // Then get initial session
      supabaseClient.auth.getSession().then(({ data: { session } }) => {
        setSession(session);
        setUser(session?.user ?? null);
        setLoading(false);
      });
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabaseClient.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signUp = async (email: string, password: string) => {
    if (!supabase) {
      return {
        data: { user: MOCK_USER, session: null },
        error: null,
      };
    }
    // Include redirectTo for email confirmation
    // This tells Supabase where to redirect after email confirmation
    const redirectTo = `${window.location.origin}${window.location.pathname}`;
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: redirectTo,
      },
    });
    return { data, error };
  };

  const signIn = async (email: string, password: string) => {
    if (!supabase) {
      return {
        data: { user: MOCK_USER, session: null },
        error: null,
      };
    }
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { data, error };
  };

  const signInWithMagicLink = async (email: string) => {
    if (!supabase) {
      return { data: null, error: null };
    }
    const redirectTo = `${window.location.origin}${window.location.pathname}`;
    const { data, error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: redirectTo,
      },
    });
    return { data, error };
  };

  const signOut = async () => {
    if (!supabase) {
      // In local mode, just clear the mock user state
      setUser(null);
      setSession(null);
      return;
    }
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('Logout error:', error);
      // Still clear state even if signOut fails
      setUser(null);
      setSession(null);
    }
  };

  const resendConfirmationEmail = async (email: string) => {
    if (!supabase) {
      return { data: null, error: null };
    }
    // Resend email confirmation
    const redirectTo = `${window.location.origin}${window.location.pathname}`;
    const { data, error } = await supabase.auth.resend({
      type: 'signup',
      email,
      options: {
        emailRedirectTo: redirectTo,
      },
    });
    return { data, error };
  };

  const updateUserMetadata = async (metadata: Record<string, any>) => {
    if (!supabase) {
      return { data: null, error: null };
    }
    const { data, error } = await supabase.auth.updateUser({
      data: metadata,
    });
    return { data, error };
  };

  return {
    user,
    session,
    loading,
    signUp,
    signIn,
    signInWithMagicLink,
    signOut,
    resendConfirmationEmail,
    updateUserMetadata,
  };
}
