import { LogOut } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { usePlayerProfile } from '../hooks/usePlayerProfile';
import { AccountMenuEditForm } from './AccountMenuEditForm';
import './AccountMenu.css';

interface AccountMenuProps {
  onLogout: () => Promise<void>;
}

export function AccountMenu({ onLogout }: AccountMenuProps) {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Fetch player profile
  const { data: playerProfile } = usePlayerProfile();

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
                onClick={() => setIsEditing(true)}
              >
                Edit Profile
              </button>
            </div>
          )}

          {playerProfile && isEditing && (
            <AccountMenuEditForm
              playerProfile={playerProfile}
              onCancel={() => setIsEditing(false)}
              onSaved={() => setIsEditing(false)}
            />
          )}

          <div className="account-menu-divider"></div>

          <div className="account-menu-actions">
            <button
              className="account-menu-action-btn logout"
              onClick={handleLogout}
            >
              <LogOut size={16} strokeWidth={1.5} />
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
