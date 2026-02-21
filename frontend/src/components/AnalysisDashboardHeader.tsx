import React from 'react';
import './AnalysisDashboard.css';
import { ArrowBackIcon } from './Icons';

interface AnalysisDashboardHeaderProps {
  videoFilename: string;
  hasServes: boolean;
  showEditMode: boolean;
  onClose: () => void;
  onToggleEditMode: () => void;
}

const AnalysisDashboardHeader: React.FC<AnalysisDashboardHeaderProps> = ({
  videoFilename,
  hasServes,
  showEditMode,
  onClose,
  onToggleEditMode,
}) => {
  return (
    <div className="analysis-dashboard__header">
      <button
        className="analysis-dashboard__back-button"
        onClick={onClose}
        type="button"
      >
        <ArrowBackIcon size={16} />
        Back to Library
      </button>
      <div className="analysis-dashboard__header-right">
        <h1 className="analysis-dashboard__title">{videoFilename}</h1>
        {hasServes && (
          <button
            className="analysis-dashboard__edit-btn"
            onClick={onToggleEditMode}
            type="button"
          >
            {showEditMode ? 'Done' : 'Edit Serves'}
          </button>
        )}
      </div>
    </div>
  );
};

export default AnalysisDashboardHeader;
