import { useQueryClient } from '@tanstack/react-query';
import React, {
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import usePersistedState from '../hooks/usePersistedState';
import { useServeBiomechanicsReport } from '../hooks/useServeBiomechanicsReport';
import { useServePlayback } from '../hooks/useServePlayback';
import { useServeProposals } from '../hooks/useServeProposals';
import { useMetricHistory } from '../hooks/useMetricHistory';
import { useTossDropProgress } from '../hooks/useTossDropProgress';
import TossDropProgressSection from './TossDropProgressSection';
import { useServeWindows } from '../hooks/useServeWindows';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { useVideoUrl } from '../hooks/useVideoUrl';
import { PhaseWindow } from '../types/biomechanics';
import './AnalysisDashboard.css';
import AnalysisDashboardHeader from './AnalysisDashboardHeader';
import AnalysisViewToggle, { ViewMode } from './AnalysisViewToggle';
import CollapsibleSection from './CollapsibleSection';
import { FeatureChartsSection } from './DetectionDetailsPanel';
import MetricCard, { VISIBLE_METRICS } from './MetricCard';
import ErrorBoundary from './ErrorBoundary';
import HeroView from './HeroView';
import { TourPlaybackControls } from './DemoTour/tourSteps';
import KeyboardShortcutsModal from './KeyboardShortcutsModal';
import ProgressBar from './ProgressBar';
import ServeWindowEditModal from './ServeWindowEditModal';
import ServeThumbnailStrip from './ServeThumbnailStrip';
import Skeleton from './Skeleton';
import TrophyFilmstripModal from './TrophyFilmstripModal';

const SPEED_OPTIONS = [0.25, 0.5, 1] as const;

interface AnalysisDashboardProps {
  videoId: number;
  videoFilename: string;
  videoUrl: string;
  videoDuration?: number;
  onClose: () => void;
  isDemo?: boolean;
  onExitToUpload?: () => void;
  tourControlsRef?: React.Ref<TourPlaybackControls>;
  onRestartTour?: () => void;
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
  videoDuration = 0,
  onClose,
  isDemo = false,
  onExitToUpload,
  tourControlsRef,
  onRestartTour,
}) => {
  const queryClient = useQueryClient();
  const { resolvedUrl: resolvedVideoUrl } = useVideoUrl({ videoId, videoUrl });

  const {
    data: analysisStatus,
    isLoading: analysisStatusLoading,
    refetch: refetchAnalysisStatus,
  } = useVideoAnalysisStatus(videoId);

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
    isDemo,
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
  const [naturalScroll, setNaturalScroll] = usePersistedState(
    'pref:natural-scroll',
    true
  );
  const [viewMode, setViewMode] = useState<ViewMode>('analysis-focus');
  const focusViewRef = useRef<HTMLDivElement>(null);
  const currentTimeRef = useRef(0);

  // Collapsible sidebar section state (persisted across sessions)
  const [chartsExpanded, setChartsExpanded] = usePersistedState(
    'sidebar:charts',
    true
  );

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isTrophyFilmstripOpen, setIsTrophyFilmstripOpen] = useState(false);

  // No-serves find state (mutually exclusive with edit panel)
  const [isFindingServes, setIsFindingServes] = useState(false);

  const {
    serveWindows,
    updateServeWindow,
    deleteServeWindow,
    loading: serveWindowsLoading,
  } = useServeWindows({
    videoId,
    filters: { video_id: videoId },
    autoRefresh: true,
    isDemo,
  });

  const { runDetection } = useServeProposals({
    videoId,
    autoRefresh: true,
    isDemo,
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
    setLoopPhaseWindow,
    autoAdvance,
    handleToggleAutoAdvance,
  } = useServePlayback({ sortedServeWindows });

  // Keep a ref in sync so the wheel handler can read the latest time
  // without needing currentTime in its dependency array.
  useEffect(() => {
    currentTimeRef.current = currentTime;
  }, [currentTime]);

  const { data: biomechanicsReport } = useServeBiomechanicsReport(
    currentServe?.id ?? null
  );

  const metricHistory = useMetricHistory(biomechanicsReport?.player_id, isDemo);
  const {
    sessions: tossDropSessions,
    mean: tossDropMean,
    totalCount: tossDropCount,
    isLoading: tossDropLoading,
  } = useTossDropProgress(biomechanicsReport?.player_id, isDemo);

  const phases = useMemo(
    () => biomechanicsReport?.phase_segmentation ?? [],
    [biomechanicsReport]
  );
  // Track which phase tab was explicitly clicked — gives instant highlight
  // without waiting for the video seek to complete.
  const [activePhaseKey, setActivePhaseKey] = useState<string | null>(null);

  // Expose playback controls for demo tour
  useImperativeHandle(
    tourControlsRef,
    () => ({
      seekToPhase: (phaseKey: string) => {
        const phase = phases.find((p) => p.phase === phaseKey);
        if (phase) {
          setActivePhaseKey(phase.phase);
          handlePhaseJump(phase);
        }
      },
      setPlaybackSpeed,
      pause: () => {
        if (isPlaying) handlePlayPause();
      },
    }),
    [phases, handlePhaseJump, setPlaybackSpeed, isPlaying, handlePlayPause]
  );

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

  // When at serve start, currentPhase can be undefined briefly; fall back
  // to the first phase so the loop button is always usable once phases load.
  const effectivePhase = currentPhase ?? phases[0];

  // After a serve switch, loop stays active but the phase window is cleared.
  // Re-sync the loop window to the new serve's current phase once phases load.
  useEffect(() => {
    if (loopCurrentPhase && !loopPhaseWindow && effectivePhase) {
      setLoopPhaseWindow(effectivePhase);
    }
  }, [loopCurrentPhase, loopPhaseWindow, effectivePhase, setLoopPhaseWindow]);

  const handleToggleLoopWithPhase = useCallback(() => {
    handleToggleLoopCurrentPhase(effectivePhase);
  }, [handleToggleLoopCurrentPhase, effectivePhase]);

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
          if (currentServe) {
            handleSeek(
              Math.max(currentServe.start_timestamp, currentTime - 3 / 30)
            );
          }
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (currentServe) {
            handleSeek(
              Math.min(currentServe.end_timestamp, currentTime + 3 / 30)
            );
          }
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
        case 'a':
        case 'A':
          e.preventDefault();
          handleToggleAutoAdvance();
          break;
        default:
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [
    handlePlayPause,
    handleSeek,
    currentServe,
    currentTime,
    pendingContactTime,
    handleArmContact,
    handleConfirmContact,
    isDemo,
    handleToggleAutoAdvance,
  ]);

  // Scroll wheel — frame scrub only on the video player display
  const handleWheelScrub = useCallback(
    (deltaY: number) => {
      if (!currentServe) return;
      const forward = naturalScroll ? deltaY > 0 : deltaY < 0;
      const delta = (forward ? 1 : -1) * (1 / 30);
      handleSeek(
        Math.max(
          currentServe.start_timestamp,
          Math.min(currentServe.end_timestamp, currentTimeRef.current + delta)
        )
      );
    },
    [currentServe, naturalScroll, handleSeek]
  );

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
  // Guard: don't derive these states until analysisStatus has loaded,
  // otherwise we flash "Ready to Analyze" while the status fetch is in flight.
  const analysisInProgress =
    !analysisStatusLoading &&
    !analysisStatus?.has_analysis &&
    (analysisState.status === 'starting' ||
      analysisState.status === 'processing');

  const analysisIdle =
    !analysisStatusLoading &&
    !analysisStatus?.has_analysis &&
    analysisState.status === 'idle';

  const analysisFailed =
    !analysisStatusLoading &&
    !analysisStatus?.has_analysis &&
    analysisState.status === 'failed';

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
        isDemo={isDemo}
      />

      {/* Initial loading — analysis status not yet fetched */}
      {analysisStatusLoading && (
        <div className="analysis-dashboard__focus-view">
          <div className="analysis-dashboard__main-col">
            <Skeleton variant="rect" height="56vh" />
            <div className="analysis-dashboard__phase-tabs">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} variant="text" width="80px" height="2em" />
              ))}
            </div>
          </div>
          <div className="analysis-dashboard__side-col">
            <Skeleton variant="rect" height="120px" />
            <Skeleton variant="rect" height="80px" />
            <Skeleton variant="rect" height="80px" />
          </div>
        </div>
      )}

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
            Watching your serve...
          </p>
        </div>
      )}

      {/* Main Content: Focus-mode serve viewer */}
      {analysisStatus?.has_analysis && (
        <div className="analysis-dashboard__focus-view" ref={focusViewRef}>
          {hasServes ? (
            <>
              {/* Serve Navigation Rail: video column only, sits above video player */}
              <div className="analysis-dashboard__serve-nav">
                <ServeThumbnailStrip
                  serveWindows={sortedServeWindows}
                  currentIndex={currentServeIndex}
                  videoUrl={resolvedVideoUrl}
                  onNavigate={handleServeNavigate}
                />
                {biomechanicsReport?.moments &&
                  sortedServeWindows.length > 1 && (
                    <>
                      <div className="analysis-dashboard__serve-nav-divider" />
                      <button
                        type="button"
                        className="analysis-dashboard__compare-btn"
                        onClick={() => setIsTrophyFilmstripOpen(true)}
                        title="Compare trophy positions across serves"
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          <rect x="3" y="3" width="7" height="18" rx="1" />
                          <rect x="14" y="3" width="7" height="18" rx="1" />
                        </svg>
                        Compare
                      </button>
                    </>
                  )}
                <AnalysisViewToggle
                  viewMode={viewMode}
                  onViewModeChange={setViewMode}
                />
              </div>
              <div className="analysis-dashboard__main-col">
                {/* Hero View (left column at desktop) */}
                <ErrorBoundary fallbackMessage="Video player encountered an error.">
                  <HeroView
                    videoUrl={resolvedVideoUrl}
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
                    playbackSpeed={playbackSpeed}
                    onPlaybackSpeedChange={setPlaybackSpeed}
                    speedOptions={SPEED_OPTIONS}
                    loopActive={loopCurrentPhase}
                    loopDisabled={!effectivePhase}
                    loopPhaseLabel={loopPhaseWindow?.phase_label}
                    onLoopToggle={handleToggleLoopWithPhase}
                    autoAdvanceActive={autoAdvance}
                    autoAdvanceDisabled={sortedServeWindows.length <= 1}
                    onAutoAdvanceToggle={handleToggleAutoAdvance}
                    contactTimestamp={currentServe!.contact_timestamp ?? null}
                    pendingContactTime={isDemo ? null : pendingContactTime}
                    onArmContact={isDemo ? undefined : handleArmContact}
                    onConfirmContact={isDemo ? undefined : handleConfirmContact}
                    onCancelContact={isDemo ? undefined : handleCancelContact}
                    onOpenShortcuts={() => setShowKeyboardShortcuts(true)}
                    onEditWindow={
                      !isDemo && currentServe
                        ? () => setIsEditModalOpen(true)
                        : undefined
                    }
                    onWheelScrub={handleWheelScrub}
                  />
                </ErrorBoundary>

                {/* Phase navigation — only when phases exist */}
                {phases.length > 0 && (
                  <div
                    className="analysis-dashboard__phase-tabs"
                    role="tablist"
                    data-tour-step="phase-tabs"
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
                )}
              </div>

              {/* Demo CTA — grid row 1 col 2 (flush with film strip), outside scrollable side-col */}
              {isDemo && (
                <div className="analysis-dashboard__side-nav">
                  <button
                    type="button"
                    className="demo-cta-block__upload-btn"
                    onClick={onExitToUpload}
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    Upload Your Own Serve
                  </button>
                  {onRestartTour && (
                    <button
                      type="button"
                      className="demo-cta-block__restart-btn"
                      onClick={onRestartTour}
                    >
                      <svg
                        width="13"
                        height="13"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                        <path d="M3 3v5h5" />
                      </svg>
                      Restart Tour
                    </button>
                  )}
                </div>
              )}

              <div className="analysis-dashboard__side-col">
                {/* Metric Cards */}
                {biomechanicsReport?.metrics && (
                  <div className="analysis-dashboard__metric-cards">
                    {[...biomechanicsReport.metrics]
                      .filter((m) => VISIBLE_METRICS.has(m.metric_name))
                      .sort((a, b) => {
                        // Toss height first (tall card fills col 1)
                        const tall = 'toss_peak_height';
                        if (a.metric_name === tall) return -1;
                        if (b.metric_name === tall) return 1;
                        return 0;
                      })
                      .map((m) => (
                        <MetricCard
                          key={m.metric_name}
                          metricName={m.metric_name}
                          value={m.value}
                          timestamp={m.timestamp}
                          historyValues={metricHistory[m.metric_name] ?? []}
                          onScrubTo={handleSeek}
                          serveWindowId={currentServe?.id ?? null}
                        />
                      ))}
                  </div>
                )}

                {/* Ball Drop Trend — hidden in demo, needs ≥3 data points */}
                {!isDemo && tossDropCount >= 3 && (
                  <TossDropProgressSection
                    sessions={tossDropSessions}
                    mean={tossDropMean}
                    isLoading={tossDropLoading}
                  />
                )}

                {/* Feature Curves */}
                {biomechanicsReport?.detection_meta && (
                  <div data-tour-step="feature-charts">
                    <CollapsibleSection
                      title="Feature Curves"
                      expanded={chartsExpanded}
                      onToggle={() => setChartsExpanded(!chartsExpanded)}
                    >
                      <FeatureChartsSection
                        detectionMeta={biomechanicsReport.detection_meta}
                        currentTime={currentTime}
                        serveStart={currentServe!.start_timestamp}
                        contactTimestamp={
                          currentServe!.contact_timestamp ?? null
                        }
                        onSeek={handleSeek}
                        loopPhaseWindow={
                          loopCurrentPhase ? loopPhaseWindow : null
                        }
                      />
                    </CollapsibleSection>
                  </div>
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
                Finding your serves...
              </p>
            </div>
          ) : serveWindowsLoading ? (
            <>
              <div className="analysis-dashboard__main-col">
                <Skeleton variant="rect" height="56vh" />
                <div className="analysis-dashboard__phase-tabs">
                  {Array.from({ length: 4 }, (_, i) => (
                    <Skeleton
                      key={i}
                      variant="text"
                      width="80px"
                      height="2em"
                    />
                  ))}
                </div>
              </div>
              <div className="analysis-dashboard__side-col">
                <Skeleton variant="rect" height="120px" />
                <Skeleton variant="rect" height="80px" />
                <Skeleton variant="rect" height="80px" />
              </div>
            </>
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

      {currentServe && (
        <ServeWindowEditModal
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          serveWindow={currentServe}
          allWindows={sortedServeWindows}
          videoDuration={videoDuration}
          videoUrl={resolvedVideoUrl}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
            setIsEditModalOpen(false);
          }}
          onSplit={() => {
            queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
            setIsEditModalOpen(false);
          }}
          onDelete={
            !isDemo
              ? async (id: number) => {
                  await deleteServeWindow(id);
                  queryClient.invalidateQueries({
                    queryKey: ['serve-windows'],
                  });
                  setIsEditModalOpen(false);
                }
              : undefined
          }
        />
      )}

      <TrophyFilmstripModal
        isOpen={isTrophyFilmstripOpen}
        onClose={() => setIsTrophyFilmstripOpen(false)}
        serveWindows={sortedServeWindows}
        videoFilename={videoFilename}
        activeServeWindowId={currentServe?.id}
      />
    </div>
  );
};

export default AnalysisDashboard;
