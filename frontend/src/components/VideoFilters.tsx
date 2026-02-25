import React from 'react';
import { usePlayerProfile } from '../hooks/usePlayerProfile';
import type { VideoFilters as VideoFiltersType } from '../services/api';
import './VideoFilters.css';

interface VideoFiltersProps {
  filters: VideoFiltersType;
  onChange: (filters: VideoFiltersType) => void;
  sortMode: 'recorded_at' | 'uploaded_at';
  sortDirection: 'desc' | 'asc';
  onSortPillClick: (sortMode: 'recorded_at' | 'uploaded_at') => void;
}

interface FilterOption {
  value: string;
  label: string;
}

const CAMERA_ANGLES: FilterOption[] = [
  { value: 'behind', label: 'Behind' },
  { value: 'profile', label: 'Profile' },
];

const VideoFilters: React.FC<VideoFiltersProps> = ({
  filters,
  onChange,
  sortMode,
  sortDirection,
  onSortPillClick,
}) => {
  const { data: playerProfile } = usePlayerProfile();

  const hasActiveFilters = Object.values(filters).some(
    (v) => v !== undefined && v !== null && v !== ''
  );

  const toggleFilter = (
    key: keyof VideoFiltersType,
    value: string | number
  ) => {
    const current = filters[key];
    if (current === value) {
      const next = { ...filters };
      delete next[key];
      onChange(next);
    } else {
      onChange({ ...filters, [key]: value });
    }
  };

  const clearFilters = () => {
    onChange({});
  };

  const renderPillGroup = (
    label: string,
    options: FilterOption[],
    filterKey: keyof VideoFiltersType
  ) => (
    <div className="filter-group">
      <span className="filter-group-label">{label}</span>
      <div className="filter-pills">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`filter-pill${String(filters[filterKey]) === opt.value ? ' filter-pill--active' : ''}`}
            onClick={() => toggleFilter(filterKey, opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );

  const handlePlayerFilter = (selection: 'you' | 'other') => {
    if (!playerProfile?.id) return;
    const isActive =
      selection === 'you'
        ? filters.player_id === playerProfile.id
        : filters.exclude_player_id === playerProfile.id;

    if (isActive) {
      const next = { ...filters };
      delete next.player_id;
      delete next.exclude_player_id;
      onChange(next);
    } else {
      const next = { ...filters };
      delete next.player_id;
      delete next.exclude_player_id;
      if (selection === 'you') {
        next.player_id = playerProfile.id;
      } else {
        next.exclude_player_id = playerProfile.id;
      }
      onChange(next);
    }
  };

  return (
    <div className="video-filters">
      <div className="filter-groups">
        {renderPillGroup('Angle', CAMERA_ANGLES, 'camera_angle')}
        {playerProfile?.id && (
          <div className="filter-group">
            <span className="filter-group-label">Player</span>
            <div className="filter-pills">
              <button
                type="button"
                className={`filter-pill${filters.player_id === playerProfile.id ? ' filter-pill--active' : ''}`}
                onClick={() => handlePlayerFilter('you')}
              >
                You
              </button>
              <button
                type="button"
                className={`filter-pill${filters.exclude_player_id === playerProfile.id ? ' filter-pill--active' : ''}`}
                onClick={() => handlePlayerFilter('other')}
              >
                Someone Else
              </button>
            </div>
          </div>
        )}
      </div>
      <div className="filter-actions">
        <div className="sort-group">
          <span className="filter-group-label">
            Sort ({sortDirection === 'desc' ? 'Newest' : 'Oldest'})
          </span>
          <div className="filter-pills">
            <button
              type="button"
              className={`filter-pill${sortMode === 'recorded_at' ? ' filter-pill--active' : ''}`}
              onClick={() => onSortPillClick('recorded_at')}
            >
              Recorded Time
            </button>
            <button
              type="button"
              className={`filter-pill${sortMode === 'uploaded_at' ? ' filter-pill--active' : ''}`}
              onClick={() => onSortPillClick('uploaded_at')}
            >
              Uploaded Time
            </button>
          </div>
        </div>
        {hasActiveFilters && (
          <button
            type="button"
            className="clear-filters-btn"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
};

export default VideoFilters;
