import { useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { useAppConfig } from '../hooks/useAppConfig';
import { useServeBiomechanicsReport } from '../hooks/useServeBiomechanicsReport';
import { useServeProposals } from '../hooks/useServeProposals';
import { useServeWindows } from '../hooks/useServeWindows';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { PhaseWindow } from '../types/biomechanics';
import './AnalysisDashboard.css';
import { ArrowBackIcon } from './Icons';
import HeroView from './HeroView';
import KeyboardShortcutsModal from './KeyboardShortcutsModal';
import ProgressBar from './ProgressBar';
import ServeNavigator from './ServeNavigator';
import ServePhaseTimeline from './ServePhaseTimeline';

interface AnalysisDashboardProps {
  videoId: number;
  videoFilename: string;
  videoUrl: string;
  onClose: () => void;
}

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  elbow_angle_at_contact: 'Elbow Extension',
  knee_flexion_min_deg: 'Knee Flexion',
  trunk_rotation_at_contact: 'Trunk Rotation',
  trunk_rotation_at_cocking: 'Trunk Coil',
  shoulder_abduction_at_contact: 'Shoulder Position',
  shoulder_abduction_at_cocking: 'Arm Position',
  contact_point_height: 'Contact Height',
  hip_shoulder_separation_max: 'Hip-Shoulder Separation',
  hip_shoulder_separation_at_contact: 'Hip-Shoulder Sep. (Contact)',
  racket_drop_depth: 'Racket Drop',
  toss_peak_height: 'Toss Peak Height',
  kinetic_chain_correct: 'Kinetic Chain',
};

function formatMetricValue(value: number | null, unit: string): string {
  if (value === null) return 'N/A';
  if (unit === 'deg' || unit === 'degrees') return `${Math.round(value)}\u00b0`;
  if (unit === 'normalized') return value.toFixed(2);
  if (unit === 'ms') return `${value} ms`;
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2);
}

