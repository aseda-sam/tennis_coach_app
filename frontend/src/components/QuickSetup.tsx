import { useQuery } from '@tanstack/react-query';
import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { playerApi } from '../services/playerApi';
import './QuickSetup.css';

interface QuickSetupProps {
  onComplete: () => void;
}

export function QuickSetup({ onComplete }: QuickSetupProps) {
  const { user, updateUserMetadata } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [dominantHand, setDominantHand] = useState('right');
  const [backhandStyle, setBackhandStyle] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Check if user already has a player profile
  const { data: existingProfile } = useQuery({
    queryKey: ['playerProfile', user?.id],
    queryFn: playerApi.getMe,
    enabled: !!user,
    retry: false,
  });

  // Pre-fill form if user already has a profile or display_name
  useEffect(() => {
    if (existingProfile?.name) {
      setDisplayName(existingProfile.name);
      setDominantHand(existingProfile.dominant_hand || 'right');
      if (existingProfile.backhand_style) {
        setBackhandStyle(existingProfile.backhand_style);
      }
    } else if (user?.user_metadata?.display_name) {
      setDisplayName(user.user_metadata.display_name);
    }
  }, [existingProfile, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedName = displayName?.trim();
    if (!trimmedName) {
      setError('Name is required');
      return;
    }

    setLoading(true);

    try {
      // Update Supabase user metadata with display_name
      const { error: metadataError } = await updateUserMetadata({
        display_name: trimmedName,
      });

      if (metadataError) {
        console.warn('Failed to update user metadata:', metadataError);
        // Continue anyway - player profile is more important
      }

      // Create/update player profile
      await playerApi.upsertMe({
        name: trimmedName,
        dominant_hand: dominantHand || 'right',
        backhand_style: backhandStyle?.trim() || undefined,
      });

      // Clear the needsSetup flag
      sessionStorage.removeItem('needsSetup');

      // Call onComplete to close the setup
      onComplete();
    } catch (err: any) {
      setError(err?.message || 'Failed to save profile. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="quick-setup-overlay">
      <div className="quick-setup-modal">
        <div className="quick-setup-header">
          <h2 className="quick-setup-title">Welcome! Let's get you set up</h2>
          <p className="quick-setup-subtitle">
            We just need a few details to personalize your experience
          </p>
        </div>

        <form onSubmit={handleSubmit} className="quick-setup-form">
          <div className="quick-setup-field">
            <label htmlFor="displayName" className="quick-setup-label">
              Your name
            </label>
            <input
              id="displayName"
              type="text"
              className="quick-setup-input"
              placeholder="e.g., Alex"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              disabled={loading}
              autoFocus
            />
          </div>

          <div className="quick-setup-field">
            <label htmlFor="dominantHand" className="quick-setup-label">
              Dominant hand
            </label>
            <select
              id="dominantHand"
              className="quick-setup-input"
              value={dominantHand}
              onChange={(e) => setDominantHand(e.target.value)}
              disabled={loading}
            >
              <option value="right">Right-handed</option>
              <option value="left">Left-handed</option>
            </select>
          </div>

          <div className="quick-setup-field">
            <label htmlFor="backhandStyle" className="quick-setup-label">
              Backhand style <span className="optional">(optional)</span>
            </label>
            <select
              id="backhandStyle"
              className="quick-setup-input"
              value={backhandStyle}
              onChange={(e) => setBackhandStyle(e.target.value)}
              disabled={loading}
            >
              <option value="">Select backhand style</option>
              <option value="one_handed">One-handed</option>
              <option value="two_handed">Two-handed</option>
            </select>
          </div>

          {error && <div className="quick-setup-error">{error}</div>}

          <button
            type="submit"
            className="quick-setup-button"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save and continue'}
          </button>
        </form>
      </div>
    </div>
  );
}
