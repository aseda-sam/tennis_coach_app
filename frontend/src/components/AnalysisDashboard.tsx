import { useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { useAppConfig } from '../hooks/useAppConfig';
import { useServeBiomechanicsReport } from '../hooks/useServeBiomechanicsReport';
import { useServePlayback } from '../hooks/useServePlayback';
import { useServeProposals } from '../hooks/useServeProposals';
import { useServeWindows } from '../hooks/useServeWindows';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { MetricValue, PhaseWindow } from '../types/biomechanics';
import './AnalysisDashboard.css';
import AnalysisDashboardEditPanel from './AnalysisDashboardEditPanel';
import AnalysisDashboardHeader from './AnalysisDashboardHeader';
import AnalysisDashboardMetrics from './AnalysisDashboardMetrics';
import AnalysisViewToggle, { ViewMode } from './AnalysisViewToggle';
import ErrorBoundary from './ErrorBoundary';
import HeroView from './HeroView';
import KeyboardShortcutsModal from './KeyboardShortcutsModal';
import ProgressBar from './ProgressBar';
import ServeThumbnailStrip from './ServeThumbnailStrip';

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

  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [naturalScroll, setNaturalScroll] = useState(true);
  const [showEditMode, setShowEditMode] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('analysis-focus');

  // No-serves find state (mutually exclusive with edit panel)
  const [isFindingServes, setIsFindingServes] = useState(false);

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

  const {
    currentServeIndex,
    currentServe,
    currentTime,
    isPlaying,
    loopCurrentPhase,
    handlePlayPause,
    handleSeek,
    handleTimeUpdate,
    handlePhaseJump,
    handleContactJump,
    handleToggleLoopCurrentPhase,
    handleServeNavigate,
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
  const currentPhase = currentServe
    ? findCurrentPhase(phases, currentTime)
    : undefined;
  const filteredMetrics = useMemo(() => {
    if (!currentPhase) return metrics;
    return metrics.filter(
      (m) => m.phase === currentPhase.phase || m.phase === null
    );
  }, [metrics, currentPhase]);

  // Wrap playback handlers that need phases/currentPhase from this scope
  const handleContactJumpWithPhases = useCallback(
    (contactTimestamp: number) => {
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
      const force = detectionStatus?.pending_proposals
        ? detectionStatus.pending_proposals > 0
        : false;
      await runDetection(force);
    } catch (err) {
      console.error('Failed to find serves:', err);
    } finally {
      setIsFindingServes(false);
    }
  }, [analysisStatus, detectionStatus, runDetection]);

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
        showEditMode={showEditMode}
        serveIndex={hasServes ? currentServeIndex : undefined}
        serveCount={hasServes ? sortedServeWindows.length : undefined}
        onClose={onClose}
        onToggleEditMode={() => setShowEditMode(!showEditMode)}
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
                />
              </ErrorBoundary>

              {/* Right panel: serve nav, timeline, phases, metrics */}
              <AnalysisDashboardMetrics
                currentServe={currentServe!}
                phases={phases}
                currentPhase={currentPhase}
                metrics={metrics}
                filteredMetrics={filteredMetrics}
                currentTime={currentTime}
                loopCurrentPhase={loopCurrentPhase}
                onSeek={handleSeek}
                onPhaseJump={handlePhaseJump}
                onContactJump={handleContactJumpWithPhases}
                onToggleLoopCurrentPhase={handleToggleLoopWithPhase}
                onMetricClick={handleMetricClick}
              />
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
        <AnalysisDashboardEditPanel
          proposals={proposals}
          detectionStatus={detectionStatus}
          hasAnalysis={!!analysisStatus?.has_analysis}
          runDetection={runDetection}
          clearProposals={clearProposals}
          acceptAllProposals={acceptAllProposals}
        />
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
