import React, { useEffect, useState } from 'react';
import { videoApi } from '../services/api';
import './AnalysisDashboard.css';
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
  const [analysisStatus, setAnalysisStatus] = useState<{
    has_analysis: boolean;
    analysis_types: string[];
  } | null>(null);

  // Fetch analysis status
  useEffect(() => {
    const fetchAnalysisStatus = async () => {
      try {
        const status = await videoApi.getVideoAnalysisStatus(videoId);
        setAnalysisStatus(status);
      } catch (error) {
        console.debug('No analysis status available for video:', videoId);
        setAnalysisStatus({
          has_analysis: false,
          analysis_types: [],
        });
      }
    };

    fetchAnalysisStatus();
  }, [videoId]);

  // Analysis state for the new unified system

  return (
    <div className="analysis-dashboard">
      <div className="dashboard-header">
        <button className="back-btn" onClick={onClose}>
          <span className="back-icon">←</span>
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
