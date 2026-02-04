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
  const [isProcessing, setIsProcessing] = useState(false);

  if (duration === 0) return null;

  const startPercent = (proposal.start_timestamp / duration) * 100;
  const endPercent = (proposal.end_timestamp / duration) * 100;
  const width = endPercent - startPercent;

  // Confidence-based color
  // >= 70%: orange (high confidence)
  // 60-70%: amber (medium confidence)
  // < 60%: red/muted (low confidence - candidates for removal)
  const LOW_CONFIDENCE_THRESHOLD = 0.6;
  const isLowConfidence = proposal.confidence < LOW_CONFIDENCE_THRESHOLD;
  const confidenceColor = isLowConfidence
    ? '#ef4444' // red-500 for low confidence
    : proposal.confidence > 0.7
      ? '#f59e0b' // orange-500 for high confidence
      : '#fbbf24'; // amber-400 for medium confidence

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isProcessing) {
      setShowActions(!showActions);
      onClick?.();
    }
  };

  const handleAccept = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      await onAccept?.();
    } finally {
      setIsProcessing(false);
      setShowActions(false);
    }
  };

  const handleReject = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      await onReject?.();
    } finally {
      setIsProcessing(false);
      setShowActions(false);
    }
  };

  const handleEdit = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isProcessing) return;
    setIsProcessing(true);
    try {
      await onEdit?.();
    } finally {
      setIsProcessing(false);
      setShowActions(false);
    }
  };

  return (
    <div
      className={`proposal-range ${isSelected ? 'selected' : ''} ${showActions ? 'actions-visible' : ''} ${isLowConfidence ? 'low-confidence' : ''}`}
      style={{
        left: `${startPercent}%`,
        width: `${width}%`,
      }}
      onClick={handleClick}
      title={`Proposal: ${proposal.start_timestamp.toFixed(2)}s - ${proposal.end_timestamp.toFixed(2)}s (${Math.round(proposal.confidence * 100)}% confidence)${isLowConfidence ? ' - Low confidence' : ''}`}
    >
      {/* Range band - dashed, semi-transparent */}
      <div
        className="proposal-range__band"
        style={{
          borderColor: confidenceColor,
          opacity: isSelected || showActions ? 0.6 : 0.4,
        }}
      />

      {/* Start marker */}
      <div
        className="proposal-range__start-marker"
        style={{ borderColor: confidenceColor }}
      />

      {/* End marker */}
      <div
        className="proposal-range__end-marker"
        style={{ borderColor: confidenceColor }}
      />

      {/* Confidence badge */}
      <div
        className="proposal-range__confidence-badge"
        style={{ backgroundColor: confidenceColor }}
      >
        {Math.round(proposal.confidence * 100)}%
      </div>

      {/* Actions menu - shown when clicked */}
      {showActions && (
        <div
          className="proposal-range__actions"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="proposal-range__action-btn proposal-range__action-btn--accept"
            onClick={handleAccept}
            disabled={isProcessing}
          >
            {isProcessing ? '...' : 'Accept'}
          </button>
          <button
            className="proposal-range__action-btn proposal-range__action-btn--edit"
            onClick={handleEdit}
            disabled={isProcessing}
          >
            Edit
          </button>
          <button
            className="proposal-range__action-btn proposal-range__action-btn--reject"
            onClick={handleReject}
            disabled={isProcessing}
          >
            Reject
          </button>
        </div>
      )}

      {/* Tooltip on hover - HIDDEN when actions are visible */}
      {!showActions && (
        <div className="proposal-range__tooltip">
          <div className="tooltip-content">
            <div className="tooltip-header">
              <span>Proposal ({proposal.model_version})</span>
              <span>{Math.round(proposal.confidence * 100)}%</span>
            </div>
            <div className="tooltip-details">
              <div>
                {proposal.start_timestamp.toFixed(2)}s -{' '}
                {proposal.end_timestamp.toFixed(2)}s
              </div>
              {proposal.detection_features && (
                <>
                  {proposal.detection_features.peak_wrist_height !==
                    undefined && (
                    <div>
                      Peak Height:{' '}
                      {proposal.detection_features.peak_wrist_height.toFixed(2)}
                    </div>
                  )}
                  {proposal.detection_features.peak_wrist_velocity !==
                    undefined && (
                    <div>
                      Peak Velocity:{' '}
                      {Math.round(
                        proposal.detection_features.peak_wrist_velocity
                      )}{' '}
                      px/s
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProposalRange;
