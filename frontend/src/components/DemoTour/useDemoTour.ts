import { useCallback, useEffect, useRef, useState } from 'react';
import { TOUR_STEPS, TourPlaybackControls, TourStep } from './tourSteps';

const STORAGE_KEY = 'demo:tour-completed';

interface UseDemoTourOptions {
  enabled: boolean;
  controlsRef: React.RefObject<TourPlaybackControls | null>;
}

export interface UseDemoTourReturn {
  isActive: boolean;
  currentStep: TourStep | null;
  currentStepIndex: number;
  totalSteps: number;
  next: () => void;
  prev: () => void;
  end: () => void;
  restart: () => void;
  tourCompleted: boolean;
}

function findNextValidStep(fromIndex: number, direction: 1 | -1): number {
  let idx = fromIndex;
  while (idx >= 0 && idx < TOUR_STEPS.length) {
    const step = TOUR_STEPS[idx];
    if (!step.target || document.querySelector(step.target)) {
      return idx;
    }
    idx += direction;
  }
  return -1;
}

export function useDemoTour({
  enabled,
  controlsRef,
}: UseDemoTourOptions): UseDemoTourReturn {
  const [isActive, setIsActive] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [tourCompleted, setTourCompleted] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  });
  const autoStarted = useRef(false);

  // Auto-start after 800ms on first visit
  useEffect(() => {
    if (!enabled || tourCompleted || autoStarted.current) return;
    autoStarted.current = true;
    const timer = setTimeout(() => {
      const firstValid = findNextValidStep(0, 1);
      if (firstValid >= 0) {
        setStepIndex(firstValid);
        setIsActive(true);
      }
    }, 800);
    return () => clearTimeout(timer);
  }, [enabled, tourCompleted]);

  // Call onEnter when step changes
  const prevStepRef = useRef<number>(-1);
  useEffect(() => {
    if (!isActive) return;
    if (prevStepRef.current === stepIndex) return;
    prevStepRef.current = stepIndex;

    const step = TOUR_STEPS[stepIndex];
    if (step?.onEnter && controlsRef.current) {
      setTimeout(() => {
        if (controlsRef.current) {
          step.onEnter!(controlsRef.current);
        }
      }, 100);
    }
  }, [isActive, stepIndex, controlsRef]);

  const next = useCallback(() => {
    const nextIdx = findNextValidStep(stepIndex + 1, 1);
    if (nextIdx >= 0) {
      setStepIndex(nextIdx);
    } else {
      setIsActive(false);
      setTourCompleted(true);
      localStorage.setItem(STORAGE_KEY, 'true');
    }
  }, [stepIndex]);

  const prev = useCallback(() => {
    const prevIdx = findNextValidStep(stepIndex - 1, -1);
    if (prevIdx >= 0) {
      setStepIndex(prevIdx);
    }
  }, [stepIndex]);

  const end = useCallback(() => {
    setIsActive(false);
    setTourCompleted(true);
    localStorage.setItem(STORAGE_KEY, 'true');
  }, []);

  const restart = useCallback(() => {
    const firstValid = findNextValidStep(0, 1);
    if (firstValid >= 0) {
      prevStepRef.current = -1;
      setStepIndex(firstValid);
      setIsActive(true);
      setTourCompleted(false);
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  return {
    isActive,
    currentStep: isActive ? (TOUR_STEPS[stepIndex] ?? null) : null,
    currentStepIndex: stepIndex,
    totalSteps: TOUR_STEPS.length,
    next,
    prev,
    end,
    restart,
    tourCompleted,
  };
}
