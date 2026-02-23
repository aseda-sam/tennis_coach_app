import React from 'react';
import { ServeWindow } from '../types/serveWindow';
import './ServeNavigator.css';

interface ServeNavigatorProps {
  serveWindows: ServeWindow[];
  currentIndex: number;
  onNavigate: (index: number) => void;
}

const ServeNavigator: React.FC<ServeNavigatorProps> = ({
  serveWindows,
  currentIndex,
  onNavigate,
}) => {
  if (serveWindows.length === 0) return null;

  const current = serveWindows[currentIndex];
  const courtSide = current?.court_side
    ? `${current.court_side.charAt(0).toUpperCase() + current.court_side.slice(1)} Court`
    : null;

  return (
    <div className="serve-navigator">
      <button
        className="serve-navigator__btn"
        onClick={() => onNavigate(currentIndex - 1)}
        disabled={currentIndex <= 0}
        aria-label="Previous serve"
        type="button"
      >
        &#8249;
      </button>
      <div className="serve-navigator__info">
        <span className="serve-navigator__count">
          Serve {currentIndex + 1} of {serveWindows.length}
        </span>
        {courtSide && (
          <span className="serve-navigator__side">{courtSide}</span>
        )}
      </div>
      <button
        className="serve-navigator__btn"
        onClick={() => onNavigate(currentIndex + 1)}
        disabled={currentIndex >= serveWindows.length - 1}
        aria-label="Next serve"
        type="button"
      >
        &#8250;
      </button>
    </div>
  );
};

export default ServeNavigator;
