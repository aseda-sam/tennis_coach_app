import React from 'react';
import {
  useStartBallDetection,
  useVideoAnalysisStatus,
} from '../hooks/useVideos';
import { getApiErrorMessage } from '../utils/apiError';
import './BallDetectionStatus.css';

interface BallDetectionStatusProps {
  videoId: number;
  isDemo?: boolean;
}

const BallDetectionStatus: React.FC<BallDetectionStatusProps> = ({
  videoId,
  isDemo = false,
}) => {
  const { data: analysisStatus } = useVideoAnalysisStatus(videoId);
  const startBallDetection = useStartBallDetection();

  if (isDemo) return null;

  const hasRate =
    analysisStatus?.has_ball_detection &&
    analysisStatus.ball_detection_rate !== null;
  const rate = analysisStatus?.ball_detection_rate ?? null;
  const isStale = !!analysisStatus?.is_ball_detection_stale;
  const isRunning =
    startBallDetection.isPending ||
    analysisStatus?.ball_detection_status === 'processing' ||
    analysisStatus?.ball_detection_status === 'queued';

  const dotColor =
    rate === null
      ? 'var(--color-text-muted)'
      : rate >= 0.5
        ? 'var(--color-success)'
        : rate >= 0.25
          ? 'var(--color-warning)'
          : 'var(--color-error)';

  const buttonLabel = isRunning
    ? 'Running…'
    : hasRate
      ? 'Re-Run'
      : 'Run Ball Detection';

  return (
    <div className="ball-detection-status">
      <div className="ball-detection-status__header">
        <span className="ball-detection-status__label">Ball Tracking</span>
        <div className="ball-detection-status__badges">
          <span
            className="ball-detection-status__scope"
            title="Ball tracking runs across the entire video, not just the current serve"
          >
            Whole Video
          </span>
          {isStale && (
            <span
              className="ball-detection-status__stale"
              title="Serve windows have changed since the last ball detection run"
            >
              Stale
            </span>
          )}
        </div>
      </div>
      <div className="ball-detection-status__body">
        <span className="ball-detection-status__value">
          <span
            className="ball-detection-status__dot"
            style={{ backgroundColor: dotColor }}
          />
          {hasRate && rate !== null ? (
            <span className="ball-detection-status__rate">
              {Math.round(rate * 100)}%
            </span>
          ) : (
            <span className="ball-detection-status__rate--empty">Not run</span>
          )}
        </span>
        <button
          type="button"
          className="ball-detection-status__rerun"
          disabled={isRunning}
          onClick={() => startBallDetection.mutate(videoId)}
        >
          {buttonLabel}
        </button>
      </div>
      {startBallDetection.isError && (
        <p className="ball-detection-status__error">
          {getApiErrorMessage(
            startBallDetection.error,
            'Failed to start ball detection'
          )}
        </p>
      )}
    </div>
  );
};

export default BallDetectionStatus;
