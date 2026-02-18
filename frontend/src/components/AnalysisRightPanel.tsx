import React from 'react';
import ServeWindowsPanel from './ServeWindowsPanel';
import './AnalysisRightPanel.css';

interface AnalysisRightPanelProps {
  videoId: number;
  videoFilename: string;
  analysisStatus?: {
    has_analysis?: boolean;
  };
  onContactClick?: (serveWindowId: number) => void;
  isDemo?: boolean;
}

const AnalysisRightPanel: React.FC<AnalysisRightPanelProps> = ({
  videoId,
  analysisStatus,
  onContactClick,
  isDemo = false,
}) => {
  return (
    <div className="analysis-right-panel">
      {analysisStatus?.has_analysis && (
        <ServeWindowsPanel
          videoId={videoId}
          onServeWindowClick={onContactClick}
          isDemo={isDemo}
        />
      )}
    </div>
  );
};

export default AnalysisRightPanel;
