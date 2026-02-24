import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { playerApi } from '../services/playerApi';

interface AuthSignupFormProps {
  email: string;
  setEmail: (value: string) => void;
  error: string | null;
  setError: (value: string | null) => void;
  success: string | null;
  setSuccess: (value: string | null) => void;
  loading: boolean;
  setLoading: (value: boolean) => void;
  showResendLink: boolean;
  setShowResendLink: (value: boolean) => void;
  onSwitchToLogin: () => void;
}

const PENDING_PROFILE_KEY = 'pendingPlayerProfile';

export function AuthSignupForm({
  email,
  setEmail,
  error,
  setError,
  success,
  setSuccess,
  loading,
  setLoading,
  showResendLink,
  setShowResendLink,
  onSwitchToLogin,
}: AuthSignupFormProps) {
  const { signUp, resendConfirmationEmail } = useAuth();

  const [password, setPassword] = useState('');
  const [playerName, setPlayerName] = useState('');
  const [dominantHand, setDominantHand] = useState('right');
  const [backhandStyle, setBackhandStyle] = useState('');
  const [heightCm, setHeightCm] = useState('');
  const [ageGroup, setAgeGroup] = useState('');
  const [gender, setGender] = useState('');

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
      dominant_hand: dominantHand || 'right',
      backhand_style: backhandStyle?.trim() || undefined,
      height_cm: parsedHeight.value,
      age_group: ageGroup || null,
      gender: gender || null,
    };

    await playerApi.upsertMe(profile);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { data, error: authError } = await signUp(email, password);
    setLoading(false);

    if (authError) {
      setError(authError.message);
    } else if (data?.user) {
      if (data.session) {
        // User is logged in (email confirmation disabled)
        setError(null);
        try {
          await upsertPlayerProfile();
        } catch (err) {
          console.warn('Failed to upsert player profile on signup:', err);
        }
      } else {
        // Email confirmation required
        setError(null);
        setSuccess(
          'Please check your email to confirm your account before logging in.'
        );
        setShowResendLink(true);
        const trimmedName = playerName?.trim();
        if (trimmedName) {
          const pendingProfile = {
            name: trimmedName,
            dominant_hand: dominantHand || 'right',
            backhand_style: backhandStyle?.trim() || undefined,
          };
          localStorage.setItem(
            PENDING_PROFILE_KEY,
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
        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Creating your account...' : 'Create account'}
        </button>
      </form>
      {showResendLink && (
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
          onClick={onSwitchToLogin}
          disabled={loading}
          type="button"
          className="auth-form-link"
        >
          Have an account? Sign in
        </button>
      </div>
    </>
  );
}
