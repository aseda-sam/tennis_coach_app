import { useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { useServeBiomechanicsReport } from '../hooks/useServeBiomechanicsReport';
import { useServePlayback } from '../hooks/useServePlayback';
import { useServeProposals } from '../hooks/useServeProposals';
import { useServeWindows } from '../hooks/useServeWindows';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { MetricValue, PhaseWindow } from '../types/biomechanics';
import './AnalysisDashboard.css';
import AnalysisDashboardHeader from './AnalysisDashboardHeader';
import DetectionDetailsPanel from './DetectionDetailsPanel';
import AnalysisViewToggle, { ViewMode } from './AnalysisViewToggle';
import ErrorBoundary from './ErrorBoundary';
import HeroView from './HeroView';
import KeyboardShortcutsModal from './KeyboardShortcutsModal';
import ProgressBar from './ProgressBar';
import ServePhaseTimeline from './ServePhaseTimeline';
import ServeThumbnailStrip from './ServeThumbnailStrip';

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  knee_flexion_min_deg: 'Knee Flexion',
  toss_peak_height: 'Toss Peak Height',
  toss_laterality: 'Toss Position',
};

function formatMetricValue(value: number | null, unit: string): string {
  if (value === null) return 'N/A';
  if (unit === 'deg' || unit === 'degrees') return `${Math.round(value)}\u00b0`;
  if (unit === 'normalized') return value.toFixed(2);
  if (unit === 'ms') return `${value} ms`;
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2);
}

const SPEED_OPTIONS = [0.25, 0.5, 1] as const;

interface AnalysisDashboardProps {
  videoId: number;
  videoFilename: string;
  videoUrl: string;
  onClose: () => void;
}

