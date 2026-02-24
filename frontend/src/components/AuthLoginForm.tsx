import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { playerApi } from '../services/playerApi';

interface AuthLoginFormProps {
  email: string;
  setEmail: (value: string) => void;
  error: string | null;
  setError: (value: string | null) => void;
  success: string | null;
  setSuccess: (value: string | null) => void;
  loading: boolean;
  setLoading: (value: boolean) => void;
  onSwitchToSignup: () => void;
}

const PENDING_PROFILE_KEY = 'pendingPlayerProfile';

export function AuthLoginForm({
  email,
  setEmail,
  error,
  setError,
  success,
  setSuccess,
  loading,
  setLoading,
  onSwitchToSignup,
}: AuthLoginFormProps) {
  const { signIn, signInWithMagicLink } = useAuth();
  const [password, setPassword] = useState('');
  const [useMagicLink, setUseMagicLink] = useState(false);

  const upsertPendingProfileIfNeeded = async () => {
    const pending = localStorage.getItem(PENDING_PROFILE_KEY);
    if (!pending) return;

    try {
      const profile = JSON.parse(pending) as {
        name?: string;
        dominant_hand?: string;
        backhand_style?: string;
      };
      if (profile.name?.trim()) {
        await playerApi.upsertMe({
          name: profile.name.trim(),
          dominant_hand: profile.dominant_hand || 'right',
          backhand_style: profile.backhand_style || undefined,
        });
        localStorage.removeItem(PENDING_PROFILE_KEY);
      }
    } catch (err) {
      console.warn('Failed to apply pending player profile:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (useMagicLink) {
      const { error: authError } = await signInWithMagicLink(email);
      setLoading(false);
      if (authError) {
        setError(authError.message);
      } else {
        setSuccess('Magic link sent. Check your email to sign in.');
      }
    } else {
      const { error: authError } = await signIn(email, password);
      setLoading(false);
      if (authError) {
        setError(authError.message);
      } else {
        try {
          await upsertPendingProfileIfNeeded();
        } catch (err) {
          console.warn('Failed to upsert player profile after login:', err);
        }
      }
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="auth-form-form">
        <div className="auth-form-field">
          <input
            type="email"
            className="input"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
          />
        </div>
        {useMagicLink ? null : (
          <div className="auth-form-field">
            <input
              type="password"
              className="input"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
        )}
        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading
            ? 'Signing in...'
            : useMagicLink
              ? 'Send magic link'
              : 'Sign in'}
        </button>
      </form>
      <div className="auth-form-footer">
        <button
          onClick={() => {
            setUseMagicLink(!useMagicLink);
            setError(null);
            setSuccess(null);
          }}
          disabled={loading}
          type="button"
          className="auth-form-link"
        >
          {useMagicLink ? 'Use password instead' : 'Use magic link instead'}
        </button>
        {useMagicLink && (
          <p className="auth-form-help">
            We will email you a one time sign in link.
          </p>
        )}
      </div>
      <div className="auth-form-footer">
        <button
          onClick={onSwitchToSignup}
          disabled={loading}
          type="button"
          className="auth-form-link"
        >
          Need an account? Register
        </button>
      </div>
    </>
  );
}
