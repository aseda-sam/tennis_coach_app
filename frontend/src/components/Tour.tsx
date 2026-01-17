/**
 * Custom Tour Component
 *
 * A lightweight tour component built for React 19 compatibility.
 * Currently using a custom implementation because react-joyride doesn't support React 19.
 *
 * Future Migration Consideration:
 * - Monitor react-joyride for React 19 support: https://github.com/gilbarbara/react-joyride
 * - Once available, consider migrating for better features (keyboard nav, accessibility) and reduced maintenance
 * - Migration would involve replacing this component and updating DemoDashboard.tsx to use react-joyride's API
 */

import React, { useEffect, useRef, useState } from 'react';
import './Tour.css';

export interface TourStep {
  target: string; // CSS selector or data-tour attribute
  content: string;
  title?: string;
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'center';
}

interface TourProps {
  steps: TourStep[];
  isOpen: boolean;
  onClose: () => void;
  onComplete?: () => void;
  showSkip?: boolean;
}

const Tour: React.FC<TourProps> = ({
  steps,
  isOpen,
  onClose,
  onComplete,
  showSkip = true,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [position, setPosition] = useState<{
    top: number;
    left: number;
    width: number;
    height: number;
  } | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const currentStepData = steps[currentStep];

  useEffect(() => {
    if (!isOpen || !currentStepData) return;

    const updatePosition = () => {
      const element = document.querySelector(
        `[data-tour="${currentStepData.target}"]`
      );
      if (!element) {
        // If element not found, center the tooltip
        setPosition({
          top: window.innerHeight / 2,
          left: window.innerWidth / 2,
          width: 0,
          height: 0,
        });
        return;
      }

      const rect = element.getBoundingClientRect();

      // Use fixed positioning relative to viewport
      // getBoundingClientRect() already returns viewport-relative coordinates
      setPosition({
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      });

      // Scroll element into view if needed
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'center',
      });
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);

    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
    };
  }, [isOpen, currentStep, currentStepData]);

  if (!isOpen || !currentStepData) return null;

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkip = () => {
    onClose();
  };

  const handleComplete = () => {
    onComplete?.();
    onClose();
  };

  const placement = currentStepData.placement || 'bottom';
  const tooltipStyle: React.CSSProperties = position
    ? {
        top: `${position.top + position.height + 12}px`,
        left: `${position.left + position.width / 2}px`,
        transform: 'translateX(-50%)',
      }
    : {
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      };

  // Adjust for different placements (position is already viewport-relative)
  if (placement === 'top' && position) {
    tooltipStyle.top = `${position.top - 12}px`;
    tooltipStyle.transform = 'translate(-50%, -100%)';
  } else if (placement === 'right' && position) {
    tooltipStyle.top = `${position.top + position.height / 2}px`;
    tooltipStyle.left = `${position.left + position.width + 12}px`;
    tooltipStyle.transform = 'translateY(-50%)';
  } else if (placement === 'left' && position) {
    tooltipStyle.top = `${position.top + position.height / 2}px`;
    tooltipStyle.left = `${position.left - 12}px`;
    tooltipStyle.transform = 'translate(-100%, -50%)';
  } else if (placement === 'center') {
    tooltipStyle.top = '50%';
    tooltipStyle.left = '50%';
    tooltipStyle.transform = 'translate(-50%, -50%)';
  }

  return (
    <>
      {/* Overlay */}
      <div
        ref={overlayRef}
        className="tour-overlay"
        onClick={handleSkip}
        aria-hidden="true"
      />
      {/* Highlight */}
      {position && position.width > 0 && (
        <div
          className="tour-highlight"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            width: `${position.width}px`,
            height: `${position.height}px`,
            position: 'fixed',
          }}
        />
      )}
      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className="tour-tooltip"
        style={tooltipStyle}
        role="dialog"
        aria-labelledby="tour-title"
        aria-describedby="tour-content"
      >
        {currentStepData.title && (
          <h3 id="tour-title" className="tour-tooltip__title">
            {currentStepData.title}
          </h3>
        )}
        <p id="tour-content" className="tour-tooltip__content">
          {currentStepData.content}
        </p>
        <div className="tour-tooltip__footer">
          <div className="tour-tooltip__progress">
            {currentStep + 1} / {steps.length}
          </div>
          <div className="tour-tooltip__actions">
            {showSkip && (
              <button
                className="tour-tooltip__skip"
                onClick={handleSkip}
                type="button"
              >
                Skip
              </button>
            )}
            {currentStep > 0 && (
              <button
                className="tour-tooltip__prev"
                onClick={handlePrevious}
                type="button"
              >
                Previous
              </button>
            )}
            <button
              className="tour-tooltip__next"
              onClick={handleNext}
              type="button"
            >
              {currentStep < steps.length - 1 ? 'Next' : 'Finish'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Tour;
