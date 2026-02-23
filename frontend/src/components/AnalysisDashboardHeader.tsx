import React from 'react';
import './AnalysisDashboard.css';
import Breadcrumb from './Breadcrumb';

interface AnalysisDashboardHeaderProps {
  videoFilename: string;
  hasServes: boolean;
  serveIndex?: number;
  serveCount?: number;
  onClose: () => void;
}

const AnalysisDashboardHeader: React.FC<AnalysisDashboardHeaderProps> = ({
  videoFilename,
  hasServes,
  serveIndex,
  serveCount,
  onClose,
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
    </div>
  );
};

export default AnalysisDashboardHeader;
