import React from 'react';
import './LoadingIndicator.css';

type LoadingIndicatorSize = 'sm' | 'md' | 'lg';
type LoadingIndicatorTone = 'default' | 'light';

interface LoadingIndicatorProps {
  label?: string;
  size?: LoadingIndicatorSize;
  tone?: LoadingIndicatorTone;
  centered?: boolean;
}

const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({
  label = 'Loading...',
  size = 'md',
  tone = 'default',
  centered = true,
}) => {
  return (
    <div
      className={`tc-loading ${centered ? 'tc-loading--centered' : ''}`}
      role="status"
      aria-live="polite"
    >
      <span
        className={`tc-loading__ring tc-loading__ring--${size} tc-loading__ring--${tone}`}
        aria-hidden="true"
      />
      <p className={`tc-loading__label tc-loading__label--${tone}`}>{label}</p>
    </div>
  );
};

export default LoadingIndicator;
