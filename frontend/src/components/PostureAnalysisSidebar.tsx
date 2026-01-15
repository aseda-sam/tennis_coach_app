import React, { useEffect, useState } from 'react';
import { usePostureAnalysis } from '../hooks/usePostureAnalysis';
import {
  BallContact,
  PostureAnalysisResponse,
} from '../services/ballContactApi';
import './PostureAnalysisSidebar.css';

interface PostureAnalysisSidebarProps {
  ballContacts: BallContact[];
  videoId: number;
  onContactSelect?: (contact: BallContact) => void;
  selectedContactId?: number;
  isVisible?: boolean;
  onClose?: () => void;
}

const PostureAnalysisSidebar: React.FC<PostureAnalysisSidebarProps> = ({
  ballContacts,
  videoId,
  onContactSelect,
  selectedContactId,
  isVisible = true,
  onClose,
}) => {
  const {
    isAnalyzing,
    analysisResults,
    error,
    analyzeContact,
    analyzeVideo,
    getContactAnalysis,
    clearError,
  } = usePostureAnalysis();

  const [showBatchActions, setShowBatchActions] = useState(false);

  // Load existing analysis results for all contacts
  useEffect(() => {
    const loadExistingResults = async () => {
      for (const contact of ballContacts) {
        if (contact.elbow_angle !== undefined) {
          // Contact already has analysis, fetch the full analysis data
          try {
            await getContactAnalysis(contact.id);
          } catch (err) {
            // Silently skip contacts without analysis data
          }
        }
      }
    };

    if (ballContacts.length > 0) {
      loadExistingResults();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ballContacts]);

  const handleAnalyzeContact = async (contact: BallContact) => {
    try {
      await analyzeContact(contact.id);
    } catch (err) {
      // Error handling is done by the analyzeContact function
    }
  };

  const handleAnalyzeAll = async () => {
    try {
      await analyzeVideo(videoId);
    } catch (err) {
      // Error handling is done by the analyzeVideo function
    }
  };

  const getAngleColor = (angle?: number): string => {
    if (angle === undefined || angle === null) return '#6b7280';

    if (angle < 90) return '#ef4444'; // red
    if (angle < 120) return '#f59e0b'; // amber
    if (angle < 150) return '#10b981'; // emerald
    return '#3b82f6'; // blue
  };

  const getAngleDescription = (angle?: number): string => {
    if (angle === undefined || angle === null) return 'Not analyzed';

    if (angle < 90) return 'Very bent';
    if (angle < 120) return 'Bent';
    if (angle < 150) return 'Good range';
    return 'Straight';
  };

  const formatTime = (timestamp: number): string => {
    return `${Math.round(timestamp * 10) / 10}s`;
  };

  const formatAngle = (angle?: number): string => {
    if (angle === undefined || angle === null) return 'N/A';
    return `${Math.round(angle)}°`;
  };

  const getAnalysisStatus = (
    contact: BallContact
  ): PostureAnalysisResponse | null => {
    return analysisResults[contact.id] || null;
  };

  const getContactAngle = (contact: BallContact): number | undefined => {
    const analysis = getAnalysisStatus(contact);
    return analysis?.elbow_angle ?? contact.elbow_angle;
  };

  const getContactAnalysisStatus = (contact: BallContact): string => {
    const analysis = getAnalysisStatus(contact);
    if (analysis) return analysis.analysis_status;
    if (contact.elbow_angle !== undefined) return 'success';
    return 'not_analyzed';
  };

  const analyzedContacts = ballContacts.filter(
    (contact) => getContactAnalysisStatus(contact) === 'success'
  );

  const unanalyzedContacts = ballContacts.filter(
    (contact) => getContactAnalysisStatus(contact) !== 'success'
  );

  if (!isVisible) return null;

  return (
    <div className="posture-analysis-sidebar">
      <div className="sidebar-header">
        <h3>Posture Analysis</h3>
        <div className="header-actions">
          <button
            className="batch-toggle"
            onClick={() => setShowBatchActions(!showBatchActions)}
            title="Batch actions"
          >
            ⚙️
          </button>
          {onClose && (
            <button className="close-button" onClick={onClose} title="Close">
              ✕
            </button>
          )}
        </div>
      </div>

      {showBatchActions && (
        <div className="batch-actions">
          <button
            className="analyze-all-button"
            onClick={handleAnalyzeAll}
            disabled={isAnalyzing || unanalyzedContacts.length === 0}
          >
            {isAnalyzing
              ? 'Analyzing...'
              : `Analyze All (${unanalyzedContacts.length})`}
          </button>
        </div>
      )}

      {error && (
        <div className="error-message">
          <span>{error}</span>
          <button onClick={clearError}>✕</button>
        </div>
      )}

      <div className="analysis-stats">
        <div className="stat">
          <span className="stat-label">Total Contacts:</span>
          <span className="stat-value">{ballContacts.length}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Analyzed:</span>
          <span className="stat-value success">{analyzedContacts.length}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Pending:</span>
          <span className="stat-value pending">
            {unanalyzedContacts.length}
          </span>
        </div>
      </div>

      <div className="contacts-list">
        {ballContacts.map((contact) => {
          const angle = getContactAngle(contact);
          const analysisStatus = getContactAnalysisStatus(contact);
          const isSelected = selectedContactId === contact.id;
          const isAnalyzingThis =
            isAnalyzing &&
            analysisResults[contact.id]?.analysis_status === 'failed';

          return (
            <div
              key={contact.id}
              className={`contact-item ${isSelected ? 'selected' : ''} ${analysisStatus}`}
              onClick={() => onContactSelect?.(contact)}
            >
              <div className="contact-header">
                <div className="contact-time">
                  {formatTime(contact.video_timestamp)}
                </div>
                <div className="contact-hand">
                  {contact.contact_hand === 'left' ? 'L' : 'R'}
                </div>
                <div className="contact-stroke">
                  {contact.stroke_type || 'Unknown'}
                </div>
              </div>

              <div className="contact-analysis">
                {analysisStatus === 'success' ? (
                  <div className="angle-display">
                    <div
                      className="angle-value"
                      style={{ color: getAngleColor(angle) }}
                    >
                      {formatAngle(angle)}
                    </div>
                    <div className="angle-description">
                      {getAngleDescription(angle)}
                    </div>
                  </div>
                ) : analysisStatus === 'failed' || isAnalyzingThis ? (
                  <div className="analysis-error">
                    {isAnalyzingThis ? 'Analyzing...' : 'Analysis failed'}
                  </div>
                ) : (
                  <button
                    className="analyze-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAnalyzeContact(contact);
                    }}
                    disabled={isAnalyzing}
                  >
                    Analyze
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {ballContacts.length === 0 && (
        <div className="empty-state">
          <p>No ball contacts found</p>
          <p className="empty-hint">
            Create ball contact markers to analyze posture
          </p>
        </div>
      )}
    </div>
  );
};

export default PostureAnalysisSidebar;
