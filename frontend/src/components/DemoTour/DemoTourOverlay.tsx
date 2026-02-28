import React, { useCallback, useEffect, useRef, useState } from 'react';
import DemoTourTooltip from './DemoTourTooltip';
import { TourStep } from './tourSteps';
import './DemoTourOverlay.css';

interface DemoTourOverlayProps {
  step: TourStep;
  stepIndex: number;
  totalSteps: number;
  onNext: () => void;
  onPrev: () => void;
  onEnd: () => void;
  onUpload?: () => void;
}

interface SpotlightRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const TOOLTIP_GAP = 16;
const MIN_CLEARANCE = 200;

type Placement = TourStep['placement'];

function computeTooltipStyle(
  spotlight: SpotlightRect | null,
  placement: Placement,
  tooltipEl: HTMLDivElement | null
): React.CSSProperties {
  if (!spotlight || placement === 'center' || !tooltipEl) {
    return {};
  }

  const tooltipRect = tooltipEl.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let top: number;
  let left: number;
  let resolved: Placement = placement;

  // Auto-flip if insufficient clearance
  if (
    placement === 'bottom' &&
    vh - (spotlight.top + spotlight.height) < MIN_CLEARANCE
  ) {
    resolved = 'top';
  } else if (placement === 'top' && spotlight.top < MIN_CLEARANCE) {
    resolved = 'bottom';
  } else if (placement === 'left' && spotlight.left < MIN_CLEARANCE) {
    resolved = 'right';
  } else if (
    placement === 'right' &&
    vw - (spotlight.left + spotlight.width) < MIN_CLEARANCE
  ) {
    resolved = 'left';
  }

  switch (resolved) {
    case 'bottom':
      top = spotlight.top + spotlight.height + TOOLTIP_GAP;
      left = spotlight.left + spotlight.width / 2 - tooltipRect.width / 2;
      break;
    case 'top':
      top = spotlight.top - tooltipRect.height - TOOLTIP_GAP;
      left = spotlight.left + spotlight.width / 2 - tooltipRect.width / 2;
      break;
    case 'left':
      top = spotlight.top + spotlight.height / 2 - tooltipRect.height / 2;
      left = spotlight.left - tooltipRect.width - TOOLTIP_GAP;
      break;
    case 'right':
      top = spotlight.top + spotlight.height / 2 - tooltipRect.height / 2;
      left = spotlight.left + spotlight.width + TOOLTIP_GAP;
      break;
    default:
      return {};
  }

  // Clamp to viewport
  left = Math.max(16, Math.min(left, vw - tooltipRect.width - 16));
  top = Math.max(16, Math.min(top, vh - tooltipRect.height - 16));

  return { position: 'fixed', top, left };
}

const DemoTourOverlay: React.FC<DemoTourOverlayProps> = ({
  step,
  stepIndex,
  totalSteps,
  onNext,
  onPrev,
  onEnd,
  onUpload,
}) => {
  const [spotlight, setSpotlight] = useState<SpotlightRect | null>(null);
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [tooltipStyle, setTooltipStyle] = useState<React.CSSProperties>({});
  const isCentered = step.placement === 'center' || !step.target;

  // Update spotlight rect from target element
  const updateSpotlight = useCallback(() => {
    if (!step.target) {
      setSpotlight(null);
      return;
    }
    const el = document.querySelector(step.target);
    if (!el) {
      setSpotlight(null);
      return;
    }
    const rect = el.getBoundingClientRect();
    const padding = 5;
    setSpotlight({
      top: rect.top - padding,
      left: rect.left - padding,
      width: rect.width + padding * 2,
      height: rect.height + padding * 2,
    });
  }, [step.target]);

  // Observe target for position/size changes
  useEffect(() => {
    updateSpotlight();

    // Sequenced animation: tooltip appears after spotlight settles
    setTooltipVisible(false);
    const timer = setTimeout(() => setTooltipVisible(true), 360);

    let observer: ResizeObserver | null = null;
    if (step.target) {
      const el = document.querySelector(step.target);
      if (el) {
        observer = new ResizeObserver(() => updateSpotlight());
        observer.observe(el);
      }
    }

    window.addEventListener('scroll', updateSpotlight, true);
    window.addEventListener('resize', updateSpotlight);

    return () => {
      clearTimeout(timer);
      observer?.disconnect();
      window.removeEventListener('scroll', updateSpotlight, true);
      window.removeEventListener('resize', updateSpotlight);
    };
  }, [step.target, updateSpotlight]);

  // Recompute tooltip position when spotlight or visibility changes
  useEffect(() => {
    if (tooltipVisible && tooltipRef.current) {
      const style = computeTooltipStyle(
        spotlight,
        step.placement,
        tooltipRef.current
      );
      setTooltipStyle(style);
    }
  }, [spotlight, tooltipVisible, step.placement]);

  // Keyboard navigation (capture phase to intercept before dashboard shortcuts)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onEnd();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        e.stopPropagation();
        onNext();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        e.stopPropagation();
        onPrev();
      } else if (e.key === ' ' || e.key === 'Space') {
        // Prevent playback toggle while tour is active
        e.stopPropagation();
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, [onNext, onPrev, onEnd]);

  return (
    <div className="demo-tour-overlay">
      {/* Spotlight cutout — creates dimmed backdrop via box-shadow */}
      {spotlight && (
        <div
          className="demo-tour-overlay__spotlight"
          style={{
            top: spotlight.top,
            left: spotlight.left,
            width: spotlight.width,
            height: spotlight.height,
          }}
        />
      )}

      {/* Centered backdrop for non-targeted steps */}
      {isCentered && <div className="demo-tour-overlay__centered-backdrop" />}

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className={`demo-tour-overlay__tooltip-wrapper${tooltipVisible ? ' demo-tour-overlay__tooltip-wrapper--visible' : ''}`}
        style={!isCentered ? tooltipStyle : undefined}
      >
        <DemoTourTooltip
          title={step.title}
          body={step.body}
          playerNote={step.playerNote}
          actionHint={step.actionHint}
          stepIndex={stepIndex}
          totalSteps={totalSteps}
          onNext={onNext}
          onPrev={onPrev}
          onEnd={onEnd}
          isLastStep={stepIndex === totalSteps - 1}
          isFirstStep={stepIndex === 0}
          isCentered={isCentered}
          onUpload={onUpload}
        />
      </div>
    </div>
  );
};

export default DemoTourOverlay;
