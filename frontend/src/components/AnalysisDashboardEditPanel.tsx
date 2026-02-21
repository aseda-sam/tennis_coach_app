import React, { useCallback, useState } from 'react';
import {
  ClearProposalsResponse,
  DetectionStatusResponse,
  ProposeResponse,
  ServeWindowProposal,
} from '../types/serveProposal';
import './AnalysisDashboard.css';

interface AnalysisDashboardEditPanelProps {
  proposals: ServeWindowProposal[];
  detectionStatus: DetectionStatusResponse | null;
  hasAnalysis: boolean;
  runDetection: (force?: boolean) => Promise<ProposeResponse>;
  clearProposals: () => Promise<ClearProposalsResponse>;
  acceptAllProposals: () => Promise<{ accepted: number; failed: number }>;
}

const AnalysisDashboardEditPanel: React.FC<AnalysisDashboardEditPanelProps> = ({
  proposals,
  detectionStatus,
  hasAnalysis,
  runDetection,
  clearProposals,
  acceptAllProposals,
}) => {
  const [isFindingServes, setIsFindingServes] = useState(false);
  const [findServesMessage, setFindServesMessage] = useState<string | null>(
    null
  );
  const [isAcceptingAll, setIsAcceptingAll] = useState(false);

  const handleFindServes = useCallback(async () => {
    if (!hasAnalysis) {
      setFindServesMessage('Please run body tracking first.');
      setTimeout(() => setFindServesMessage(null), 3000);
      return;
    }

    const hasExisting =
      detectionStatus &&
      (detectionStatus.pending_proposals > 0 ||
        detectionStatus.serve_windows > 0);

    if (hasExisting && detectionStatus) {
      if (
        detectionStatus.serve_windows > 0 &&
        detectionStatus.pending_proposals === 0
      ) {
        setFindServesMessage(
          'Serves already tagged. Delete them to re-detect.'
        );
        setTimeout(() => setFindServesMessage(null), 4000);
        return;
      }
      if (detectionStatus.pending_proposals > 0) {
        const confirmed = window.confirm(
          `You have ${detectionStatus.pending_proposals} pending proposal(s). Clear them and re-detect?`
        );
        if (!confirmed) return;
      }
    }

    setIsFindingServes(true);
    setFindServesMessage(null);
    try {
      const force = detectionStatus?.pending_proposals
        ? detectionStatus.pending_proposals > 0
        : false;
      const response = await runDetection(force);
      if (response.count === 0) {
        setFindServesMessage('No serves found in this video.');
      } else {
        setFindServesMessage(
          `Found ${response.count} serve${response.count > 1 ? 's' : ''}!`
        );
      }
      setTimeout(() => setFindServesMessage(null), 4000);
    } catch (err) {
      console.error('Failed to find serves:', err);
      setFindServesMessage('Failed to find serves. Please try again.');
      setTimeout(() => setFindServesMessage(null), 4000);
    } finally {
      setIsFindingServes(false);
    }
  }, [hasAnalysis, detectionStatus, runDetection]);

  const handleClearProposals = useCallback(async () => {
    if (proposals.length === 0) return;
    const confirmed = window.confirm('Clear all pending serve proposals?');
    if (!confirmed) return;
    try {
      await clearProposals();
      setFindServesMessage('Proposals cleared.');
      setTimeout(() => setFindServesMessage(null), 2000);
    } catch (err) {
      console.error('Failed to clear:', err);
    }
  }, [proposals.length, clearProposals]);

  const handleAcceptAll = useCallback(async () => {
    if (proposals.length === 0) return;
    setIsAcceptingAll(true);
    try {
      const result = await acceptAllProposals();
      if (result.failed > 0) {
        setFindServesMessage(
          `Accepted ${result.accepted}, ${result.failed} failed.`
        );
      } else {
        setFindServesMessage(`Accepted ${result.accepted} serves!`);
      }
      setTimeout(() => setFindServesMessage(null), 3000);
    } catch (err) {
      console.error('Failed to accept all:', err);
      setFindServesMessage('Failed to accept proposals.');
      setTimeout(() => setFindServesMessage(null), 3000);
    } finally {
      setIsAcceptingAll(false);
    }
  }, [proposals.length, acceptAllProposals]);

  return (
    <div className="analysis-dashboard__edit-panel">
      <h3 className="analysis-dashboard__edit-title">Edit Serves</h3>
      <div className="analysis-dashboard__edit-actions">
        {proposals.length === 0 ? (
          <button
            className="analysis-dashboard__action-btn analysis-dashboard__action-btn--find"
            onClick={handleFindServes}
            disabled={isFindingServes}
            type="button"
          >
            {isFindingServes ? 'Finding...' : 'Re-Detect Serves'}
          </button>
        ) : (
          <>
            <button
              className="analysis-dashboard__action-btn analysis-dashboard__action-btn--accept-all"
              onClick={handleAcceptAll}
              disabled={isAcceptingAll || proposals.length === 0}
              type="button"
            >
              {isAcceptingAll
                ? 'Accepting...'
                : `Accept All Proposals (${proposals.length})`}
            </button>
            <button
              className="analysis-dashboard__action-btn analysis-dashboard__action-btn--clear-all"
              onClick={handleClearProposals}
              type="button"
            >
              Clear All
            </button>
          </>
        )}
      </div>
      {findServesMessage && (
        <div className="analysis-dashboard__toast">{findServesMessage}</div>
      )}
    </div>
  );
};

export default AnalysisDashboardEditPanel;