function findCurrentPhase(
  phases: PhaseWindow[],
  time: number
): PhaseWindow | undefined {
  // Half-open intervals [start, end) so boundary time belongs to the next phase.
  // Last phase uses closed interval since nothing follows it.
  return phases.find(
    (p, i) =>
      time >= p.start_timestamp &&
      (i === phases.length - 1
        ? time <= p.end_timestamp
        : time < p.end_timestamp)
  );
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({
  videoId,
  videoFilename,
  videoUrl,
  onClose,
}) => {
  const queryClient = useQueryClient();

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

  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [naturalScroll, setNaturalScroll] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('analysis-focus');

  // No-serves find state (mutually exclusive with edit panel)
  const [isFindingServes, setIsFindingServes] = useState(false);

  const { serveWindows } = useServeWindows({
    videoId,
    filters: { video_id: videoId },
    autoRefresh: true,
  });

  const { runDetection } = useServeProposals({
    videoId,
    autoRefresh: true,
  });

  const sortedServeWindows = useMemo(
    () =>
      [...serveWindows].sort((a, b) => a.start_timestamp - b.start_timestamp),
    [serveWindows]
  );

  const {
    currentServeIndex,
    currentServe,
    currentTime,
    isPlaying,
    loopCurrentPhase,
    loopPhaseWindow,
    playbackSpeed,
    handlePlayPause,
    handleSeek,
    handleTimeUpdate,
    handlePhaseJump,
    handleContactJump,
    handleToggleLoopCurrentPhase,
    handleServeNavigate,
    setPlaybackSpeed,
  } = useServePlayback({ sortedServeWindows });

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
  // Track which phase tab was explicitly clicked — gives instant highlight
  // without waiting for the video seek to complete.
  const [activePhaseKey, setActivePhaseKey] = useState<string | null>(null);

  // Clear override when playback starts (natural phase transitions take over)
  useEffect(() => {
    if (isPlaying) setActivePhaseKey(null);
  }, [isPlaying]);

  const timeBasedPhase = currentServe
    ? findCurrentPhase(phases, currentTime)
    : undefined;
  const currentPhase = activePhaseKey
    ? (phases.find((p) => p.phase === activePhaseKey) ?? timeBasedPhase)
    : timeBasedPhase;
  // Wrap playback handlers to capture the selected phase for instant tab highlight
  const wrappedPhaseJump = useCallback(
    (phase: PhaseWindow) => {
      setActivePhaseKey(phase.phase);
      handlePhaseJump(phase);
    },
    [handlePhaseJump]
  );

  const handleContactJumpWithPhases = useCallback(
    (contactTimestamp: number) => {
      const phaseAtContact = phases.find(
        (p) =>
          contactTimestamp >= p.start_timestamp &&
          contactTimestamp <= p.end_timestamp
      );
      setActivePhaseKey(phaseAtContact?.phase ?? null);
      handleContactJump(contactTimestamp, phases);
    },
    [handleContactJump, phases]
  );

  const handleToggleLoopWithPhase = useCallback(() => {
    handleToggleLoopCurrentPhase(currentPhase);
  }, [handleToggleLoopCurrentPhase, currentPhase]);

  const handleMetricClick = useCallback(
    (metric: MetricValue) => {
      if (metric.timestamp != null) {
        handleSeek(metric.timestamp);
      }
    },
    [handleSeek]
  );

  // Metrics with timestamps, for canvas annotations
  const annotationMetrics = useMemo(
    () => metrics.filter((m) => m.timestamp != null && m.value != null),
    [metrics]
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

  // Find serves handler for the no-serves fallback state
  const handleFindServes = useCallback(async () => {
    if (!analysisStatus?.has_analysis) return;

    setIsFindingServes(true);
    try {
      await runDetection(false);
    } catch (err) {
      console.error('Failed to find serves:', err);
    } finally {
      setIsFindingServes(false);
    }
  }, [analysisStatus, runDetection]);

  // Analysis in progress -- show progress view
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

  return (
    <div className="analysis-dashboard">
      {/* Header */}
      <AnalysisDashboardHeader
        videoFilename={videoFilename}
        hasServes={hasServes}
        serveIndex={hasServes ? currentServeIndex : undefined}
        serveCount={hasServes ? sortedServeWindows.length : undefined}
        onClose={onClose}
      />

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

      {/* View Mode Toggle */}
      {analysisStatus?.has_analysis && hasServes && (
        <div className="analysis-dashboard__view-toggle-row">
          <AnalysisViewToggle
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        </div>
      )}

      {/* Serve Thumbnail Strip */}
      {analysisStatus?.has_analysis && hasServes && (
        <ServeThumbnailStrip
          serveWindows={sortedServeWindows}
          currentIndex={currentServeIndex}
          videoUrl={videoUrl}
          onNavigate={handleServeNavigate}
        />
      )}

      {/* Main Content: Focus-mode serve viewer */}
      {analysisStatus?.has_analysis && (
        <div className="analysis-dashboard__focus-view">
          {hasServes ? (
            <>
              {/* Hero View (left column at desktop) */}
              <ErrorBoundary fallbackMessage="Video player encountered an error.">
                <HeroView
                  videoUrl={videoUrl}
                  videoId={videoId}
                  serveStart={currentServe!.start_timestamp}
                  serveEnd={currentServe!.end_timestamp}
                  currentTime={currentTime}
                  isPlaying={isPlaying}
                  phaseLabel={currentPhase?.phase_label}
                  viewMode={viewMode}
                  onTimeUpdate={handleTimeUpdate}
                  onPlayPause={handlePlayPause}
                  onSeek={handleSeek}
                  annotations={annotationMetrics}
                  playbackSpeed={playbackSpeed}
                />
              </ErrorBoundary>

              {/* Phase navigation — only when phases exist */}
              {phases.length > 0 && (
                <>
                  {/* Phase tab strip */}
                  <div
                    className="analysis-dashboard__phase-tabs"
                    role="tablist"
                  >
                    {phases.map((phase) => (
                      <button
                        key={phase.phase}
                        type="button"
                        className={`analysis-dashboard__phase-tab${
                          currentPhase?.phase === phase.phase
                            ? ' analysis-dashboard__phase-tab--active'
                            : ''
                        }`}
                        role="tab"
                        aria-selected={currentPhase?.phase === phase.phase}
                        onClick={() => wrappedPhaseJump(phase)}
                      >
                        {phase.phase_label}
                      </button>
                    ))}
                    {currentServe!.contact_timestamp != null && (
                      <button
                        type="button"
                        className="analysis-dashboard__phase-tab analysis-dashboard__phase-tab--contact"
                        role="tab"
                        aria-selected={false}
                        onClick={() =>
                          handleContactJumpWithPhases(
                            currentServe!.contact_timestamp!
                          )
                        }
                      >
                        &#x2299; Contact
                      </button>
                    )}
                  </div>

                  {/* Slim timeline scrubber */}
                  <div className="analysis-dashboard__timeline-inset">
                    <ServePhaseTimeline
                      phases={phases}
                      currentTime={currentTime}
                      serveStart={currentServe!.start_timestamp}
                      serveEnd={currentServe!.end_timestamp}
                      onSeek={handleSeek}
                      contactTimestamp={currentServe!.contact_timestamp ?? null}
                      hideLabels
                      activePhase={currentPhase?.phase}
                    />
                  </div>

                  {/* Playback controls: speed + loop */}
                  <div className="analysis-dashboard__playback-controls">
                    <div
                      className="analysis-dashboard__speed-selector"
                      role="group"
                      aria-label="Playback speed"
                    >
                      {SPEED_OPTIONS.map((speed) => (
                        <button
                          key={speed}
                          type="button"
                          className={`analysis-dashboard__speed-btn${
                            playbackSpeed === speed
                              ? ' analysis-dashboard__speed-btn--active'
                              : ''
                          }`}
                          onClick={() => setPlaybackSpeed(speed)}
                        >
                          {speed}x
                        </button>
                      ))}
                    </div>
                    <button
                      type="button"
                      className={`analysis-dashboard__loop-btn${
                        loopCurrentPhase
                          ? ' analysis-dashboard__loop-btn--active'
                          : ''
                      }`}
                      onClick={handleToggleLoopWithPhase}
                      disabled={!currentPhase}
                    >
                      &#x21bb;{' '}
                      {loopCurrentPhase
                        ? `Looping ${loopPhaseWindow?.phase_label ?? 'Phase'}`
                        : `Loop ${currentPhase?.phase_label ?? 'Phase'}`}
                    </button>
                  </div>
                </>
              )}

              {/* Metrics */}
              {metrics.length > 0 && (
                <div className="analysis-dashboard__metrics-strip">
                  {metrics.map((m) => {
                    const isClickable = m.timestamp != null && m.value != null;
                    return (
                      <div
                        key={m.metric_name}
                        className={`analysis-dashboard__metric-card${isClickable ? ' analysis-dashboard__metric-card--clickable' : ''}`}
                        onClick={
                          isClickable ? () => handleMetricClick(m) : undefined
                        }
                        role={isClickable ? 'button' : undefined}
                        tabIndex={isClickable ? 0 : undefined}
                        onKeyDown={
                          isClickable
                            ? (e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  handleMetricClick(m);
                                }
                              }
                            : undefined
                        }
                      >
                        <span className="analysis-dashboard__metric-label">
                          {METRIC_DISPLAY_NAMES[m.metric_name] ??
                            m.metric_name.replace(/_/g, ' ')}
                        </span>
                        <span className="analysis-dashboard__metric-value">
                          {formatMetricValue(m.value, m.unit)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Detection Details (stats for nerds) */}
              {biomechanicsReport?.detection_meta && (
                <DetectionDetailsPanel
                  detectionMeta={biomechanicsReport.detection_meta}
                  currentTime={currentTime}
                  serveStart={currentServe!.start_timestamp}
                  onSeek={handleSeek}
                />
              )}
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
