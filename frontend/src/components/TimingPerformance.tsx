import React from 'react';
import {
  AnalyticsIcon,
  FrameExtractionIcon,
  PoseDetectionIcon,
  VideoAnnotationIcon,
  VideoIcon,
} from './Icons';
import './TimingPerformance.css';

interface TimingData {
  frame_extraction?: number;
  pose_detection?: number;
  frame_annotation?: number;
  video_creation?: number;
  total_analysis?: number;
}

interface TimingPerformanceProps {
  timing?: TimingData;
  processingTime?: number;
}

const TimingPerformance: React.FC<TimingPerformanceProps> = ({
  timing,
  processingTime,
}) => {
  const formatTime = (seconds: number): string => {
    if (seconds < 1) {
      return `${(seconds * 1000).toFixed(0)}ms`;
    }
    return `${seconds.toFixed(2)}s`;
  };

  const getStageIcon = (stageName: string): React.ReactNode => {
    switch (stageName) {
      case 'frame_extraction':
        return <FrameExtractionIcon size={16} />;
      case 'pose_detection':
        return <PoseDetectionIcon size={16} />;
      case 'frame_annotation':
        return <VideoAnnotationIcon size={16} />;
      case 'video_creation':
        return <VideoIcon size={16} />;
      case 'total_analysis':
        return <AnalyticsIcon size={16} />;
      default:
        return <AnalyticsIcon size={16} />;
    }
  };

  const getStageDisplayName = (stageName: string): string => {
    const names: Record<string, string> = {
      frame_extraction: 'Frame Extraction',
      pose_detection: 'Pose Detection',
      frame_annotation: 'Frame Annotation',
      video_creation: 'Video Creation',
      total_analysis: 'Total Analysis',
    };
    return (
      names[stageName] ||
      stageName.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
    );
  };

  // Calculate total time from timing breakdown or use processing time
  const totalTime = timing?.total_analysis || processingTime || 0;

  // Get all timing stages, excluding total_analysis
  const timingStages = timing
    ? Object.entries(timing).filter(([key]) => key !== 'total_analysis')
    : [];

  // If no detailed timing, show simple processing time
  if (!timing || timingStages.length === 0) {
    return (
      <div className="timing-performance" data-testid="timing-performance">
        <div className="timing-header" data-testid="timing-header">
          <h4>Processing Time</h4>
          <div className="total-time">{formatTime(totalTime)}</div>
        </div>
        <div className="simple-timing">
          <div className="timing-stage">
            <div className="stage-info">
              <span
                className="stage-icon"
                data-testid="stage-icon-total_analysis"
              >
                {getStageIcon('total_analysis')}
              </span>
              <span className="stage-name">Total Processing</span>
            </div>
            <div className="stage-timing">
              <div className="stage-duration">{formatTime(totalTime)}</div>
              <div className="stage-percentage">100%</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="timing-performance" data-testid="timing-performance">
      <div className="timing-header" data-testid="timing-header">
        <h4>Performance Breakdown</h4>
        <div className="total-time">{formatTime(totalTime)}</div>
      </div>

      <div className="timing-breakdown" data-testid="timing-breakdown">
        {timingStages.map(([stageKey, stageTime]) => {
          const percentage = totalTime > 0 ? (stageTime / totalTime) * 100 : 0;

          return (
            <div key={stageKey} className="timing-stage">
              <div className="stage-progress">
                <div
                  className="progress-bar"
                  style={{ width: `${percentage}%` }}
                />
              </div>

              <div className="stage-info">
                <span
                  className="stage-icon"
                  data-testid={`stage-icon-${stageKey}`}
                >
                  {getStageIcon(stageKey)}
                </span>
                <span className="stage-name">
                  {getStageDisplayName(stageKey)}
                </span>
              </div>

              <div className="stage-timing">
                <div className="stage-duration">{formatTime(stageTime)}</div>
                <div className="stage-percentage">{percentage.toFixed(1)}%</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="timing-insights" data-testid="timing-insights">
        <div className="insight-item">
          <span className="insight-icon" aria-hidden="true">
            <AnalyticsIcon size={16} />
          </span>
          <span className="insight-text">
            {totalTime > 10
              ? 'Analysis completed in a reasonable time'
              : 'Fast analysis processing'}
          </span>
        </div>

        {timing.pose_detection && (
          <div className="insight-item">
            <span className="insight-icon" aria-hidden="true">
              <PoseDetectionIcon size={16} />
            </span>
            <span className="insight-text">
              Pose detection took{' '}
              {((timing.pose_detection / totalTime) * 100).toFixed(1)}% of total
              time
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default TimingPerformance;
