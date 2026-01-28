import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { playerApi } from '../services/playerApi';
import './AuthForm.css';

export function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [playerName, setPlayerName] = useState('');
  const [dominantHand, setDominantHand] = useState('right');
  const [backhandStyle, setBackhandStyle] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showResendLink, setShowResendLink] = useState(false);
  const { signIn, signUp, resendConfirmationEmail } = useAuth();
  const pendingProfileKey = 'pendingPlayerProfile';

  const upsertPlayerProfile = async () => {
    const profile = {
      name: playerName?.trim() || undefined,
      dominant_hand: dominantHand || undefined,
      backhand_style: backhandStyle?.trim() || undefined,
    };

    const hasProfileData =
      Boolean(profile.name) ||
      Boolean(profile.dominant_hand) ||
      Boolean(profile.backhand_style);

    if (!hasProfileData) {
      return;
    }

    await playerApi.upsertMe(profile);
  };

  const upsertPendingProfileIfNeeded = async () => {
    const pending = localStorage.getItem(pendingProfileKey);
    if (!pending) return;

    try {
      const profile = JSON.parse(pending) as {
        name?: string;
        dominant_hand?: string;
        backhand_style?: string;
      };
      await playerApi.upsertMe(profile);
      localStorage.removeItem(pendingProfileKey);
    } catch (err) {
      console.warn('Failed to apply pending player profile:', err);
    }
  };

  // Check if we just confirmed email (from URL hash)
  React.useEffect(() => {
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const type = hashParams.get('type');
    if (type === 'signup') {
      setSuccess('Email confirmed! You can now log in.');
      // Clean up URL
      window.history.replaceState(null, '', window.location.pathname);
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (isLogin) {
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
    } else {
      // Sign up
      const { data, error: authError } = await signUp(email, password);
      setLoading(false);

      if (authError) {
        setError(authError.message);
      } else if (data?.user) {
        // Signup successful
        // If email confirmation is disabled, user is automatically logged in
        // If email confirmation is enabled, show a message
        if (data.session) {
          // User is logged in (email confirmation disabled)
          setError(null);
          try {
            await upsertPlayerProfile();
          } catch (err) {
            console.warn('Failed to upsert player profile on signup:', err);
          }
          // The auth state change will automatically update the UI
        } else {
          // Email confirmation required
          setError(null);
          setSuccess(
            'Please check your email to confirm your account before logging in.'
          );
          setShowResendLink(true);
          const pendingProfile = {
            name: playerName?.trim() || undefined,
            dominant_hand: dominantHand || undefined,
            backhand_style: backhandStyle?.trim() || undefined,
          };
          localStorage.setItem(
            pendingProfileKey,
            JSON.stringify(pendingProfile)
          );
        }
      }
    }
  };

  const handleResendConfirmation = async () => {
    if (!email) {
      setError('Please enter your email address first.');
      return;
    }

    setError(null);
    setLoading(true);
    const { error: resendError } = await resendConfirmationEmail(email);
    setLoading(false);

    if (resendError) {
      setError(resendError.message);
    } else {
      setSuccess('Confirmation email sent! Please check your inbox.');
      setShowResendLink(false);
    }
  };

  return (
    <div className="auth-form">
      <div className="auth-form-header">
        <h2 className="auth-form-title">
          {isLogin ? 'Welcome back' : 'Create your account'}
        </h2>
        <p className="auth-form-subtitle">
          {isLogin
            ? 'Sign in to continue to Tennis Coach App'
            : 'Join Tennis Coach App to analyze your serve'}
        </p>
      </div>
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
        {!isLogin && (
          <>
            <div className="auth-form-field">
              <input
                type="text"
                className="input"
                placeholder="Player name (e.g., Alex)"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="auth-form-field">
              <select
                className="input"
                value={dominantHand}
                onChange={(e) => setDominantHand(e.target.value)}
                disabled={loading}
              >
                <option value="right">Right-handed</option>
                <option value="left">Left-handed</option>
              </select>
            </div>
            <div className="auth-form-field">
              <select
                className="input"
                value={backhandStyle}
                onChange={(e) => setBackhandStyle(e.target.value)}
                disabled={loading}
              >
                <option value="">Backhand style (optional)</option>
                <option value="one_handed">One-handed</option>
                <option value="two_handed">Two-handed</option>
              </select>
            </div>
          </>
        )}
        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Loading...' : isLogin ? 'Sign in' : 'Create account'}
        </button>
      </form>
      {showResendLink && !isLogin && (
        <div className="auth-form-footer">
          <button
            onClick={handleResendConfirmation}
            disabled={loading}
            type="button"
            className="auth-form-link"
          >
            Resend confirmation email
          </button>
        </div>
      )}
      <div className="auth-form-footer">
        <button
          onClick={() => {
            setIsLogin(!isLogin);
            setShowResendLink(false);
            setError(null);
            setSuccess(null);
          }}
          disabled={loading}
          type="button"
          className="auth-form-link"
        >
          {isLogin ? 'Need an account? Register' : 'Have an account? Sign in'}
        </button>
      </div>
    </div>
  );
}
