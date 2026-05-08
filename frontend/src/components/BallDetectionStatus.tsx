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

  return (
    <div className="ball-detection-status">
      <div className="ball-detection-status__row">
        {hasRate && rate !== null ? (
          <span
            className="ball-detection-status__badge"
            title={`Ball detected in ${Math.round(rate * 100)}% of frames`}
          >
            <span
              className="ball-detection-status__dot"
              style={{ backgroundColor: dotColor }}
            />
            Ball tracking {Math.round(rate * 100)}%
          </span>
        ) : (
          <span className="ball-detection-status__badge ball-detection-status__badge--empty">
            Ball tracking not run
          </span>
        )}
        {isStale && (
          <span
            className="ball-detection-status__stale"
            title="Serve windows have changed since the last ball detection run"
          >
            Stale
          </span>
        )}
        <button
          type="button"
          className="ball-detection-status__rerun"
          disabled={isRunning}
          onClick={() => startBallDetection.mutate(videoId)}
        >
          {isRunning ? 'Running…' : hasRate ? 'Re-run' : 'Run ball detection'}
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
