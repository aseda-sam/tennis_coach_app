import React from 'react';
import './AnalysisDashboard.css';
import Breadcrumb from './Breadcrumb';

interface AnalysisDashboardHeaderProps {
  videoFilename: string;
  hasServes: boolean;
  showEditMode: boolean;
  serveIndex?: number;
  serveCount?: number;
  onClose: () => void;
  onToggleEditMode: () => void;
}

const AnalysisDashboardHeader: React.FC<AnalysisDashboardHeaderProps> = ({
  videoFilename,
  hasServes,
  showEditMode,
  serveIndex,
  serveCount,
  onClose,
  onToggleEditMode,
}) => {
  const segments = [
    { label: 'Library', onClick: onClose },
    { label: videoFilename },
  ];

  if (hasServes && serveIndex != null && serveCount != null) {
    segments[1] = { label: videoFilename, onClick: onClose };
    segments.push({ label: `Serve ${serveIndex + 1} of ${serveCount}` });
  }

  return (
    <div className="analysis-dashboard__header">
      <Breadcrumb segments={segments} />
      <div className="analysis-dashboard__header-right">
        <h1 className="analysis-dashboard__page-title">Serve Analysis</h1>
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
