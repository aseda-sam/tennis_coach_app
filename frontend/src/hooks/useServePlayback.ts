import { useCallback, useEffect, useState } from 'react';
import { PhaseWindow } from '../types/biomechanics';
import usePersistedState from './usePersistedState';
import { ServeWindow } from '../types/serveWindow';

interface UseServePlaybackOptions {
  sortedServeWindows: ServeWindow[];
}

interface UseServePlaybackResult {
  currentServeIndex: number;
  currentServe: ServeWindow | null;
  currentTime: number;
  isPlaying: boolean;
  loopCurrentPhase: boolean;
  loopPhaseWindow: PhaseWindow | null;
  playbackSpeed: number;
  handlePlayPause: () => void;
  handleSeek: (t: number) => void;
  handleTimeUpdate: (t: number) => void;
  handlePhaseJump: (phase: PhaseWindow) => void;
  handleContactJump: (contactTimestamp: number, phases: PhaseWindow[]) => void;
  handleToggleLoopCurrentPhase: (currentPhase: PhaseWindow | undefined) => void;
  handleServeNavigate: (index: number) => void;
  setPlaybackSpeed: (speed: number) => void;
}

export function useServePlayback({
  sortedServeWindows,
}: UseServePlaybackOptions): UseServePlaybackResult {
  const [currentServeIndex, setCurrentServeIndex] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loopCurrentPhase, setLoopCurrentPhase] = useState(false);
  const [loopPhaseWindow, setLoopPhaseWindow] = useState<PhaseWindow | null>(
    null
  );
  const [playbackSpeed, setPlaybackSpeed] = usePersistedState(
    'pref:playback-speed',
    1
  );

  const currentServe = sortedServeWindows[currentServeIndex] ?? null;

  // Sync currentTime when switching serves
  useEffect(() => {
    if (currentServe) {
      setCurrentTime(currentServe.start_timestamp);
      setIsPlaying(false);
      setLoopCurrentPhase(false);
      setLoopPhaseWindow(null);
      setPlaybackSpeed(1);
    }
  }, [currentServe?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Playback timer for stick figure mode (and video mode sync)
  useEffect(() => {
    if (!isPlaying || !currentServe) return;

    const interval = setInterval(() => {
      setCurrentTime((t) => {
        const next = t + (1 / 30) * playbackSpeed;
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
  }, [
    isPlaying,
    currentServe,
    loopCurrentPhase,
    loopPhaseWindow,
    playbackSpeed,
  ]);

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
    (contactTimestamp: number, phases: PhaseWindow[]) => {
      setCurrentTime(contactTimestamp);
      setIsPlaying(false);
      if (loopCurrentPhase) {
        const phaseAtContact = phases.find(
          (p) =>
            contactTimestamp >= p.start_timestamp &&
            contactTimestamp <= p.end_timestamp
        );
        setLoopPhaseWindow(phaseAtContact ?? null);
      }
    },
    [loopCurrentPhase]
  );

  const handleToggleLoopCurrentPhase = useCallback(
    (currentPhase: PhaseWindow | undefined) => {
      if (loopCurrentPhase) {
        setLoopCurrentPhase(false);
        setLoopPhaseWindow(null);
        return;
      }
      if (!currentPhase) return;
      setLoopCurrentPhase(true);
      setLoopPhaseWindow(currentPhase);
      setCurrentTime(currentPhase.start_timestamp);
    },
    [loopCurrentPhase]
  );

  const handleServeNavigate = useCallback(
    (index: number) => {
      if (index >= 0 && index < sortedServeWindows.length) {
        setCurrentServeIndex(index);
      }
    },
    [sortedServeWindows.length]
  );

  return {
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
  };
}
