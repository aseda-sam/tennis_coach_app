import { FormEvent, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useUpsertPlayerProfile } from '../hooks/usePlayerProfile';
import { PlayerInfo } from '../types/player';

interface AccountMenuEditFormProps {
  playerProfile: PlayerInfo;
  onCancel: () => void;
  onSaved: () => void;
}

export function AccountMenuEditForm({
  playerProfile,
  onCancel,
  onSaved,
}: AccountMenuEditFormProps) {
  const { user, updateUserMetadata } = useAuth();
  const upsertProfile = useUpsertPlayerProfile();

  const [profileName, setProfileName] = useState(playerProfile.name || '');
  const [dominantHand, setDominantHand] = useState(
    playerProfile.dominant_hand || 'right'
  );
  const [backhandStyle, setBackhandStyle] = useState(
    playerProfile.backhand_style || ''
  );
  const [heightCm, setHeightCm] = useState(
    playerProfile.height_cm !== null && playerProfile.height_cm !== undefined
      ? playerProfile.height_cm.toString()
      : ''
  );
  const [ageGroup, setAgeGroup] = useState(playerProfile.age_group || '');
  const [gender, setGender] = useState(playerProfile.gender || '');
  const [formError, setFormError] = useState<string | null>(null);

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

      onSaved();
    } catch (err: any) {
      setFormError(err?.message || 'Failed to update profile.');
    }
  };

  return (
    <form
      className="account-menu-profile account-menu-profile--edit"
      onSubmit={handleSaveProfile}
    >
      <div className="account-menu-section-title">Edit Player Profile</div>
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
      {formError && <div className="account-menu-error">{formError}</div>}
      <div className="account-menu-edit-actions">
        <button
          type="button"
          className="account-menu-secondary-btn"
          onClick={onCancel}
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
  );
}
