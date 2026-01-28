import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { playerApi, PlayerInfo } from '../services/playerApi';
import './AccountMenu.css';

interface AccountMenuProps {
  onLogout: () => Promise<void>;
}

export function AccountMenu({ onLogout }: AccountMenuProps) {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Fetch player profile
  const { data: playerProfile } = useQuery<PlayerInfo>({
    queryKey: ['playerProfile', user?.id],
    queryFn: playerApi.getMe,
    enabled: !!user,
    retry: 1,
  });

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
  const displayName =
    playerProfile?.name || user?.email?.split('@')[0] || 'User';
  const initial = displayName.charAt(0).toUpperCase();

  const handleLogout = async () => {
    setIsOpen(false);
    await onLogout();
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

          {playerProfile && (
            <div className="account-menu-profile">
              <div className="account-menu-section-title">Player Profile</div>
              <div className="account-menu-profile-item">
                <span className="profile-label">Dominant Hand:</span>
                <span className="profile-value">
                  {playerProfile.dominant_hand === 'left' ? 'Left' : 'Right'}
                </span>
              </div>
              {playerProfile.backhand_style && (
                <div className="account-menu-profile-item">
                  <span className="profile-label">Backhand:</span>
                  <span className="profile-value">
                    {playerProfile.backhand_style === 'one_handed'
                      ? 'One-handed'
                      : 'Two-handed'}
                  </span>
                </div>
              )}
            </div>
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
