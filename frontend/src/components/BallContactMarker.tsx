import React from 'react';
import { BallContact } from '../services/ballContactApi';
import './BallContactMarker.css';

interface BallContactMarkerProps {
  contact: BallContact;
  position: number; // Position as percentage (0-100) along the timeline
  isSelected?: boolean;
  onClick?: () => void;
  onAnalyzeClick?: () => void;
  showAnalysisButton?: boolean;
}

const BallContactMarker: React.FC<BallContactMarkerProps> = ({
  contact,
  position,
  isSelected = false,
  onClick,
  onAnalyzeClick,
  showAnalysisButton = true,
}) => {
  const formatElbowAngle = (angle?: number): string => {
    if (angle === undefined || angle === null) return 'N/A';
    return `${Math.round(angle)}°`;
  };

  const getAngleColor = (angle?: number): string => {
    if (angle === undefined || angle === null) return '#6b7280'; // gray-500

    // Color coding based on angle ranges
    if (angle < 90) return '#ef4444'; // red-500 - very bent
    if (angle < 120) return '#f59e0b'; // amber-500 - moderately bent
    if (angle < 150) return '#10b981'; // emerald-500 - good range
    return '#3b82f6'; // blue-500 - straight
  };

  const getAngleDescription = (angle?: number): string => {
    if (angle === undefined || angle === null) return 'Not analyzed';

    if (angle < 90) return 'Very bent';
    if (angle < 120) return 'Bent';
    if (angle < 150) return 'Good range';
    return 'Straight';
  };

  return (
    <div
      className={`ball-contact-marker ${isSelected ? 'selected' : ''}`}
      style={{ left: `${position}%` }}
      onClick={onClick}
    >
      <div className="marker-content">
        <div
          className="marker-dot"
          style={{ backgroundColor: getAngleColor(contact.elbow_angle) }}
        >
          <span className="marker-time">
            {Math.round(contact.video_timestamp * 10) / 10}s
          </span>
        </div>

        {contact.elbow_angle !== undefined && (
          <div className="angle-info">
            <div
              className="angle-value"
              style={{ color: getAngleColor(contact.elbow_angle) }}
            >
              {formatElbowAngle(contact.elbow_angle)}
            </div>
            <div className="angle-description">
              {getAngleDescription(contact.elbow_angle)}
            </div>
          </div>
        )}

        {showAnalysisButton && contact.elbow_angle === undefined && (
          <button
            className="analyze-button"
            onClick={(e) => {
              e.stopPropagation();
              onAnalyzeClick?.();
            }}
            title="Analyze posture"
          >
            Analyze
          </button>
        )}
      </div>

      <div className="marker-tooltip">
        <div className="tooltip-content">
          <div className="tooltip-header">
            <span className="contact-hand">
              {contact.contact_hand === 'left' ? 'Left' : 'Right'} hand
            </span>
            <span className="stroke-type">
              {contact.stroke_type || 'Unknown stroke'}
            </span>
          </div>

          {contact.stroke_subtype && (
            <div className="stroke-subtype">{contact.stroke_subtype}</div>
          )}

          {contact.elbow_angle !== undefined ? (
            <div className="posture-info">
              <div className="elbow-angle">
                <strong>Elbow Angle:</strong>{' '}
                {formatElbowAngle(contact.elbow_angle)}
              </div>
              <div className="angle-assessment">
                {getAngleDescription(contact.elbow_angle)}
              </div>
            </div>
          ) : (
            <div className="no-analysis">No posture analysis available</div>
          )}

          <div className="contact-details">
            <div>Time: {contact.video_timestamp.toFixed(1)}s</div>
            <div>Source: {contact.detection_source}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BallContactMarker;
