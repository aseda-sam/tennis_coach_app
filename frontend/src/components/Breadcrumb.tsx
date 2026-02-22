import React from 'react';
import './Breadcrumb.css';

interface BreadcrumbSegment {
  label: string;
  onClick?: () => void;
}

interface BreadcrumbProps {
  segments: BreadcrumbSegment[];
}

const Breadcrumb: React.FC<BreadcrumbProps> = ({ segments }) => {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      {segments.map((segment, i) => {
        const isLast = i === segments.length - 1;
        return (
          <React.Fragment key={i}>
            <span className="breadcrumb__segment">
              {segment.onClick && !isLast ? (
                <button
                  className="breadcrumb__link"
                  onClick={segment.onClick}
                  type="button"
                >
                  {segment.label}
                </button>
              ) : (
                <span className="breadcrumb__current">{segment.label}</span>
              )}
            </span>
            {!isLast && <span className="breadcrumb__separator">/</span>}
          </React.Fragment>
        );
      })}
    </nav>
  );
};

export default Breadcrumb;
