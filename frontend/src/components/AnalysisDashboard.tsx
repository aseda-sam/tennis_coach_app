import React, { useState } from 'react';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import './AnalysisDashboard.css';
import { ArrowBackIcon } from './Icons';
import VideoPlayer from './VideoPlayer';

interface AnalysisDashboardProps {
  videoId: number;
  videoFilename: string;
  videoUrl: string;
  onClose: () => void;
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({
  videoId,
  videoFilename,
  videoUrl,
  onClose,
}) => {
  const [aspectRatioMode, setAspectRatioMode] = useState<
    'cover' | 'contain' | 'auto'
  >('contain');

  // Use React Query hook for analysis status (with caching)
  const { data: analysisStatus } = useVideoAnalysisStatus(videoId);

  // Analysis state for the new unified system

  return (
    <div className="analysis-dashboard">
      <div className="dashboard-header">
        <button className="back-btn" onClick={onClose}>
          <ArrowBackIcon size={18} />
          Back to Videos
        </button>
        <h1 className="dashboard-title">{videoFilename}</h1>
        <div className="upload-info">Uploaded recently</div>
      </div>

      <div className="dashboard-content">
        <div className="video-section">
          {/* Aspect Ratio Mode Selector */}
          <div className="aspect-ratio-controls">
            <label htmlFor="aspect-ratio-mode">Video Display Mode:</label>
            <select
              id="aspect-ratio-mode"
              value={aspectRatioMode}
              onChange={(e) =>
                setAspectRatioMode(
                  e.target.value as 'cover' | 'contain' | 'auto'
                )
              }
              className="aspect-ratio-select"
            >
              <option value="contain">Fit with Black Bars (Default)</option>
              <option value="cover">Crop to Fit</option>
              <option value="auto">Auto Adjust</option>
            </select>
          </div>

          <VideoPlayer
            videoUrl={videoUrl}
            title={videoFilename}
            showControls={true}
            aspectRatioMode={aspectRatioMode}
            videoId={videoId}
            showPostureAnalysis={true}
            hasPoseData={analysisStatus?.has_analysis || false}
          />
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;
