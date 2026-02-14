import { FormEvent, useEffect, useRef, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import {
  usePlayerProfile,
  useUpsertPlayerProfile,
} from '../hooks/usePlayerProfile';
import './AccountMenu.css';

interface AccountMenuProps {
  onLogout: () => Promise<void>;
}

export function AccountMenu({ onLogout }: AccountMenuProps) {
  const { user, updateUserMetadata } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [profileName, setProfileName] = useState('');
  const [dominantHand, setDominantHand] = useState('right');
  const [backhandStyle, setBackhandStyle] = useState('');
  const [heightCm, setHeightCm] = useState('');
  const [ageGroup, setAgeGroup] = useState('');
  const [gender, setGender] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Fetch player profile
  const { data: playerProfile } = usePlayerProfile();
  const upsertProfile = useUpsertPlayerProfile();

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  // Get user display name and initial
  // Priority: player profile name > user metadata display_name > email prefix > 'User'
  const displayName =
    playerProfile?.name ||
    user?.user_metadata?.display_name ||
    user?.email?.split('@')[0] ||
    'User';
  const initial = displayName.charAt(0).toUpperCase();

  const handleLogout = async () => {
    setIsOpen(false);
    await onLogout();
  };

  const formatHeight = (value?: number | null) => {
    if (value === null || value === undefined) return 'Not set';
    const label = Number.isInteger(value) ? value.toString() : value.toFixed(1);
    return `${label} cm`;
  };

  const formatAgeGroup = (value?: string | null) => {
    if (!value) return 'Not set';
    return value
      .replace('under_', 'Under ')
      .replace('_to_', '-')
      .replace('_plus', '+');
  };

  const formatGender = (value?: string | null) => {
    if (!value) return 'Not set';
    const formatted = value
      .replace('non_binary', 'Non-Binary')
      .replace('prefer_not_to_say', 'Prefer Not To Say');
    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
  };

  const startEditing = () => {
    if (!playerProfile) return;
    setProfileName(playerProfile.name || '');
    setDominantHand(playerProfile.dominant_hand || 'right');
    setBackhandStyle(playerProfile.backhand_style || '');
    setHeightCm(
      playerProfile.height_cm !== null && playerProfile.height_cm !== undefined
        ? playerProfile.height_cm.toString()
        : ''
    );
    setAgeGroup(playerProfile.age_group || '');
    setGender(playerProfile.gender || '');
    setFormError(null);
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setFormError(null);
    setIsEditing(false);
  };

  const handleSaveProfile = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    setFormError(null);

    const trimmedName = profileName.trim();
    if (!trimmedName) {
      setFormError('Name is required.');
      return;
    }

    const trimmedHeight = heightCm.trim();
    let parsedHeight: number | null = null;
    if (trimmedHeight) {
      const numericHeight = Number(trimmedHeight);
      if (Number.isNaN(numericHeight)) {
        setFormError('Height must be a number.');
        return;
      }
      if (numericHeight < 0) {
        setFormError('Height must be positive.');
        return;
      }
      parsedHeight = numericHeight;
    }

    try {
      if (trimmedName !== user?.user_metadata?.display_name) {
        const { error: metadataError } = await updateUserMetadata({
          display_name: trimmedName,
        });
        if (metadataError) {
          console.warn('Failed to update user metadata:', metadataError);
        }
      }

      await upsertProfile.mutateAsync({
        name: trimmedName,
        dominant_hand: dominantHand || 'right',
        backhand_style: backhandStyle || null,
        height_cm: parsedHeight,
        age_group: ageGroup || null,
        gender: gender || null,
      });

      setIsEditing(false);
    } catch (err: any) {
      setFormError(err?.message || 'Failed to update profile.');
    }
  };

  return (
    <div className="account-menu" ref={menuRef}>
      <button
        className="account-menu-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Account menu"
        aria-expanded={isOpen}
      >
        <div className="account-avatar">{initial}</div>
        <span className="account-name">{displayName}</span>
        <svg
          className={`account-menu-chevron ${isOpen ? 'open' : ''}`}
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M4 6L8 10L12 6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="account-menu-dropdown">
          <div className="account-menu-header">
            <div className="account-menu-avatar-large">{initial}</div>
            <div className="account-menu-info">
              <div className="account-menu-name">{displayName}</div>
              <div className="account-menu-email">{user?.email}</div>
            </div>
          </div>

          {playerProfile && !isEditing && (
            <div className="account-menu-profile">
              <div className="account-menu-section-title">Player Profile</div>
              <div className="account-menu-profile-item">
                <span className="profile-label">Dominant Hand:</span>
                <span className="profile-value">
                  {playerProfile.dominant_hand === 'left' ? 'Left' : 'Right'}
                </span>
              </div>
              <div className="account-menu-profile-item">
                <span className="profile-label">Backhand:</span>
                <span className="profile-value">
                  {playerProfile.backhand_style
                    ? playerProfile.backhand_style === 'one_handed'
                      ? 'One-handed'
                      : 'Two-handed'
                    : 'Not set'}
                </span>
              </div>
              <div className="account-menu-profile-item">
                <span className="profile-label">Height:</span>
                <span className="profile-value">
                  {formatHeight(playerProfile.height_cm)}
                </span>
              </div>
              <div className="account-menu-profile-item">
                <span className="profile-label">Age Group:</span>
                <span className="profile-value">
                  {formatAgeGroup(playerProfile.age_group)}
                </span>
              </div>
              <div className="account-menu-profile-item">
                <span className="profile-label">Gender:</span>
                <span className="profile-value">
                  {formatGender(playerProfile.gender)}
                </span>
              </div>
              <button
                className="account-menu-edit-btn"
                type="button"
                onClick={startEditing}
              >
                Edit Profile
              </button>
            </div>
          )}

          {playerProfile && isEditing && (
            <form
              className="account-menu-profile account-menu-profile--edit"
              onSubmit={handleSaveProfile}
            >
              <div className="account-menu-section-title">
                Edit Player Profile
              </div>
              <div className="account-menu-field">
                <label htmlFor="profileName" className="profile-label">
                  Name
                </label>
                <input
                  id="profileName"
                  className="account-menu-input"
                  type="text"
                  value={profileName}
                  onChange={(event) => setProfileName(event.target.value)}
                  required
                  disabled={upsertProfile.isPending}
                />
              </div>
              <div className="account-menu-field">
                <label htmlFor="dominantHand" className="profile-label">
                  Dominant Hand
                </label>
                <select
                  id="dominantHand"
                  className="account-menu-input"
                  value={dominantHand}
                  onChange={(event) => setDominantHand(event.target.value)}
                  disabled={upsertProfile.isPending}
                >
                  <option value="right">Right-handed</option>
                  <option value="left">Left-handed</option>
                </select>
              </div>
              <div className="account-menu-field">
                <label htmlFor="backhandStyle" className="profile-label">
                  Backhand Style
                </label>
                <select
                  id="backhandStyle"
                  className="account-menu-input"
                  value={backhandStyle}
                  onChange={(event) => setBackhandStyle(event.target.value)}
                  disabled={upsertProfile.isPending}
                >
                  <option value="">Select backhand style</option>
                  <option value="one_handed">One-handed</option>
                  <option value="two_handed">Two-handed</option>
                </select>
              </div>
              <div className="account-menu-field">
                <label htmlFor="heightCm" className="profile-label">
                  Height (cm)
                </label>
                <input
                  id="heightCm"
                  className="account-menu-input"
                  type="number"
                  min="0"
                  step="0.1"
                  placeholder="Optional"
                  value={heightCm}
                  onChange={(event) => setHeightCm(event.target.value)}
                  disabled={upsertProfile.isPending}
                />
              </div>
              <div className="account-menu-field">
                <label htmlFor="ageGroup" className="profile-label">
                  Age Group
                </label>
                <select
                  id="ageGroup"
                  className="account-menu-input"
                  value={ageGroup}
                  onChange={(event) => setAgeGroup(event.target.value)}
                  disabled={upsertProfile.isPending}
                >
                  <option value="">Select age group</option>
                  <option value="under_13">Under 13</option>
                  <option value="13_to_17">13-17</option>
                  <option value="18_to_29">18-29</option>
                  <option value="30_to_44">30-44</option>
                  <option value="45_to_59">45-59</option>
                  <option value="60_plus">60+</option>
                </select>
              </div>
              <div className="account-menu-field">
                <label htmlFor="gender" className="profile-label">
                  Gender
                </label>
                <select
                  id="gender"
                  className="account-menu-input"
                  value={gender}
                  onChange={(event) => setGender(event.target.value)}
                  disabled={upsertProfile.isPending}
                >
                  <option value="">Select gender</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="non_binary">Non-Binary</option>
                  <option value="prefer_not_to_say">Prefer Not To Say</option>
                </select>
              </div>
              {formError && (
                <div className="account-menu-error">{formError}</div>
              )}
              <div className="account-menu-edit-actions">
                <button
                  type="button"
                  className="account-menu-secondary-btn"
                  onClick={cancelEditing}
                  disabled={upsertProfile.isPending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="account-menu-primary-btn"
                  disabled={upsertProfile.isPending}
                >
                  {upsertProfile.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}

          <div className="account-menu-divider"></div>

          <div className="account-menu-actions">
            <button
              className="account-menu-action-btn logout"
              onClick={handleLogout}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M6 14H3C2.44772 14 2 13.5523 2 13V3C2 2.44772 2.44772 2 3 2H6M10 11L14 7M14 7L10 3M14 7H6"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