function findCurrentPhase(
  phases: PhaseWindow[],
  time: number
): PhaseWindow | undefined {
  return phases.find(
    (p) => time >= p.start_timestamp && time <= p.end_timestamp
  );
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({
  videoId,
  videoFilename,
  videoUrl,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const { config } = useAppConfig();
  const lowConfidenceThreshold =
    config.serve_detection.low_confidence_threshold;

  const { data: analysisStatus, refetch: refetchAnalysisStatus } =
    useVideoAnalysisStatus(videoId);

  const handleAnalysisComplete = useCallback(async () => {
    await refetchAnalysisStatus();
    queryClient.invalidateQueries({
      queryKey: ['video-analysis-status', videoId],
    });
    queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
  }, [refetchAnalysisStatus, queryClient, videoId]);

  const {
    analysisState,
    startAnalysis,
    isLoading: isAnalysisLoading,
  } = useAnalysisManager({
    videoId,
    autoRefresh: true,
    onAnalysisComplete: handleAnalysisComplete,
  });

  const handleFocusAnalysis = useCallback(async () => {
    try {
      await startAnalysis({
        analysis_type: 'pose_only',
        confidence_threshold: 0.5,
      });
    } catch {
      // Error handling is done by the hook
    }
  }, [startAnalysis]);

  const [currentServeIndex, setCurrentServeIndex] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [naturalScroll, setNaturalScroll] = useState(true);
  const [showEditMode, setShowEditMode] = useState(false);
  const [phaseDetailExpanded, setPhaseDetailExpanded] = useState(false);
  const [loopCurrentPhase, setLoopCurrentPhase] = useState(false);
  const [loopPhaseWindow, setLoopPhaseWindow] = useState<PhaseWindow | null>(
    null
  );

  // Edit mode state
  const [isFindingServes, setIsFindingServes] = useState(false);
  const [findServesMessage, setFindServesMessage] = useState<string | null>(
    null
  );
  const [isAcceptingAll, setIsAcceptingAll] = useState(false);

  const { serveWindows } = useServeWindows({
    videoId,
    filters: { video_id: videoId },
    autoRefresh: true,
  });

  const {
    proposals,
    detectionStatus,
    runDetection,
    clearProposals,
    acceptAllProposals,
  } = useServeProposals({
    videoId,
    autoRefresh: true,
    lowConfidenceThreshold,
  });

  const sortedServeWindows = useMemo(
    () =>
      [...serveWindows].sort((a, b) => a.start_timestamp - b.start_timestamp),
    [serveWindows]
  );

  const currentServe = sortedServeWindows[currentServeIndex] ?? null;

  const { data: biomechanicsReport } = useServeBiomechanicsReport(
    currentServe?.id ?? null
  );

  const phases = useMemo(
    () => biomechanicsReport?.phase_segmentation ?? [],
    [biomechanicsReport]
  );
  const metrics = useMemo(
    () => biomechanicsReport?.metrics ?? [],
    [biomechanicsReport]
  );
  const currentPhase = currentServe
    ? findCurrentPhase(phases, currentTime)
    : undefined;

  // Sync currentTime when switching serves
  useEffect(() => {
    if (currentServe) {
      setCurrentTime(currentServe.start_timestamp);
      setIsPlaying(false);
      setLoopCurrentPhase(false);
      setLoopPhaseWindow(null);
    }
  }, [currentServe?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Playback timer for stick figure mode (and video mode sync)
  useEffect(() => {
    if (!isPlaying || !currentServe) return;

    const interval = setInterval(() => {
      setCurrentTime((t) => {
        const next = t + 1 / 30;
        // When looping a phase, keep playback pinned to that phase window.
        if (loopCurrentPhase && loopPhaseWindow) {
          if (
            t < loopPhaseWindow.start_timestamp ||
            t > loopPhaseWindow.end_timestamp
          ) {
            return loopPhaseWindow.start_timestamp;
          }
          if (next >= loopPhaseWindow.end_timestamp) {
            return loopPhaseWindow.start_timestamp;
          }
          return next;
        }
        // Otherwise use serve bounds and stop at serve end
        if (next > currentServe.end_timestamp) {
          setIsPlaying(false);
          return currentServe.start_timestamp;
        }
        return next;
      });
    }, 1000 / 30);

    return () => clearInterval(interval);
  }, [isPlaying, currentServe, loopCurrentPhase, loopPhaseWindow]);

  const handlePlayPause = useCallback(() => {
    setIsPlaying((p) => !p);
  }, []);

  const handleSeek = useCallback(
    (t: number) => {
      if (!currentServe) return;
      setCurrentTime(
        Math.max(
          currentServe.start_timestamp,
          Math.min(currentServe.end_timestamp, t)
        )
      );
    },
    [currentServe]
  );

  const handleTimeUpdate = useCallback((t: number) => {
    setCurrentTime(t);
  }, []);

  const handlePhaseJump = useCallback(
    (phase: PhaseWindow) => {
      setCurrentTime(phase.start_timestamp);
      setIsPlaying(false);
      if (loopCurrentPhase) {
        setLoopPhaseWindow(phase);
      }
    },
    [loopCurrentPhase]
  );

  const handleContactJump = useCallback(
    (contactTimestamp: number) => {
      setCurrentTime(contactTimestamp);
      setIsPlaying(false);
      if (loopCurrentPhase) {
        const phaseAtContact = findCurrentPhase(phases, contactTimestamp);
        setLoopPhaseWindow(phaseAtContact ?? null);
      }
    },
    [loopCurrentPhase, phases]
  );

  const handleToggleLoopCurrentPhase = useCallback(() => {
    if (loopCurrentPhase) {
      setLoopCurrentPhase(false);
      setLoopPhaseWindow(null);
      return;
    }
    if (!currentPhase) return;
    setLoopCurrentPhase(true);
    setLoopPhaseWindow(currentPhase);
    setCurrentTime(currentPhase.start_timestamp);
  }, [loopCurrentPhase, currentPhase]);

  const handleServeNavigate = useCallback(
    (index: number) => {
      if (index >= 0 && index < sortedServeWindows.length) {
        setCurrentServeIndex(index);
      }
    },
    [sortedServeWindows.length]
  );

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
        e.preventDefault();
        setShowKeyboardShortcuts(true);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Edit mode handlers
  const handleFindServes = useCallback(async () => {
    if (!analysisStatus?.has_analysis) {
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
  }, [analysisStatus, detectionStatus, runDetection]);

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

  // Analysis in progress — show progress view
  const analysisInProgress =
    !analysisStatus?.has_analysis &&
    (analysisState.status === 'starting' ||
      analysisState.status === 'processing');

  const analysisIdle =
    !analysisStatus?.has_analysis && analysisState.status === 'idle';

  const analysisFailed =
    !analysisStatus?.has_analysis && analysisState.status === 'failed';

  const hasServes = sortedServeWindows.length > 0;
  const analysisJobActive =
    analysisState.status === 'starting' ||
    analysisState.status === 'processing';
  const serveWindowsProcessing =
    !!analysisStatus?.has_analysis && !hasServes && analysisJobActive;

  // Current phase metrics (for phase detail panel)
  const currentPhaseMetrics = useMemo(() => {
    if (!currentPhase) return metrics;
    return metrics.filter((m) => m.phase === currentPhase.phase);
  }, [metrics, currentPhase]);

  return (
    <div className="analysis-dashboard">
      {/* Header */}
      <div className="analysis-dashboard__header">
        <button
          className="analysis-dashboard__back-button"
          onClick={onClose}
          type="button"
        >
          <ArrowBackIcon size={16} />
          Back to Library
        </button>
        <div className="analysis-dashboard__header-right">
          <h1 className="analysis-dashboard__title">{videoFilename}</h1>
          {hasServes && (
            <button
              className="analysis-dashboard__edit-btn"
              onClick={() => setShowEditMode(!showEditMode)}
              type="button"
            >
              {showEditMode ? 'Done' : 'Edit Serves'}
            </button>
          )}
        </div>
      </div>

      {/* Analysis Required State */}
      {analysisIdle && (
        <div className="analysis-dashboard__empty-state">
          <h2 className="analysis-dashboard__empty-title">Ready to Analyze</h2>
          <p className="analysis-dashboard__empty-desc">
            Track body movement to detect serves and compute biomechanics
            automatically.
          </p>
          <button
            className="analysis-dashboard__action-btn analysis-dashboard__action-btn--primary"
            onClick={handleFocusAnalysis}
            disabled={isAnalysisLoading}
            type="button"
          >
            Track Body Movement
          </button>
        </div>
      )}

      {/* Analysis Failed */}
      {analysisFailed && (
        <div className="analysis-dashboard__empty-state analysis-dashboard__empty-state--error">
          <p className="analysis-dashboard__error-message">
            {analysisState.error || 'Analysis failed. Please try again.'}
          </p>
          <button
            className="analysis-dashboard__action-btn analysis-dashboard__action-btn--primary"
            onClick={handleFocusAnalysis}
            disabled={isAnalysisLoading}
            type="button"
          >
            Retry Body Tracking
          </button>
        </div>
      )}

      {/* Analysis In Progress */}
      {analysisInProgress && (
        <div className="analysis-dashboard__progress-state">
          <ProgressBar
            status={
              analysisState.status as
                | 'starting'
                | 'processing'
                | 'finalizing'
                | 'completed'
                | 'failed'
                | 'cancelled'
            }
            showPercentage={false}
            showStatus={true}
            size="medium"
            animated={true}
            indeterminate={true}
          />
          <p className="analysis-dashboard__progress-text">
            Analyzing your serve video...
          </p>
        </div>
      )}

      {/* Main Content: Focus-mode serve viewer */}
      {analysisStatus?.has_analysis && (
        <div className="analysis-dashboard__focus-view">
          {hasServes ? (
            <>
              {/* Hero View */}
              <HeroView
                videoUrl={videoUrl}
                videoId={videoId}
                serveStart={currentServe!.start_timestamp}
                serveEnd={currentServe!.end_timestamp}
                currentTime={currentTime}
                isPlaying={isPlaying}
                phaseLabel={currentPhase?.phase_label}
                onTimeUpdate={handleTimeUpdate}
                onPlayPause={handlePlayPause}
                onSeek={handleSeek}
              />

              {/* Serve Nav + Phase Timeline Row */}
              <div className="analysis-dashboard__nav-row">
                <ServeNavigator
                  serveWindows={sortedServeWindows}
                  currentIndex={currentServeIndex}
                  onNavigate={handleServeNavigate}
                />
                {phases.length > 0 && (
                  <div className="analysis-dashboard__timeline-wrapper">
                    <ServePhaseTimeline
                      phases={phases}
                      currentTime={currentTime}
                      serveStart={currentServe!.start_timestamp}
                      serveEnd={currentServe!.end_timestamp}
                      onSeek={handleSeek}
                      contactTimestamp={currentServe?.contact_timestamp ?? null}
                    />
                  </div>
                )}
              </div>

              {phases.length > 0 && (
                <div className="analysis-dashboard__phase-controls">
                  <div className="analysis-dashboard__current-stage">
                    <span className="analysis-dashboard__current-stage-label">
                      Current Stage
                    </span>
                    <strong className="analysis-dashboard__current-stage-value">
                      {currentPhase?.phase_label ?? 'Unknown'}
                    </strong>
                  </div>
                  <div className="analysis-dashboard__phase-chip-row">
                    {phases.map((phase) => (
                      <button
                        key={phase.phase}
                        type="button"
                        className={`analysis-dashboard__phase-chip ${
                          currentPhase?.phase === phase.phase
                            ? 'analysis-dashboard__phase-chip--active'
                            : ''
                        }`}
                        onClick={() => handlePhaseJump(phase)}
                      >
                        {phase.phase_label}
                      </button>
                    ))}
                  </div>
                  <div className="analysis-dashboard__phase-actions">
                    {currentServe?.contact_timestamp != null && (
                      <button
                        type="button"
                        className="analysis-dashboard__goto-contact-btn"
                        onClick={() =>
                          handleContactJump(currentServe.contact_timestamp!)
                        }
                      >
                        Go to Contact
                      </button>
                    )}
                    <button
                      type="button"
                      className={`analysis-dashboard__loop-btn ${
                        loopCurrentPhase
                          ? 'analysis-dashboard__loop-btn--active'
                          : ''
                      }`}
                      onClick={handleToggleLoopCurrentPhase}
                      disabled={!currentPhase}
                    >
                      {loopCurrentPhase
                        ? 'Looping Current Stage'
                        : 'Loop Current Stage'}
                    </button>
                  </div>
                </div>
              )}

              {/* Phase Detail (Progressive Disclosure) */}
              {currentPhase && (
                <div className="analysis-dashboard__phase-detail">
                  <button
                    className="analysis-dashboard__phase-detail-header"
                    onClick={() => setPhaseDetailExpanded(!phaseDetailExpanded)}
                    type="button"
                    aria-expanded={phaseDetailExpanded}
                  >
                    <span className="analysis-dashboard__phase-name">
                      {currentPhase.phase_label}
                    </span>
                    {currentPhaseMetrics.length > 0 && !phaseDetailExpanded && (
                      <span className="analysis-dashboard__phase-summary">
                        {METRIC_DISPLAY_NAMES[
                          currentPhaseMetrics[0].metric_name
                        ] ??
                          currentPhaseMetrics[0].metric_name.replace(/_/g, ' ')}
                        :{' '}
                        {formatMetricValue(
                          currentPhaseMetrics[0].value,
                          currentPhaseMetrics[0].unit
                        )}
                      </span>
                    )}
                    <span
                      className="analysis-dashboard__phase-chevron"
                      data-expanded={phaseDetailExpanded}
                    >
                      &#9662;
                    </span>
                  </button>
                  {phaseDetailExpanded && currentPhaseMetrics.length > 0 && (
                    <div className="analysis-dashboard__phase-metrics">
                      {currentPhaseMetrics.map((m) => (
                        <div
                          key={m.metric_name}
                          className="analysis-dashboard__metric-row"
                        >
                          <span className="analysis-dashboard__metric-label">
                            {METRIC_DISPLAY_NAMES[m.metric_name] ??
                              m.metric_name.replace(/_/g, ' ')}
                          </span>
                          <span className="analysis-dashboard__metric-value">
                            {formatMetricValue(m.value, m.unit)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Go Practice CTA */}
              <button
                className="analysis-dashboard__practice-cta"
                onClick={onClose}
                type="button"
              >
                Go Practice
              </button>
            </>
          ) : serveWindowsProcessing ? (
            <div className="analysis-dashboard__progress-state">
              <ProgressBar
                status={
                  analysisState.status as
                    | 'starting'
                    | 'processing'
                    | 'finalizing'
                    | 'completed'
                    | 'failed'
                    | 'cancelled'
                }
                showPercentage={false}
                showStatus={true}
                size="medium"
                animated={true}
                indeterminate={true}
              />
              <p className="analysis-dashboard__progress-text">
                Processing serve windows...
              </p>
            </div>
          ) : (
            <div className="analysis-dashboard__no-serves">
              <p>No serves detected yet.</p>
              <p className="analysis-dashboard__no-serves-hint">
                Serves are detected automatically during analysis. If no serves
                were found, try re-running detection or adding them manually.
              </p>
              <button
                className="analysis-dashboard__action-btn analysis-dashboard__action-btn--find"
                onClick={handleFindServes}
                disabled={isFindingServes}
                type="button"
              >
                {isFindingServes ? 'Finding...' : 'Find Serve Windows'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Edit Serves Mode (secondary) */}
      {showEditMode && (
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
      )}

      {/* Keyboard Shortcuts */}
      <button
        className="analysis-dashboard__shortcuts-hint"
        onClick={() => setShowKeyboardShortcuts(true)}
        type="button"
        title="Keyboard shortcuts"
      >
        <kbd>?</kbd> Keyboard Shortcuts
      </button>

      <KeyboardShortcutsModal
        isOpen={showKeyboardShortcuts}
        onClose={() => setShowKeyboardShortcuts(false)}
        naturalScroll={naturalScroll}
        onNaturalScrollChange={setNaturalScroll}
      />
    </div>
  );
};

export default AnalysisDashboard;
