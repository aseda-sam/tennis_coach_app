import React from 'react';
import './AnalysisViewToggle.css';

export type ViewMode = 'video-focus' | 'analysis-focus';

interface AnalysisViewToggleProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

const AnalysisViewToggle: React.FC<AnalysisViewToggleProps> = ({
  viewMode,
  onViewModeChange,
}) => {
  return (
    <div
      className="analysis-view-toggle"
      role="tablist"
      aria-label="View mode"
      data-tour-step="view-toggle"
    >
      <button
        className={`analysis-view-toggle__option${viewMode === 'video-focus' ? ' analysis-view-toggle__option--active' : ''}`}
        onClick={() => onViewModeChange('video-focus')}
        role="tab"
        aria-selected={viewMode === 'video-focus'}
        type="button"
      >
        Video
      </button>
      <button
        className={`analysis-view-toggle__option${viewMode === 'analysis-focus' ? ' analysis-view-toggle__option--active' : ''}`}
        onClick={() => onViewModeChange('analysis-focus')}
        role="tab"
        aria-selected={viewMode === 'analysis-focus'}
        type="button"
      >
        Pose
      </button>
    </div>
  );
};

export default AnalysisViewToggle;
