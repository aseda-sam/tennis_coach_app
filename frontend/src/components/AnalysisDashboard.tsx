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
import { useServeWindows } from '../hooks/useServeWindows';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { useVideoUrl } from '../hooks/useVideoUrl';
import { PhaseWindow } from '../types/biomechanics';
import './AnalysisDashboard.css';
import AnalysisDashboardHeader from './AnalysisDashboardHeader';
import AnalysisViewToggle, { ViewMode } from './AnalysisViewToggle';
import CollapsibleSection from './CollapsibleSection';
import { FeatureChartsSection, KTPTable } from './DetectionDetailsPanel';
import ErrorBoundary from './ErrorBoundary';
import HeroView from './HeroView';
import { TourPlaybackControls } from './DemoTour/tourSteps';
import KeyboardShortcutsModal from './KeyboardShortcutsModal';
import ProgressBar from './ProgressBar';
import ServeWindowEditModal from './ServeWindowEditModal';
import ServeThumbnailStrip from './ServeThumbnailStrip';
import Skeleton from './Skeleton';

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

  // Collapsible sidebar section state (persisted across sessions)
  const [ktpExpanded, setKtpExpanded] = usePersistedState('sidebar:ktp', true);
  const [chartsExpanded, setChartsExpanded] = usePersistedState(
    'sidebar:charts',
    true
  );

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // No-serves find state (mutually exclusive with edit panel)
  const [isFindingServes, setIsFindingServes] = useState(false);

  const {
    serveWindows,
    updateServeWindow,
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

  const handleToggleLoopWithPhase = useCallback(() => {
    handleToggleLoopCurrentPhase(currentPhase);
  }, [handleToggleLoopCurrentPhase, currentPhase]);

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
  ]);

  // Scroll wheel — frame navigation within current serve window (only when hovering over the player/chart area)
  useEffect(() => {
    if (!currentServe) return;
    const container = focusViewRef.current;
    if (!container) return;
    const handleWheel = (e: WheelEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }
      e.preventDefault();
      const forward = naturalScroll ? e.deltaY > 0 : e.deltaY < 0;
      const delta = (forward ? 1 : -1) * (1 / 30);
      handleSeek(
        Math.max(
          currentServe.start_timestamp,
          Math.min(currentServe.end_timestamp, currentTime + delta)
        )
      );
    };
    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [currentServe, currentTime, naturalScroll, handleSeek]);

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
        onRestartTour={onRestartTour}
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

      {/* Serve Navigation Rail: thumbnails + view toggle inline */}
      {analysisStatus?.has_analysis && hasServes && (
        <div className="analysis-dashboard__serve-nav">
          <ServeThumbnailStrip
            serveWindows={sortedServeWindows}
            currentIndex={currentServeIndex}
            videoUrl={resolvedVideoUrl}
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
        <div className="analysis-dashboard__focus-view" ref={focusViewRef}>
          {hasServes ? (
            <>
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
                    loopDisabled={!currentPhase}
                    onLoopToggle={handleToggleLoopWithPhase}
                    phases={phases}
                    activePhase={currentPhase?.phase}
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

              <div className="analysis-dashboard__side-col">
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
                      />
                    </CollapsibleSection>
                  </div>
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
        />
      )}
    </div>
  );
};

export default AnalysisDashboard;
