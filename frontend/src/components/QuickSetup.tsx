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
  const [heightCm, setHeightCm] = useState('');
  const [ageGroup, setAgeGroup] = useState('');
  const [gender, setGender] = useState('');
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
      setHeightCm(
        existingProfile.height_cm !== null &&
          existingProfile.height_cm !== undefined
          ? existingProfile.height_cm.toString()
          : ''
      );
      setAgeGroup(existingProfile.age_group || '');
      setGender(existingProfile.gender || '');
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
      const trimmedHeight = heightCm.trim();
      let parsedHeight: number | null = null;
      if (trimmedHeight) {
        const numericHeight = Number(trimmedHeight);
        if (Number.isNaN(numericHeight)) {
          setError('Height must be a number');
          setLoading(false);
          return;
        }
        if (numericHeight < 0) {
          setError('Height must be positive');
          setLoading(false);
          return;
        }
        parsedHeight = numericHeight;
      }

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
        height_cm: parsedHeight,
        age_group: ageGroup || null,
        gender: gender || null,
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
            <label htmlFor="heightCm" className="quick-setup-label">
              Height (cm)
            </label>
            <input
              id="heightCm"
              type="number"
              className="quick-setup-input"
              placeholder="Optional"
              min="0"
              step="0.1"
              value={heightCm}
              onChange={(e) => setHeightCm(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="quick-setup-field">
            <label htmlFor="ageGroup" className="quick-setup-label">
              Age group
            </label>
            <select
              id="ageGroup"
              className="quick-setup-input"
              value={ageGroup}
              onChange={(e) => setAgeGroup(e.target.value)}
              disabled={loading}
            >
              <option value="">Select age group (optional)</option>
              <option value="under_13">Under 13</option>
              <option value="13_to_17">13-17</option>
              <option value="18_to_29">18-29</option>
              <option value="30_to_44">30-44</option>
              <option value="45_to_59">45-59</option>
              <option value="60_plus">60+</option>
            </select>
          </div>
          <div className="quick-setup-field">
            <label htmlFor="gender" className="quick-setup-label">
              Gender
            </label>
            <select
              id="gender"
              className="quick-setup-input"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              disabled={loading}
            >
              <option value="">Select gender (optional)</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="non_binary">Non-Binary</option>
              <option value="prefer_not_to_say">Prefer Not To Say</option>
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
