import { useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAdmin } from '../hooks/useAdmin';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import usePersistedState from '../hooks/usePersistedState';
import { useServeBiomechanicsReport } from '../hooks/useServeBiomechanicsReport';
import { useServePlayback } from '../hooks/useServePlayback';
import { useServeProposals } from '../hooks/useServeProposals';
import { useServeWindows } from '../hooks/useServeWindows';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { MetricValue, PhaseWindow } from '../types/biomechanics';
import './AnalysisDashboard.css';
import AnalysisDashboardHeader from './AnalysisDashboardHeader';
import AnalysisViewToggle, { ViewMode } from './AnalysisViewToggle';
import CollapsibleSection from './CollapsibleSection';
import { FeatureChartsSection, KTPTable } from './DetectionDetailsPanel';
import ErrorBoundary from './ErrorBoundary';
import HeroView from './HeroView';
import { ArrowBackIcon, UploadIcon } from './Icons';
import KeyboardShortcutsModal from './KeyboardShortcutsModal';
import ProgressBar from './ProgressBar';
import ServeThumbnailStrip from './ServeThumbnailStrip';
import Tour, { TourStep } from './Tour';

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
  isDemo?: boolean;
  onExitToUpload?: () => void;
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
  isDemo = false,
  onExitToUpload,
}) => {
  const queryClient = useQueryClient();
  const { isAdmin } = useAdmin();

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

  // Collapsible sidebar section state (persisted across sessions)
  const [metricsExpanded, setMetricsExpanded] = usePersistedState(
    'sidebar:metrics',
    true
  );
  const [ktpExpanded, setKtpExpanded] = usePersistedState('sidebar:ktp', true);
  const [chartsExpanded, setChartsExpanded] = usePersistedState(
    'sidebar:charts',
    true
  );

  // No-serves find state (mutually exclusive with edit panel)
  const [isFindingServes, setIsFindingServes] = useState(false);

  // Demo tour state
  const [isTourOpen, setIsTourOpen] = useState(false);

  const { serveWindows, updateServeWindow } = useServeWindows({
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

  const handleSetContactAtCurrentTime = useCallback(
    async (serveWindowId: number, timestamp: number) => {
      await updateServeWindow(serveWindowId, { contact_timestamp: timestamp });
      queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
      queryClient.invalidateQueries({
        queryKey: ['biomechanics-report', serveWindowId],
      });
    },
    [updateServeWindow, queryClient]
  );

  // Pending contact — two-step confirm before committing a contact timestamp
  const [pendingContactTime, setPendingContactTime] = useState<number | null>(
    null
  );

  const handleArmContact = useCallback((time: number) => {
    setPendingContactTime(time);
  }, []);

  const handleConfirmContact = useCallback(async () => {
    if (pendingContactTime == null || !currentServe) return;
    await handleSetContactAtCurrentTime(currentServe.id, pendingContactTime);
    setPendingContactTime(null);
  }, [pendingContactTime, currentServe, handleSetContactAtCurrentTime]);

  const handleCancelContact = useCallback(() => {
    setPendingContactTime(null);
  }, []);

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
        return;
      }

      switch (e.key) {
        case ' ':
        case 'Space':
          e.preventDefault();
          handlePlayPause();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          handleServeNavigate(currentServeIndex - 1);
          break;
        case 'ArrowRight':
          e.preventDefault();
          handleServeNavigate(currentServeIndex + 1);
          break;
        case 'c':
        case 'C':
          if (isDemo) break;
          e.preventDefault();
          if (pendingContactTime !== null) {
            handleConfirmContact();
          } else if (currentServe) {
            handleArmContact(currentTime);
          }
          break;
        default:
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [
    handlePlayPause,
    handleServeNavigate,
    currentServeIndex,
    currentServe,
    currentTime,
    pendingContactTime,
    handleArmContact,
    handleConfirmContact,
    isDemo,
  ]);

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

  // Demo: admin status warning
  const hasPoseAnalysis = analysisStatus?.has_analysis || false;
  const showDemoStatusWarning =
    isDemo && isAdmin && (!hasPoseAnalysis || serveWindows.length === 0);

  // Demo: tour steps
  const tourSteps: TourStep[] = useMemo(
    () => [
      {
        target: 'video-player',
        title: 'Video Player',
        content:
          'Play the demo clip and scrub through frames using the timeline below.',
        placement: 'bottom',
      },
      {
        target: 'serve-window-ranges',
        title: 'Key Moments',
        content: 'Navigate key moments directly from the timeline.',
        placement: 'top',
      },
      {
        target: 'analysis-panel',
        title: 'Metrics & Analysis',
        content:
          'Review pose and key-moment metrics to understand your serve mechanics.',
        placement: 'left',
      },
      {
        target: 'upload-cta',
        title: 'Ready to Upload?',
        content:
          'Ready to analyze your own video? Upload to see personalized feedback on your technique.',
        placement: 'left',
      },
    ],
    []
  );

  useEffect(() => {
    if (!isDemo) return;
    const tourCompleted = localStorage.getItem('demoTourCompleted');
    if (!tourCompleted) {
      const timer = setTimeout(() => setIsTourOpen(true), 500);
      return () => clearTimeout(timer);
    }
  }, [isDemo]);

  const handleTourComplete = useCallback(() => {
    localStorage.setItem('demoTourCompleted', 'true');
  }, []);

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
      {/* Demo: Admin status warning */}
      {showDemoStatusWarning && (
        <div className="analysis-dashboard__status-warning">
          <div className="analysis-dashboard__status-warning-content">
            <strong>Demo Status:</strong>
            {!hasPoseAnalysis && (
              <span className="analysis-dashboard__status-item warning">
                ⚠ Missing pose analysis
              </span>
            )}
            {serveWindows.length === 0 && (
              <span className="analysis-dashboard__status-item warning">
                ⚠ No key moments tagged
              </span>
            )}
            <span className="analysis-dashboard__status-hint">
              Use the Admin tab to manage demo videos.
            </span>
          </div>
        </div>
      )}

      {/* Header */}
      <AnalysisDashboardHeader
        videoFilename={videoFilename}
        hasServes={hasServes}
        serveIndex={hasServes ? currentServeIndex : undefined}
        serveCount={hasServes ? sortedServeWindows.length : undefined}
        onClose={onClose}
        isDemo={isDemo}
      />

      {/* Analysis Required State */}
      {analysisIdle && !isDemo && (
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
      {analysisFailed && !isDemo && (
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
      {analysisInProgress && !isDemo && (
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

      {/* Serve Navigation Rail: thumbnails + view toggle inline */}
      {analysisStatus?.has_analysis && hasServes && (
        <div className="analysis-dashboard__serve-nav">
          <ServeThumbnailStrip
            serveWindows={sortedServeWindows}
            currentIndex={currentServeIndex}
            videoUrl={videoUrl}
            onNavigate={handleServeNavigate}
          />
          <AnalysisViewToggle
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        </div>
      )}

      {/* Main Content: Focus-mode serve viewer */}
      {analysisStatus?.has_analysis && (
        <div className="analysis-dashboard__focus-view">
          {hasServes ? (
            <>
              <div
                className="analysis-dashboard__main-col"
                data-tour="video-player"
              >
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
                    onPlaybackSpeedChange={setPlaybackSpeed}
                    speedOptions={SPEED_OPTIONS}
                    loopActive={loopCurrentPhase}
                    loopDisabled={!currentPhase}
                    onLoopToggle={handleToggleLoopWithPhase}
                    phases={phases}
                    activePhase={currentPhase?.phase}
                    contactTimestamp={currentServe!.contact_timestamp ?? null}
                    pendingContactTime={isDemo ? null : pendingContactTime}
                    onArmContact={isDemo ? undefined : handleArmContact}
                    onConfirmContact={isDemo ? undefined : handleConfirmContact}
                    onCancelContact={isDemo ? undefined : handleCancelContact}
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
                  </>
                )}
              </div>

              <div
                className="analysis-dashboard__side-col"
                data-tour="analysis-panel"
              >
                {/* Demo: Upload CTA */}
                {isDemo && onExitToUpload && (
                  <div
                    className="analysis-dashboard__upload-cta"
                    data-tour="upload-cta"
                  >
                    <div className="analysis-dashboard__upload-cta-content">
                      <button
                        className="analysis-dashboard__back-button"
                        onClick={onClose}
                        type="button"
                      >
                        <ArrowBackIcon size={16} />
                        Back to Home
                      </button>
                      <h3 className="analysis-dashboard__upload-cta-title">
                        Ready to analyze your own video?
                      </h3>
                      <p className="analysis-dashboard__upload-cta-description">
                        Now that you've seen how it works, upload your tennis
                        video and get personalized feedback on your technique.
                      </p>
                      <button
                        className="analysis-dashboard__upload-cta-button"
                        onClick={onExitToUpload}
                        type="button"
                      >
                        <UploadIcon size={20} />
                        Upload Your Video
                      </button>
                    </div>
                  </div>
                )}

                {/* Feature Curves */}
                {biomechanicsReport?.detection_meta && (
                  <CollapsibleSection
                    title="Feature Curves"
                    expanded={chartsExpanded}
                    onToggle={() => setChartsExpanded(!chartsExpanded)}
                  >
                    <FeatureChartsSection
                      detectionMeta={biomechanicsReport.detection_meta}
                      currentTime={currentTime}
                      serveStart={currentServe!.start_timestamp}
                      contactTimestamp={currentServe!.contact_timestamp ?? null}
                      onSeek={handleSeek}
                    />
                  </CollapsibleSection>
                )}

                {/* Metrics */}
                {metrics.length > 0 && (
                  <CollapsibleSection
                    title="Metrics"
                    expanded={metricsExpanded}
                    onToggle={() => setMetricsExpanded(!metricsExpanded)}
                  >
                    <div className="analysis-dashboard__metrics-strip">
                      {metrics.map((m) => {
                        const isClickable =
                          m.timestamp != null && m.value != null;
                        return (
                          <div
                            key={m.metric_name}
                            className={`analysis-dashboard__metric-card${isClickable ? ' analysis-dashboard__metric-card--clickable' : ''}`}
                            onClick={
                              isClickable
                                ? () => handleMetricClick(m)
                                : undefined
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
                  </CollapsibleSection>
                )}

                {/* Key Time Points */}
                {biomechanicsReport?.detection_meta && (
                  <CollapsibleSection
                    title="Key Time Points"
                    expanded={ktpExpanded}
                    onToggle={() => setKtpExpanded(!ktpExpanded)}
                  >
                    <KTPTable
                      detectionMeta={biomechanicsReport.detection_meta}
                      serveStart={currentServe!.start_timestamp}
                      onSeek={handleSeek}
                    />
                  </CollapsibleSection>
                )}
              </div>
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
              {!isDemo && (
                <button
                  className="analysis-dashboard__action-btn analysis-dashboard__action-btn--find"
                  onClick={handleFindServes}
                  disabled={isFindingServes}
                  type="button"
                >
                  {isFindingServes ? 'Finding...' : 'Find Serve Windows'}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      <KeyboardShortcutsModal
        isOpen={showKeyboardShortcuts}
        onClose={() => setShowKeyboardShortcuts(false)}
        isDemo={isDemo}
        naturalScroll={naturalScroll}
        onNaturalScrollChange={setNaturalScroll}
      />

      {isDemo && (
        <Tour
          steps={tourSteps}
          isOpen={isTourOpen}
          onClose={() => setIsTourOpen(false)}
          onComplete={handleTourComplete}
          showSkip={true}
        />
      )}
    </div>
  );
};

export default AnalysisDashboard;
