import React, { useState } from 'react';
import { ServeWindowProposal } from '../services/serveProposalApi';
import './ProposalRange.css';

interface ProposalRangeProps {
  proposal: ServeWindowProposal;
  duration: number;
  isSelected?: boolean;
  onClick?: () => void;
  onAccept?: () => void;
  onReject?: () => void;
  onEdit?: () => void;
}

const ProposalRange: React.FC<ProposalRangeProps> = ({
  proposal,
  duration,
  isSelected = false,
  onClick,
  onAccept,
  onReject,
  onEdit,
}) => {
  const [showActions, setShowActions] = useState(false);

  if (duration === 0) return null;

  const startPercent = (proposal.start_timestamp / duration) * 100;
  const endPercent = (proposal.end_timestamp / duration) * 100;
  const width = endPercent - startPercent;

  // Confidence-based color (higher = more orange/yellow)
  const confidenceColor = proposal.confidence > 0.7 ? '#f59e0b' : '#fbbf24'; // orange-500 or amber-400

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowActions(!showActions);
    onClick?.();
  };

  return (
    <div
      className={`proposal-range ${isSelected ? 'selected' : ''}`}
      style={{
        left: `${startPercent}%`,
        width: `${width}%`,
      }}
      onClick={handleClick}
      title={`Proposal: ${proposal.start_timestamp.toFixed(2)}s - ${proposal.end_timestamp.toFixed(2)}s (${Math.round(proposal.confidence * 100)}% confidence)`}
    >
      {/* Range band - dashed, semi-transparent */}
      <div
        className="proposal-range__band"
        style={{
          borderColor: confidenceColor,
          opacity: isSelected ? 0.6 : 0.4,
        }}
      />

      {/* Start marker */}
      <div className="proposal-range__start-marker" style={{ borderColor: confidenceColor }} />

      {/* End marker */}
      <div className="proposal-range__end-marker" style={{ borderColor: confidenceColor }} />

      {/* Confidence badge */}
      <div className="proposal-range__confidence-badge" style={{ backgroundColor: confidenceColor }}>
        {Math.round(proposal.confidence * 100)}%
      </div>

      {/* Actions menu */}
      {showActions && (
        <div className="proposal-range__actions" onClick={(e) => e.stopPropagation()}>
          <button
            className="proposal-range__action-btn proposal-range__action-btn--accept"
            onClick={(e) => {
              e.stopPropagation();
              setShowActions(false);
              onAccept?.();
            }}
          >
            Accept
          </button>
          <button
            className="proposal-range__action-btn proposal-range__action-btn--edit"
            onClick={(e) => {
              e.stopPropagation();
              setShowActions(false);
              onEdit?.();
            }}
          >
            Edit
          </button>
          <button
            className="proposal-range__action-btn proposal-range__action-btn--reject"
            onClick={(e) => {
              e.stopPropagation();
              setShowActions(false);
              onReject?.();
            }}
          >
            Reject
          </button>
        </div>
      )}

      {/* Tooltip on hover */}
      <div className="proposal-range__tooltip">
        <div className="tooltip-content">
          <div className="tooltip-header">
            <span>Proposal ({proposal.model_version})</span>
            <span>{Math.round(proposal.confidence * 100)}%</span>
          </div>
          <div className="tooltip-details">
            <div>{proposal.start_timestamp.toFixed(2)}s - {proposal.end_timestamp.toFixed(2)}s</div>
            {proposal.detection_features && (
              <>
                {proposal.detection_features.peak_wrist_height !== undefined && (
                  <div>Peak Height: {proposal.detection_features.peak_wrist_height.toFixed(2)}</div>
                )}
                {proposal.detection_features.peak_wrist_velocity !== undefined && (
                  <div>Peak Velocity: {Math.round(proposal.detection_features.peak_wrist_velocity)} px/s</div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProposalRange;
