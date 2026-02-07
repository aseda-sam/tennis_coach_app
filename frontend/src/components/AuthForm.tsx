import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { playerApi } from '../services/playerApi';
import './AuthForm.css';

export function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [useMagicLink, setUseMagicLink] = useState(false);
  const [playerName, setPlayerName] = useState('');
  const [dominantHand, setDominantHand] = useState('right');
  const [backhandStyle, setBackhandStyle] = useState('');
  const [heightCm, setHeightCm] = useState('');
  const [ageGroup, setAgeGroup] = useState('');
  const [gender, setGender] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showResendLink, setShowResendLink] = useState(false);
  const { signIn, signInWithMagicLink, signUp, resendConfirmationEmail } =
    useAuth();
  const pendingProfileKey = 'pendingPlayerProfile';

  const getParsedHeight = () => {
    const trimmedHeight = heightCm.trim();
    if (!trimmedHeight) {
      return { value: null, error: null };
    }

    const numericHeight = Number(trimmedHeight);
    if (Number.isNaN(numericHeight)) {
      return { value: null, error: 'Height must be a number' };
    }
    if (numericHeight < 0) {
      return { value: null, error: 'Height must be positive' };
    }
    return { value: numericHeight, error: null };
  };

  const upsertPlayerProfile = async () => {
    // Name is required, so ensure it's always sent
    const trimmedName = playerName?.trim();
    if (!trimmedName) {
      setError('Player name is required');
      return;
    }

    const parsedHeight = getParsedHeight();
    if (parsedHeight.error) {
      setError(parsedHeight.error);
      return;
    }

    const profile = {
      name: trimmedName,
      dominant_hand: dominantHand || 'right', // Default to right if not selected
      backhand_style: backhandStyle?.trim() || undefined,
      height_cm: parsedHeight.value,
      age_group: ageGroup || null,
      gender: gender || null,
    };

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
          height_cm?: number | null;
          age_group?: string | null;
          gender?: string | null;
      };
      // Ensure name is provided before upserting
      if (profile.name?.trim()) {
        await playerApi.upsertMe({
          name: profile.name.trim(),
          dominant_hand: profile.dominant_hand || 'right',
          backhand_style: profile.backhand_style || undefined,
            height_cm: profile.height_cm ?? null,
            age_group: profile.age_group ?? null,
            gender: profile.gender ?? null,
        });
        localStorage.removeItem(pendingProfileKey);
      }
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
          // Store pending profile only if name is provided
          const trimmedName = playerName?.trim();
          if (trimmedName) {
            const parsedHeight = getParsedHeight();
            if (parsedHeight.error) {
              setError(parsedHeight.error);
              return;
            }
            const pendingProfile = {
              name: trimmedName,
              dominant_hand: dominantHand || 'right',
              backhand_style: backhandStyle?.trim() || undefined,
              height_cm: parsedHeight.value,
              age_group: ageGroup || null,
              gender: gender || null,
            };
            localStorage.setItem(
              pendingProfileKey,
              JSON.stringify(pendingProfile)
            );
          }
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
        {isLogin && useMagicLink ? null : (
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
        {!isLogin && (
          <>
            <div className="auth-form-field">
              <input
                type="text"
                className="input"
                placeholder="Player name (e.g., Alex)"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                required
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
            <div className="auth-form-field">
              <input
                type="number"
                className="input"
                placeholder="Height in cm (optional)"
                value={heightCm}
                onChange={(e) => setHeightCm(e.target.value)}
                disabled={loading}
                min="0"
                step="0.1"
              />
            </div>
            <div className="auth-form-field">
              <select
                className="input"
                value={ageGroup}
                onChange={(e) => setAgeGroup(e.target.value)}
                disabled={loading}
              >
                <option value="">Age group (optional)</option>
                <option value="under_13">Under 13</option>
                <option value="13_to_17">13-17</option>
                <option value="18_to_29">18-29</option>
                <option value="30_to_44">30-44</option>
                <option value="45_to_59">45-59</option>
                <option value="60_plus">60+</option>
              </select>
            </div>
            <div className="auth-form-field">
              <select
                className="input"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                disabled={loading}
              >
                <option value="">Gender (optional)</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="non_binary">Non-Binary</option>
                <option value="prefer_not_to_say">Prefer Not To Say</option>
              </select>
            </div>
          </>
        )}
        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading
            ? 'Loading...'
            : isLogin
              ? useMagicLink
                ? 'Send magic link'
                : 'Sign in'
              : 'Create account'}
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
      {isLogin && (
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
      )}
      <div className="auth-form-footer">
        <button
          onClick={() => {
            setIsLogin(!isLogin);
            setShowResendLink(false);
            setError(null);
            setSuccess(null);
            setUseMagicLink(false);
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
