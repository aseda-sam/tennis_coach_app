import React from 'react';
import { RotateCcw } from 'lucide-react';
import './AnalysisDashboard.css';
import Breadcrumb from './Breadcrumb';

interface AnalysisDashboardHeaderProps {
  videoFilename: string;
  hasServes: boolean;
  serveIndex?: number;
  serveCount?: number;
  onClose: () => void;
  isDemo?: boolean;
  onRestartTour?: () => void;
}

const AnalysisDashboardHeader: React.FC<AnalysisDashboardHeaderProps> = ({
  videoFilename,
  hasServes,
  serveIndex,
  serveCount,
  onClose,
  isDemo = false,
  onRestartTour,
}) => {
  const rootLabel = isDemo ? 'Demo' : 'Library';

  let segments;
  if (isDemo) {
    // Demo: skip the filename — show "Demo / Serve N of N" or just "Demo"
    segments =
      hasServes && serveIndex != null && serveCount != null
        ? [
            { label: rootLabel, onClick: onClose },
            { label: `Serve ${serveIndex + 1} of ${serveCount}` },
          ]
        : [{ label: rootLabel, onClick: onClose }];
  } else {
    segments = [
      { label: rootLabel, onClick: onClose },
      { label: videoFilename },
    ];
    if (hasServes && serveIndex != null && serveCount != null) {
      segments[1] = { label: videoFilename, onClick: onClose };
      segments.push({ label: `Serve ${serveIndex + 1} of ${serveCount}` });
    }
  }

  return (
    <div className="analysis-dashboard__header">
      <Breadcrumb segments={segments} />
      {isDemo && onRestartTour && (
        <button
          className="analysis-dashboard__restart-tour-btn"
          onClick={onRestartTour}
          type="button"
          aria-label="Restart tour"
        >
          <RotateCcw size={13} />
          Restart Tour
        </button>
      )}
    </div>
  );
};

export default AnalysisDashboardHeader;
