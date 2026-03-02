import React from 'react';
import { Upload } from 'lucide-react';
import './DemoTourTooltip.css';

interface DemoTourTooltipProps {
  title: string;
  body: string;
  actionHint?: string;
  stepIndex: number;
  totalSteps: number;
  onNext: () => void;
  onPrev: () => void;
  onEnd: () => void;
  isLastStep: boolean;
  isFirstStep: boolean;
  isCentered: boolean;
  onUpload?: () => void;
}

const DemoTourTooltip: React.FC<DemoTourTooltipProps> = ({
  title,
  body,
  actionHint,
  stepIndex,
  totalSteps,
  onNext,
  onPrev,
  onEnd,
  isLastStep,
  isFirstStep,
  isCentered,
  onUpload,
}) => {
  const paragraphs = body.split('\n\n');

  return (
    <div
      className={`demo-tour-tooltip${isCentered ? ' demo-tour-tooltip--centered' : ''}`}
      role="dialog"
      aria-label={title}
    >
      <div className="demo-tour-tooltip__header">
        <h3 className="demo-tour-tooltip__title">{title}</h3>
        <span className="demo-tour-tooltip__counter">
          {stepIndex + 1} / {totalSteps}
        </span>
      </div>

      <div className="demo-tour-tooltip__body">
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>

      {actionHint && <p className="demo-tour-tooltip__hint">{actionHint}</p>}

      <div className="demo-tour-tooltip__nav">
        {isLastStep && onUpload && (
          <button
            className="demo-tour-tooltip__upload-btn"
            onClick={onUpload}
            type="button"
          >
            <Upload size={14} />
            Upload Your Video
          </button>
        )}
        <div className="demo-tour-tooltip__nav-buttons">
          {!isFirstStep && (
            <button
              className="demo-tour-tooltip__nav-btn demo-tour-tooltip__nav-btn--back"
              onClick={onPrev}
              type="button"
            >
              Back
            </button>
          )}
          <button
            className="demo-tour-tooltip__nav-btn demo-tour-tooltip__nav-btn--skip"
            onClick={onEnd}
            type="button"
          >
            {isLastStep ? 'Close' : 'Skip'}
          </button>
          {!isLastStep && (
            <button
              className="demo-tour-tooltip__nav-btn demo-tour-tooltip__nav-btn--next"
              onClick={onNext}
              type="button"
            >
              Next
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default DemoTourTooltip;
