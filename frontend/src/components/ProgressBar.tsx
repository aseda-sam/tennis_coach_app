import React from 'react';
import './ProgressBar.css';

interface ProgressBarProps {
  progress?: number; // 0-100 (optional, ignored when indeterminate=true)
  status:
    | 'starting'
    | 'processing'
    | 'finalizing'
    | 'completed'
    | 'failed'
    | 'cancelled';
  showPercentage?: boolean;
  showStatus?: boolean;
  size?: 'small' | 'medium' | 'large';
  animated?: boolean;
  indeterminate?: boolean; // When true, shows animated indeterminate progress bar
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress = 0,
  status,
  showPercentage = true,
  showStatus = true,
  size = 'medium',
  animated = true,
  indeterminate = false,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'starting':
      case 'processing':
      case 'finalizing':
        return 'processing';
      case 'completed':
        return 'completed';
      case 'failed':
      case 'cancelled':
        return 'error';
      default:
        return 'processing';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'starting':
        return 'Starting analysis...';
      case 'processing':
        return 'Processing video...';
      case 'finalizing':
        return 'Finalizing results...';
      case 'completed':
        return 'Analysis complete!';
      case 'failed':
        return 'Analysis failed';
      case 'cancelled':
        return 'Analysis cancelled';
      default:
        return 'Processing...';
    }
  };

  const getProgressText = () => {
    if (status === 'starting') return '0%';
    if (status === 'finalizing') return '100%';
    if (status === 'completed') return '100%';
    if (status === 'failed' || status === 'cancelled') return `${progress}%`;
    return `${progress}%`;
  };

  return (
    <div className={`progress-bar-container ${size}`} role="progressbar">
      {showStatus && (
        <div className="progress-status">
          <span className={`status-text ${getStatusColor()}`}>
            {getStatusText()}
          </span>
        </div>
      )}

      <div
        className={`progress-bar ${getStatusColor()} ${animated ? 'animated' : ''} ${indeterminate ? 'indeterminate' : ''}`}
      >
        {indeterminate ? (
          <div
            className="progress-fill indeterminate-fill"
            data-testid="progress-fill"
          />
        ) : (
          <>
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
              data-testid="progress-fill"
            />
            {status === 'processing' && animated && (
              <div className="progress-shimmer" />
            )}
          </>
        )}
      </div>

      {showPercentage && !indeterminate && (
        <div className="progress-percentage">
          <span className="percentage-text">{getProgressText()}</span>
        </div>
      )}
    </div>
  );
};

export default ProgressBar;
