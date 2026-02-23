import React from 'react';
import './CollapsibleSection.css';

interface CollapsibleSectionProps {
  title: string;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  expanded,
  onToggle,
  children,
}) => {
  return (
    <div className="collapsible-section">
      <button
        type="button"
        className="collapsible-section__toggle"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <svg
          className={`collapsible-section__chevron${expanded ? ' collapsible-section__chevron--open' : ''}`}
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
        >
          <path
            d="M6 4l4 4-4 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="collapsible-section__label">{title}</span>
      </button>
      {expanded && (
        <div className="collapsible-section__content">{children}</div>
      )}
    </div>
  );
};

export default CollapsibleSection;
